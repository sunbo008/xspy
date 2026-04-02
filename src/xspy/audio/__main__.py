"""CLI: python -m xspy.audio --input tts_results/ch001/ --screenplay enriched_ch001.json --output chapter.wav"""

from __future__ import annotations

from pathlib import Path

import click

from xspy.audio.service import AudioProcessorService
from xspy.core.logging import setup_logging
from xspy.core.models import AudioInput, AudioSegment, ChapterScreenplay


@click.command()
@click.option("--input", "input_dir", required=True, type=click.Path(exists=True))
@click.option("--screenplay", "screenplay_file", required=True, type=click.Path(exists=True))
@click.option("--output-dir", default="data/output")
def main(input_dir: str, screenplay_file: str, output_dir: str) -> None:
    """Assemble utterance WAV files into chapter audio."""
    setup_logging()
    screenplay = ChapterScreenplay.model_validate_json(
        Path(screenplay_file).read_text(encoding="utf-8")
    )

    in_path = Path(input_dir)
    segments = []
    for wav_file in sorted(in_path.glob("*.wav")):
        uid = wav_file.stem
        segments.append(AudioSegment(utterance_id=uid, file_path=wav_file))

    svc = AudioProcessorService(output_dir=output_dir)
    result = svc.process(AudioInput(segments=segments, screenplay=screenplay))
    click.echo(f"Assembled chapter audio → {result.file_path} ({result.duration_ms}ms)")


if __name__ == "__main__":
    main()
