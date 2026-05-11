from unittest.mock import MagicMock, patch

from convmd.cli import main


def _base_args(target, output_dir):
    """Build a fully-populated Namespace-like mock matching the new argparse schema."""
    a = MagicMock()
    a.target = target
    a.output_dir = output_dir
    a.obsidian_vault = None
    a.transform = None
    a.notebooklm = None
    a.open_obsidian = False
    a.interval = 0
    a.summary = False
    a.slack_webhook = None
    a.auto_link = False
    a.depth = 0
    a.format = "md"
    a.bilingual = False
    a.diff_only = False
    a.no_cache = False
    a.show_cost = False
    a.podcast_limit = 1
    return a


@patch("convmd.pipeline.process_target")
@patch("convmd.cli.argparse.ArgumentParser.parse_args")
def test_cli_directory_processing(mock_parse_args, mock_process_target, tmp_path):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    file1 = input_dir / "test1.md"
    file1.touch()
    file2 = input_dir / "test2.pdf"
    file2.touch()
    hidden_file = input_dir / ".hidden.md"
    hidden_file.touch()

    mock_parse_args.return_value = _base_args(str(input_dir), tmp_path / "output")

    main()

    assert mock_process_target.call_count == 2
    called_paths = [call.args[1] for call in mock_process_target.call_args_list]
    assert file1 in called_paths
    assert file2 in called_paths
    assert hidden_file not in called_paths


@patch("convmd.pipeline.time.time", return_value=0)
@patch("convmd.pipeline.process_target")
@patch("convmd.pipeline.transform_markdown_with_gemini")
@patch("convmd.pipeline.upload_to_notebooklm")
@patch("convmd.cli.argparse.ArgumentParser.parse_args")
def test_cli_post_processing_pipeline(
    mock_parse_args, mock_upload, mock_transform, mock_process_target, _mock_time, tmp_path
):
    out_dir = tmp_path / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    args = _base_args("https://example.com", out_dir)
    args.transform = "Translate"
    args.notebooklm = "notebook123"
    mock_parse_args.return_value = args

    def fake_process_target(*_args, **_kwargs):
        (out_dir / "generated.md").touch()

    mock_process_target.side_effect = fake_process_target

    transformed_file = out_dir / "generated_transformed.md"
    mock_transform.return_value = transformed_file

    main()

    mock_process_target.assert_called_once()

    mock_transform.assert_called_once()
    assert mock_transform.call_args[0][0].name == "generated.md"
    assert mock_transform.call_args[0][1] == "Translate"

    mock_upload.assert_called_once()
    assert mock_upload.call_args[0][0] == "notebook123"
    assert mock_upload.call_args[0][1] == transformed_file
