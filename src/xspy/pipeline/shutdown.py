"""Graceful shutdown handler for the pipeline."""

from __future__ import annotations

import signal
import threading

import structlog

logger = structlog.get_logger()


class GracefulShutdown:
    """Handles SIGTERM/SIGINT for graceful pipeline shutdown.

    When a shutdown signal is received, in-progress tasks are allowed to
    complete, and the checkpoint is saved before exiting.
    """

    def __init__(self) -> None:
        self._shutdown_requested = threading.Event()
        self._original_sigterm = None
        self._original_sigint = None

    def install(self) -> None:
        """Install signal handlers."""
        self._original_sigterm = signal.getsignal(signal.SIGTERM)
        self._original_sigint = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
        logger.debug("shutdown.handlers_installed")

    def uninstall(self) -> None:
        """Restore original signal handlers."""
        if self._original_sigterm:
            signal.signal(signal.SIGTERM, self._original_sigterm)
        if self._original_sigint:
            signal.signal(signal.SIGINT, self._original_sigint)

    def _handle_signal(self, signum: int, frame: object) -> None:
        sig_name = signal.Signals(signum).name
        logger.warning("shutdown.signal_received", signal=sig_name)
        self._shutdown_requested.set()

    @property
    def is_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self._shutdown_requested.is_set()

    def check_or_continue(self) -> None:
        """Raise KeyboardInterrupt if shutdown was requested.

        Call this at safe checkpoints (between chapters, between stages)
        to allow graceful exit.
        """
        if self._shutdown_requested.is_set():
            logger.info("shutdown.graceful_exit")
            raise KeyboardInterrupt("Graceful shutdown requested")
