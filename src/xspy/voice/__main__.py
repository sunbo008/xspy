"""CLI: python -m xspy.voice --input cast_registry.json --output voice_assignment.json"""

from __future__ import annotations

from pathlib import Path

import click

from xspy.core.logging import setup_logging
from xspy.core.models import CastRegistry, VoiceBankInput
from xspy.voice.service import VoiceBankService


@click.command()
@click.option("--input", "input_file", required=True, type=click.Path(exists=True))
@click.option("--output", "output_file", default="voice_assignment.json")
def main(input_file: str, output_file: str) -> None:
    """Assign voices to characters from cast registry."""
    setup_logging()
    cast_registry = CastRegistry.model_validate_json(Path(input_file).read_text(encoding="utf-8"))

    svc = VoiceBankService()
    result = svc.process(VoiceBankInput(cast_registry=cast_registry))

    Path(output_file).write_text(result.model_dump_json(indent=2), encoding="utf-8")
    click.echo(f"Assigned {len(result.assignments)} voices, {len(result.unassigned)} unassigned")


if __name__ == "__main__":
    main()
