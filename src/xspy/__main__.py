"""CLI entry point: python -m xspy"""

from __future__ import annotations

import sys

import click

from xspy import __version__
from xspy.core.config import load_settings
from xspy.core.logging import setup_logging


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True, help="Show version and exit.")
@click.pass_context
def main(ctx: click.Context, *, version: bool) -> None:
    """xspy — Novel-to-audiobook fully automated dubbing system."""
    if version:
        click.echo(f"xspy {__version__}")
        return
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
def validate_config() -> None:
    """Validate configuration files and show final merged settings."""
    setup_logging()
    try:
        settings = load_settings()
        click.echo("Configuration valid.")
        click.echo(settings.model_dump_json(indent=2))
    except Exception as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
