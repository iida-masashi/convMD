"""Regression tests for _resolve_output_dir's CLI-vs-config precedence.

See CLAUDE.md-tracked incident: a YAML-configured `obsidian_vault` was silently
overriding an explicit `--output-dir` CLI argument, because argparse's
`set_defaults(**yaml_defaults)` makes `args.obsidian_vault` truthy regardless of
whether the user typed --obsidian-vault or it only came from config.
"""

from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from convmd.cli import _resolve_output_dir


def _args(*, output_dir=None, obsidian_vault=None):
    return Namespace(output_dir=output_dir, obsidian_vault=obsidian_vault)


def test_explicit_output_dir_beats_config_only_obsidian_vault(tmp_path):
    """CLI --output-dir must win when obsidian_vault only came from YAML config."""
    vault = tmp_path / "vault"
    out = tmp_path / "explicit_out"
    args = _args(output_dir=out, obsidian_vault=vault)
    argv = ["target", "--output-dir", str(out)]  # note: no --obsidian-vault token
    with patch("convmd.cli.sys.argv", ["convmd", *argv]):
        resolved = _resolve_output_dir(args)
    assert resolved == out.resolve()
    assert not vault.exists()


def test_explicit_output_dir_equals_form_also_wins(tmp_path):
    vault = tmp_path / "vault"
    out = tmp_path / "explicit_out"
    args = _args(output_dir=out, obsidian_vault=vault)
    argv = ["target", f"--output-dir={out}"]
    with patch("convmd.cli.sys.argv", ["convmd", *argv]):
        resolved = _resolve_output_dir(args)
    assert resolved == out.resolve()


def test_config_only_obsidian_vault_still_wins_without_explicit_output_dir(tmp_path):
    """If the user didn't type --output-dir at all, a config-only obsidian_vault still applies."""
    vault = tmp_path / "vault"
    args = _args(output_dir=None, obsidian_vault=vault)
    argv = ["target"]
    with patch("convmd.cli.sys.argv", ["convmd", *argv]):
        resolved = _resolve_output_dir(args)
    assert resolved == vault.resolve()
    assert vault.exists()


def test_explicit_obsidian_vault_wins_even_with_explicit_output_dir(tmp_path):
    """Explicit beats explicit: --obsidian-vault on the CLI still takes precedence."""
    vault = tmp_path / "vault"
    out = tmp_path / "explicit_out"
    args = _args(output_dir=out, obsidian_vault=vault)
    argv = ["target", "--output-dir", str(out), "--obsidian-vault", str(vault)]
    with patch("convmd.cli.sys.argv", ["convmd", *argv]):
        resolved = _resolve_output_dir(args)
    assert resolved == vault.resolve()


def test_no_obsidian_vault_uses_output_dir(tmp_path):
    out = tmp_path / "out"
    args = _args(output_dir=out, obsidian_vault=None)
    argv = ["target", "--output-dir", str(out)]
    with patch("convmd.cli.sys.argv", ["convmd", *argv]):
        resolved = _resolve_output_dir(args)
    assert resolved == Path(out)
