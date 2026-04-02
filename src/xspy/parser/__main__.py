"""CLI: python -m xspy.parser --input novel.txt --output parse_result.json"""

from __future__ import annotations

from pathlib import Path

import click

from xspy.core.logging import setup_logging
from xspy.core.models import ParseInput
from xspy.parser.service import NovelParserService


@click.command()
@click.option("--input", "input_file", required=True, type=click.Path(exists=True))
@click.option("--output", "output_file", default="parse_result.json")
@click.option("--encoding", default=None, help="Force encoding (e.g. gb2312, utf-8)")
@click.option("--chapter-pattern", default=None, help="Regex override for chapter splitting")
def main(
    input_file: str,
    output_file: str,
    encoding: str | None,
    chapter_pattern: str | None,
) -> None:
    """Parse a novel file into structured chapters."""
    setup_logging()
    parser = NovelParserService()
    result = parser.process(
        ParseInput(
            file_path=Path(input_file),
            encoding_override=encoding,
            chapter_pattern_override=chapter_pattern,
        )
    )
    Path(output_file).write_text(result.model_dump_json(indent=2), encoding="utf-8")
    click.echo(f"Parsed {len(result.chapters)} chapters → {output_file}")


if __name__ == "__main__":
    main()
