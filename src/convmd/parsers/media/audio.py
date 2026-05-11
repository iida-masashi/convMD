import logging
from pathlib import Path

from convmd.core.utils import generate_frontmatter, sanitize_filename

logger = logging.getLogger(__name__)


def format_timestamp(seconds: float) -> str:
    """Formats seconds into HH:MM:SS or MM:SS."""
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def convert_audio_file(file_path: Path, output_dir: Path) -> Path | None:
    """
    Transcribes a local audio/video file using faster-whisper and saves it as Markdown.
    Requires FFmpeg to be installed on the system.
    """
    logger.info(f"Attempting to transcribe {file_path} using faster-whisper...")

    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return None

    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError:
        logger.error("faster-whisper is not installed. Please install it to use this feature.")
        return None

    try:
        # Load the model. 'base' or 'small' are good tradeoffs for CPU/speed.
        # For better accuracy, users can change this to 'medium' or 'large-v3'.
        model_size = "base"

        # Determine device. fallback to CPU if CUDA is not easily available
        # compute_type="int8" makes it much lighter on CPU
        logger.info(f"Loading Whisper model ({model_size}) on CPU with int8 quantization...")
        model = WhisperModel(model_size, device="cpu", compute_type="int8")

        logger.info("Transcription started. This may take a while depending on file length...")
        # Transcribe with VAD (Voice Activity Detection) filter to skip silence
        segments, info = model.transcribe(str(file_path), beam_size=5, vad_filter=True)

        logger.info(
            f"Detected language '{info.language}' with probability {info.language_probability:.2f}"
        )

        safe_title = sanitize_filename(file_path.stem)
        filename = f"{safe_title}.md"
        out_path = output_dir / filename

        frontmatter = generate_frontmatter(
            title=file_path.name,
            url=f"file://{file_path.resolve()}",
            tags=["local_file", "audio_transcript"],
        )

        lines = [
            frontmatter,
            f"# {file_path.name} の文字起こし\n\n",
            f"- **検出言語**: {info.language}\n",
            "- **使用モデル**: Whisper (faster-whisper)\n\n",
            "## トランスクリプト\n\n",
        ]

        # Process segments as an iterator
        for segment in segments:
            start_time = format_timestamp(segment.start)
            text = segment.text.strip()
            if text:
                lines.append(f"**[{start_time}]** {text}\n\n")

        out_path.write_text("".join(lines), encoding="utf-8")

        logger.info(f"Successfully transcribed {file_path} to {out_path}")
        return out_path

    except Exception as e:
        logger.error(
            f"Failed to transcribe audio file {file_path}. Ensure FFmpeg is installed in your PATH. Error: {e}"
        )
        return None
