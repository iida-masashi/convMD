from unittest.mock import MagicMock, patch

from convmd.cli import main


@patch("convmd.cli.process_target")
@patch("convmd.cli.argparse.ArgumentParser.parse_args")
def test_cli_directory_processing(mock_parse_args, mock_process_target, tmp_path):
    # Setup dummy directory with files
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    file1 = input_dir / "test1.md"
    file1.touch()

    file2 = input_dir / "test2.pdf"
    file2.touch()

    # Hidden file should be skipped
    hidden_file = input_dir / ".hidden.md"
    hidden_file.touch()

    # Mock CLI arguments
    mock_args = MagicMock()
    mock_args.target = str(input_dir)
    mock_args.output_dir = tmp_path / "output"
    mock_args.obsidian_vault = None
    mock_args.transform = None
    mock_args.notebooklm = None
    mock_args.open_obsidian = False
    mock_args.interval = 0
    mock_args.summary = False
    mock_args.slack_webhook = None
    mock_args.auto_link = False
    mock_args.depth = 0
    mock_parse_args.return_value = mock_args

    # Execute
    main()

    # Verify that process_target was called for the two visible files
    assert mock_process_target.call_count == 2

    called_paths = [call.args[1] for call in mock_process_target.call_args_list]
    assert file1 in called_paths
    assert file2 in called_paths
    assert hidden_file not in called_paths


@patch("convmd.cli.time.time", return_value=0)
@patch("convmd.cli.process_target")
@patch("convmd.cli.transform_markdown_with_gemini")
@patch("convmd.cli.upload_to_notebooklm")
@patch("convmd.cli.argparse.ArgumentParser.parse_args")
def test_cli_post_processing_pipeline(
    mock_parse_args, mock_upload, mock_transform, mock_process_target, mock_time, tmp_path
):
    # Mock CLI arguments
    mock_args = MagicMock()
    mock_args.target = "https://example.com"
    mock_args.output_dir = tmp_path / "output"
    mock_args.obsidian_vault = None
    mock_args.transform = "Translate"
    mock_args.notebooklm = "notebook123"
    mock_args.open_obsidian = False
    mock_args.interval = 0
    mock_args.summary = False
    mock_args.slack_webhook = None
    mock_args.auto_link = False
    mock_args.depth = 0
    mock_parse_args.return_value = mock_args

    out_dir = mock_args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # Simulate parser generating a file
    def fake_process_target(*args, **kwargs):
        new_md = out_dir / "generated.md"
        new_md.touch()

    mock_process_target.side_effect = fake_process_target

    # Simulate transform returning a new file
    transformed_file = out_dir / "generated_transformed.md"
    mock_transform.return_value = transformed_file

    # Execute
    main()

    # Verify Pipeline execution order and arguments
    mock_process_target.assert_called_once()

    mock_transform.assert_called_once()
    assert mock_transform.call_args[0][0].name == "generated.md"
    assert mock_transform.call_args[0][1] == "Translate"

    mock_upload.assert_called_once()
    assert mock_upload.call_args[0][0] == "notebook123"
    assert mock_upload.call_args[0][1] == transformed_file
