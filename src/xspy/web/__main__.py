"""Web server entry point: python -m xspy.web"""

from __future__ import annotations

import click
import uvicorn

from xspy.core.config import load_settings


@click.command()
@click.option("--host", default=None)
@click.option("--port", default=None, type=int)
@click.option("--reload", is_flag=True, default=False)
def main(host: str | None, port: int | None, *, reload: bool) -> None:
    """Start the xspy web server."""
    settings = load_settings()
    uvicorn.run(
        "xspy.web.app:create_app",
        factory=True,
        host=host or settings.web.host,
        port=port or settings.web.port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
