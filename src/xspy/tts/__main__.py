"""CLI: python -m xspy.tts --input tts_request.json --output audio.wav"""

from __future__ import annotations

from pathlib import Path

import click

from xspy.core.config import load_settings
from xspy.core.logging import setup_logging
from xspy.core.models import TTSRequest
from xspy.tts.service import TTSClientService


@click.command()
@click.option("--input", "input_file", required=True, type=click.Path(exists=True))
@click.option("--output-dir", default="data/tts_output")
def main(input_file: str, output_dir: str) -> None:
    """Synthesize speech from a TTS request JSON."""
    setup_logging()
    settings = load_settings()
    req = TTSRequest.model_validate_json(Path(input_file).read_text(encoding="utf-8"))

    svc = TTSClientService(
        base_url=settings.tts.base_url,
        timeout=settings.tts.timeout_seconds,
        max_retries=settings.tts.max_retries,
        output_dir=output_dir,
    )
    try:
        resp = svc.process(req)
        click.echo(f"Synthesized → {resp.audio_path} ({resp.metadata.latency_ms}ms)")
    finally:
        svc.close()


if __name__ == "__main__":
    main()
