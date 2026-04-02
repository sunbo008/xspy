"""CLI: python -m xspy.character --input parse_result.json --output cast_registry.json"""

from __future__ import annotations

from pathlib import Path

import click

from xspy.character.service import CharacterEngineService
from xspy.core.config import load_llm_models, load_settings
from xspy.core.llm.client import ModelConfig
from xspy.core.llm.prompts import PromptManager
from xspy.core.llm.router import ModelRouter
from xspy.core.logging import setup_logging
from xspy.core.models import CharacterInput, ParseResult


@click.command()
@click.option("--input", "input_file", required=True, type=click.Path(exists=True))
@click.option("--output", "output_file", default="cast_registry.json")
@click.option("--relations", "relations_file", default="relation_graph.json")
def main(input_file: str, output_file: str, relations_file: str) -> None:
    """Analyze characters from parse result."""
    setup_logging()
    settings = load_settings()
    llm_data = load_llm_models(settings)
    models = [ModelConfig(**m) for m in llm_data["models"]]
    router = ModelRouter(models, llm_data.get("task_routing", {}))
    prompts = PromptManager()

    parse_result = ParseResult.model_validate_json(Path(input_file).read_text(encoding="utf-8"))

    svc = CharacterEngineService(router, prompts)
    output = svc.process(CharacterInput(parse_result=parse_result))

    Path(output_file).write_text(output.cast_registry.model_dump_json(indent=2), encoding="utf-8")
    Path(relations_file).write_text(
        output.relation_graph.model_dump_json(indent=2), encoding="utf-8"
    )
    click.echo(
        f"Found {len(output.cast_registry.characters)} characters, "
        f"{len(output.relation_graph.edges)} relations"
    )


if __name__ == "__main__":
    main()
