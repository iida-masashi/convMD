"""Tests for vault tag extraction and normalization."""

from convmd.integrations.vault_tags import (
    _extract_tags_from_frontmatter,
    _is_cjk,
    normalize_tag,
    normalize_tags,
    scan_vault_tags,
)

# --- frontmatter extraction ---

def test_extract_tags_inline_list():
    content = '---\ntitle: foo\ntags: [Python, "AI", machine-learning]\n---\n# body\n'
    assert _extract_tags_from_frontmatter(content) == ["Python", "AI", "machine-learning"]


def test_extract_tags_yaml_block():
    content = '---\ntitle: foo\ntags:\n  - "Python"\n  - AI\n  - "歴史"\n---\n'
    assert _extract_tags_from_frontmatter(content) == ["Python", "AI", "歴史"]


def test_extract_tags_no_frontmatter():
    assert _extract_tags_from_frontmatter("# just markdown") == []


def test_extract_tags_frontmatter_without_tags():
    assert _extract_tags_from_frontmatter("---\ntitle: foo\n---\n") == []


def test_extract_tags_mixed_inline_and_block_takes_both():
    content = '---\ntitle: x\ntags: [a, b]\nother:\n  ignored: true\n---\n'
    assert _extract_tags_from_frontmatter(content) == ["a", "b"]


# --- CJK detection ---

def test_is_cjk_detects_japanese():
    assert _is_cjk("歴史") is True
    assert _is_cjk("ひらがな") is True
    assert _is_cjk("カタカナ") is True
    assert _is_cjk("混合English歴史") is True


def test_is_cjk_pure_ascii():
    assert _is_cjk("python") is False
    assert _is_cjk("machine-learning") is False


# --- normalize_tag ---

def test_normalize_tag_exact_case_insensitive_match():
    existing = {"Python", "JavaScript"}
    assert normalize_tag("python", existing) == "Python"
    assert normalize_tag("PYTHON", existing) == "Python"


def test_normalize_tag_fuzzy_above_cutoff():
    existing = {"machine-learning"}
    # "machine_learning" -> "machine-learning"
    assert normalize_tag("machine_learning", existing) == "machine-learning"


def test_normalize_tag_below_cutoff_returns_input():
    existing = {"history"}
    # "biology" is too different from "history"
    assert normalize_tag("biology", existing) == "biology"


def test_normalize_tag_cjk_skips_fuzzy():
    # "歴" and "歴史" would otherwise fuzzy-match (1 char vs 2 char)
    existing = {"歴史"}
    assert normalize_tag("歴", existing) == "歴"


def test_normalize_tag_cjk_exact_still_works():
    existing = {"歴史"}
    assert normalize_tag("歴史", existing) == "歴史"


def test_normalize_tag_empty_existing():
    assert normalize_tag("anything", set()) == "anything"


def test_normalize_tag_empty_input():
    assert normalize_tag("", {"x", "y"}) == ""


def test_normalize_tag_respects_cutoff_parameter():
    existing = {"history"}
    # With a low cutoff, "histo" should still match
    assert normalize_tag("histo", existing, cutoff=0.5) == "history"
    # With a strict cutoff, it should not
    assert normalize_tag("histo", existing, cutoff=0.99) == "histo"


# --- normalize_tags list version ---

def test_normalize_tags_preserves_order_and_dedupes():
    existing = {"Python", "machine-learning"}
    out = normalize_tags(["python", "PYTHON", "machine_learning", "novel"], existing)
    assert out == ["Python", "machine-learning", "novel"]


# --- scan_vault_tags ---

def test_scan_vault_tags_empty_vault(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    assert scan_vault_tags(vault) == set()


def test_scan_vault_tags_nonexistent_vault(tmp_path):
    assert scan_vault_tags(tmp_path / "nonexistent") == set()


def test_scan_vault_tags_walks_recursively(tmp_path):
    vault = tmp_path / "vault"
    (vault / "a").mkdir(parents=True)
    (vault / "a" / "note1.md").write_text(
        '---\ntags: [Python, AI]\n---\n# n1\n', encoding="utf-8"
    )
    (vault / "note2.md").write_text(
        '---\ntags:\n  - "歴史"\n  - "Japan"\n---\n', encoding="utf-8"
    )
    # A file without frontmatter should be skipped
    (vault / "note3.md").write_text("# plain\n", encoding="utf-8")

    tags = scan_vault_tags(vault)
    assert tags == {"Python", "AI", "歴史", "Japan"}


def test_scan_vault_tags_skips_unreadable_files(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "ok.md").write_text("---\ntags: [a]\n---\n", encoding="utf-8")
    # Binary garbage — Read with errors='ignore' should not crash
    (vault / "bad.md").write_bytes(b"\xff\xfe\x00\x00 not real utf16")
    tags = scan_vault_tags(vault)
    assert "a" in tags


# --- pipeline integration ---

def test_link_phase_passes_vault_when_normalize_enabled(tmp_path):
    from unittest.mock import patch

    from convmd.cli_args import RunConfig
    from convmd.pipeline import link_phase

    cfg = RunConfig(
        target="x",
        output_dir=tmp_path,
        auto_link=True,
        normalize_tags=True,
        obsidian_vault=tmp_path / "vault",
        tag_similarity_cutoff=0.9,
    )
    f = tmp_path / "a.md"
    with patch("convmd.core.transform.apply_obsidian_links") as mock_link:
        mock_link.return_value = f
        link_phase([f], cfg)
        _, kwargs = mock_link.call_args
        assert kwargs["vault_path"] == cfg.obsidian_vault
        assert kwargs["tag_similarity_cutoff"] == 0.9


def test_link_phase_no_vault_when_normalize_disabled(tmp_path):
    from unittest.mock import patch

    from convmd.cli_args import RunConfig
    from convmd.pipeline import link_phase

    cfg = RunConfig(
        target="x",
        output_dir=tmp_path,
        auto_link=True,
        normalize_tags=False,
        obsidian_vault=tmp_path / "vault",
    )
    f = tmp_path / "a.md"
    with patch("convmd.core.transform.apply_obsidian_links") as mock_link:
        mock_link.return_value = f
        link_phase([f], cfg)
        _, kwargs = mock_link.call_args
        assert kwargs["vault_path"] is None
