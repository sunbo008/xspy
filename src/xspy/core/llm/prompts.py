"""Prompt template management using Jinja2."""

from __future__ import annotations

from pathlib import Path

import structlog
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from xspy.core.exceptions import AgentError

logger = structlog.get_logger()

_DEFAULT_PROMPTS_DIR = Path("resources/prompts")


class PromptManager:
    """Loads and renders Jinja2 prompt templates from the resources directory."""

    def __init__(self, prompts_dir: str | Path = _DEFAULT_PROMPTS_DIR) -> None:
        self._prompts_dir = Path(prompts_dir)
        self._env = Environment(
            loader=FileSystemLoader(str(self._prompts_dir)),
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_path: str, **context: object) -> str:
        """Render a prompt template with the given context variables.

        Args:
            template_path: Relative path within prompts dir (e.g. "screenwriter/split.j2")
            **context: Template variables
        """
        try:
            template = self._env.get_template(template_path)
        except TemplateNotFound as e:
            raise AgentError(
                f"Prompt template not found: {template_path}",
                module="llm.prompts",
                context={"prompts_dir": str(self._prompts_dir)},
            ) from e

        rendered = template.render(**context)
        logger.debug(
            "prompt.rendered",
            template=template_path,
            length=len(rendered),
        )
        return rendered

    def list_templates(self) -> list[str]:
        """List all available template paths."""
        return sorted(self._env.list_templates(extensions=["j2", "txt", "md"]))
