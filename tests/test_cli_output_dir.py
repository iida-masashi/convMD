"""Regression tests for _resolve_output_dir's CLI-vs-config precedence.

See CLAUDE.md-tracked incident: a YAML-configured `obsidian_vault` was silently
overriding an explicit `--output-dir` CLI argument, because argparse's
`set_defaults(**yaml_defaults)` makes `args.obsidian_vault` truthy regardless of
whether the user typed --obsidian-vault or it only came from config.

These tests go through the actual buggy wiring (build_parser + set_defaults +
parse_args), not a hand-built Namespace, so they exercise the real code path
that produced the original bug -- including argparse's flag abbreviation
(e.g. --output instead of --output-dir), which a naive sys.argv string sniff
would miss.
"""

from pathlib import Path

from convmd.cli import _resolve_output_dir
from convmd.cli_args import build_parser


def _parse(argv, yaml_defaults):
    parser = build_parser()
    if yaml_defaults:
        parser.set_defaults(**yaml_defaults)
    return parser.parse_args(argv)


def test_explicit_output_dir_beats_config_only_obsidian_vault(tmp_path):
    """CLI --output-dir must win when obsidian_vault only came from YAML config."""
    vault = tmp_path / "vault"
    out = tmp_path / "explicit_out"
    yaml_defaults = {"obsidian_vault": vault}
    args = _parse(["target", "--output-dir", str(out)], yaml_defaults)

    resolved = _resolve_output_dir(args, yaml_defaults)

    assert resolved == out.resolve()
    assert not vault.exists()


def test_explicit_output_dir_via_equals_form_also_wins(tmp_path):
    vault = tmp_path / "vault"
    out = tmp_path / "explicit_out"
    yaml_defaults = {"obsidian_vault": vault}
    args = _parse([f"--output-dir={out}", "target"], yaml_defaults)

    resolved = _resolve_output_dir(args, yaml_defaults)

    assert resolved == out.resolve()


def test_explicit_output_dir_via_abbreviated_flag_also_wins(tmp_path):
    """argparse allows unambiguous prefixes (--output) to resolve to --output-dir;
    the fix must not rely on matching the literal '--output-dir' token."""
    vault = tmp_path / "vault"
    out = tmp_path / "explicit_out"
    yaml_defaults = {"obsidian_vault": vault}
    args = _parse(["target", "--output", str(out)], yaml_defaults)

    resolved = _resolve_output_dir(args, yaml_defaults)

    assert resolved == out.resolve()
    assert not vault.exists()


def test_config_only_obsidian_vault_still_wins_without_explicit_output_dir(tmp_path):
    """If the user didn't pass --output-dir at all, a config-only obsidian_vault still applies."""
    vault = tmp_path / "vault"
    yaml_defaults = {"obsidian_vault": vault}
    args = _parse(["target"], yaml_defaults)

    resolved = _resolve_output_dir(args, yaml_defaults)

    assert resolved == vault.resolve()
    assert vault.exists()


def test_explicit_obsidian_vault_wins_even_with_explicit_output_dir(tmp_path):
    """Explicit beats explicit: --obsidian-vault on the CLI still takes precedence
    over an explicit --output-dir, matching the pre-existing single-flag behavior."""
    vault = tmp_path / "vault"
    other_vault = tmp_path / "other_vault"
    out = tmp_path / "explicit_out"
    yaml_defaults = {"obsidian_vault": other_vault}
    args = _parse(
        ["target", "--output-dir", str(out), "--obsidian-vault", str(vault)], yaml_defaults
    )

    resolved = _resolve_output_dir(args, yaml_defaults)

    assert resolved == vault.resolve()


def test_no_obsidian_vault_uses_output_dir(tmp_path):
    out = tmp_path / "out"
    args = _parse(["target", "--output-dir", str(out)], {})

    resolved = _resolve_output_dir(args, {})

    assert resolved == Path(out)


def test_no_flags_no_config_falls_back_to_default(monkeypatch, tmp_path):
    monkeypatch.delenv("CONVMD_OUTPUT_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    args = _parse(["target"], {})

    resolved = _resolve_output_dir(args, {})

    assert resolved == (tmp_path / "output").resolve()
