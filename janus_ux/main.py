"""CLI Entrypoint for launching Janus Core UX."""

from __future__ import annotations

from janus_ux.cli import app, main

__all__ = ["app", "main"]

if __name__ == "__main__":
    main()
