"""Guards against silent data loss: same-title overwrites, empty extracts, unverified AI numbers."""

from pathlib import Path
from unittest.mock import patch

from convmd import pipeline
from convmd.cli_args import RunConfig
from convmd.core.llm_extractor import find_unverified_numbers
from convmd.core.utils import body_text, generate_frontmatter, unique_output_path
from convmd.routing import _is_too_small


def _write(path: Path, url: str, body: str = "body") -> None:
    path.write_text(generate_frontmatter("T", url) + body, encoding="utf-8")


# --- unique_output_path ---

def test_unique_output_path_new_file(tmp_path):
    assert unique_output_path(tmp_path, "T", "https://a") == tmp_path / "T.md"


def test_unique_output_path_same_source_reuses(tmp_path):
    _write(tmp_path / "T.md", "https://a")
    assert unique_output_path(tmp_path, "T", "https://a") == tmp_path / "T.md"


def test_unique_output_path_different_source_gets_suffix(tmp_path):
    _write(tmp_path / "T.md", "https://a")
    _write(tmp_path / "T_2.md", "https://b")
    assert unique_output_path(tmp_path, "T", "https://c") == tmp_path / "T_3.md"
    assert unique_output_path(tmp_path, "T", "https://b") == tmp_path / "T_2.md"


# --- empty-body detection ---

def test_body_text_strips_frontmatter():
    assert body_text(generate_frontmatter("T", "https://a") + "\n hello \n") == "hello"


def test_frontmatter_only_file_is_too_small(tmp_path):
    # Long title/URL pushes the file well past 200 bytes but there is no content.
    path = tmp_path / "x.md"
    path.write_text(
        generate_frontmatter("銘柄スカウター" * 10, "https://example.com/" + "a" * 150) + "# t\n",
        encoding="utf-8",
    )
    assert path.stat().st_size > 200
    assert _is_too_small(path)


def test_real_body_is_not_too_small(tmp_path):
    path = tmp_path / "x.md"
    _write(path, "https://a", "本文" * 100)
    assert not _is_too_small(path)


# --- AI number verification ---

def test_unverified_numbers_ignores_separators_and_fullwidth():
    source = "<td>3,467,675</td><td>１２３４</td>"
    assert find_unverified_numbers("売上 3467675 百万円、1,234件", source) == []


def test_unverified_numbers_flags_converted_or_invented():
    source = "<td>3,467,675</td>"
    # 34,677 (unit-converted) and 999 (invented) are absent; 12 is below the digit floor.
    assert find_unverified_numbers("34,677億円 / 999 / 12", source) == ["34677", "999"]


# --- exit status ---

@patch("convmd.pipeline.dispatch_phase")
@patch("convmd.pipeline.summary_phase", return_value=None)
@patch("convmd.pipeline.extract_phase", return_value=[])
def test_single_target_without_output_fails(_e, _s, _d, tmp_path):
    cfg = RunConfig(target="https://example.com", output_dir=tmp_path, no_cache=True)
    assert pipeline.run_pipeline(cfg) is False


@patch("convmd.pipeline.dispatch_phase")
@patch("convmd.pipeline.summary_phase", return_value=None)
def test_single_target_with_output_succeeds(_s, _d, tmp_path):
    md = tmp_path / "a.md"
    md.write_text("x", encoding="utf-8")
    cfg = RunConfig(target="https://example.com", output_dir=tmp_path, no_cache=True)
    with patch("convmd.pipeline.extract_phase", return_value=[md]):
        assert pipeline.run_pipeline(cfg) is True


@patch("convmd.pipeline.dispatch_phase")
@patch("convmd.pipeline.summary_phase", return_value=None)
@patch("convmd.pipeline.extract_phase", return_value=[])
def test_batch_with_failed_targets_fails(_e, _s, _d, tmp_path):
    (tmp_path / ".convmd_failed.txt").write_text("https://bad\n", encoding="utf-8")
    cfg = RunConfig(target="", output_dir=tmp_path, retry_failed=True, no_cache=True)
    assert pipeline.run_pipeline(cfg) is False
