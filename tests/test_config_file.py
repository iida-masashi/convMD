"""Tests for the YAML config loader."""

from pathlib import Path

from convmd.config_file import load_config


def test_load_config_returns_empty_when_no_files(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    assert load_config(None, home=home, cwd=cwd) == {}


def test_load_config_home_only(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".convmd.yaml").write_text(
        "transform: Translate\nauto_link: true\n", encoding="utf-8"
    )
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    cfg = load_config(None, home=home, cwd=cwd)
    assert cfg == {"transform": "Translate", "auto_link": True}


def test_load_config_cwd_overrides_home(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".convmd.yaml").write_text(
        "transform: HomeTranslate\nauto_link: true\n", encoding="utf-8"
    )
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    (cwd / ".convmd.yaml").write_text(
        "transform: CwdTranslate\n", encoding="utf-8"
    )
    cfg = load_config(None, home=home, cwd=cwd)
    assert cfg["transform"] == "CwdTranslate"
    # auto_link survives from home (cwd didn't override it)
    assert cfg["auto_link"] is True


def test_load_config_explicit_overrides_all(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".convmd.yaml").write_text("transform: home\n", encoding="utf-8")
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    (cwd / ".convmd.yaml").write_text("transform: cwd\n", encoding="utf-8")
    explicit = tmp_path / "custom.yaml"
    explicit.write_text("transform: explicit\n", encoding="utf-8")

    cfg = load_config(explicit, home=home, cwd=cwd)
    assert cfg["transform"] == "explicit"


def test_load_config_coerces_path_fields(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".convmd.yaml").write_text(
        "obsidian_vault: /tmp/vault\noutput_dir: /tmp/out\n", encoding="utf-8"
    )
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    cfg = load_config(None, home=home, cwd=cwd)
    assert isinstance(cfg["obsidian_vault"], Path)
    assert isinstance(cfg["output_dir"], Path)


def test_load_config_coerces_int_fields(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".convmd.yaml").write_text(
        "depth: 3\ninterval: 60\npodcast_limit: 5\n", encoding="utf-8"
    )
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    cfg = load_config(None, home=home, cwd=cwd)
    assert cfg["depth"] == 3
    assert cfg["interval"] == 60
    assert cfg["podcast_limit"] == 5


def test_load_config_unknown_keys_dropped_with_warning(tmp_path, caplog):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".convmd.yaml").write_text(
        "transform: keep\nbogus_key: drop\n", encoding="utf-8"
    )
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    cfg = load_config(None, home=home, cwd=cwd)
    assert "transform" in cfg
    assert "bogus_key" not in cfg
    assert any("bogus_key" in r.message for r in caplog.records)


def test_load_config_malformed_yaml_logged_and_skipped(tmp_path, caplog):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".convmd.yaml").write_text("not: valid: yaml: ::", encoding="utf-8")
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    cfg = load_config(None, home=home, cwd=cwd)
    assert cfg == {}
    assert any("Failed to parse" in r.message for r in caplog.records)


def test_load_config_non_mapping_root_skipped(tmp_path, caplog):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".convmd.yaml").write_text("- just\n- a\n- list\n", encoding="utf-8")
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    cfg = load_config(None, home=home, cwd=cwd)
    assert cfg == {}


def test_load_config_empty_file(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".convmd.yaml").write_text("", encoding="utf-8")
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    assert load_config(None, home=home, cwd=cwd) == {}


def test_load_config_bad_coercion_dropped(tmp_path, caplog):
    home = tmp_path / "home"
    home.mkdir()
    # depth must be int — "abc" cannot be coerced
    (home / ".convmd.yaml").write_text(
        "depth: abc\ntransform: ok\n", encoding="utf-8"
    )
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    cfg = load_config(None, home=home, cwd=cwd)
    assert "depth" not in cfg
    assert cfg["transform"] == "ok"


def test_load_config_cli_integration_via_set_defaults(tmp_path, monkeypatch):
    """End-to-end smoke test: YAML defaults feed into argparse and survive to RunConfig."""
    from convmd.cli_args import build_parser, to_run_config

    home = tmp_path / "home"
    home.mkdir()
    (home / ".convmd.yaml").write_text(
        "transform: FromYaml\nauto_link: true\ndepth: 2\n", encoding="utf-8"
    )
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    defaults = load_config(None, home=home, cwd=cwd)

    parser = build_parser()
    parser.set_defaults(**defaults)
    args = parser.parse_args(["https://example.com"])

    cfg = to_run_config(args, tmp_path)
    assert cfg.transform == "FromYaml"
    assert cfg.auto_link is True
    assert cfg.depth == 2


def test_load_config_render_js_survives_to_run_config(tmp_path):
    """Regression: render_js was missing from _ALLOWED_KEYS, so a YAML
    ``render_js: true`` was silently dropped with a warning and never reached
    RunConfig, even though --render-js works fine from the CLI."""
    from convmd.cli_args import build_parser, to_run_config

    home = tmp_path / "home"
    home.mkdir()
    (home / ".convmd.yaml").write_text("render_js: true\n", encoding="utf-8")
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    defaults = load_config(None, home=home, cwd=cwd)
    assert defaults == {"render_js": True}

    parser = build_parser()
    parser.set_defaults(**defaults)
    args = parser.parse_args(["https://example.com"])

    cfg = to_run_config(args, tmp_path)
    assert cfg.render_js is True


def test_load_config_cli_flag_wins_over_yaml(tmp_path):
    from convmd.cli_args import build_parser, to_run_config

    home = tmp_path / "home"
    home.mkdir()
    (home / ".convmd.yaml").write_text("transform: FromYaml\n", encoding="utf-8")
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    defaults = load_config(None, home=home, cwd=cwd)

    parser = build_parser()
    parser.set_defaults(**defaults)
    args = parser.parse_args(["https://example.com", "--transform", "FromCLI"])
    cfg = to_run_config(args, tmp_path)
    assert cfg.transform == "FromCLI"
