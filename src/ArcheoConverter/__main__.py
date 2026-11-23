"""Command line entry point: ``python -m ArcheoConverter`` or ``acheoconverter``.

Starts the ASGI server (uvicorn) with the configuration loaded from
``config/app.json`` (or ``--config`` / ``ARCHEOCONVERTER_CONFIG``) and
environment variable overrides.

Examples:
    python -m ArcheoConverter
    python -m ArcheoConverter --host 127.0.0.1 --port 9000
    archeoconverter --config /etc/acheo/app.json --log-level DEBUG
"""

from __future__ import annotations

import argparse
import logging
import sys


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="archeoconverter",
        description="ArcheoConverter - import, convert, compare and export "
                    "enterprise architecture models.",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to a JSON configuration file (default: config/app.json "
             "or $ARCHEOCONVERTER_CONFIG).",
    )
    parser.add_argument("--host", default=None, help="Bind host (overrides config).")
    parser.add_argument("--port", type=int, default=None, help="Bind port (overrides config).")
    parser.add_argument(
        "--log-level",
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (overrides config).",
    )
    parser.add_argument("--version", action="version", version="ArcheoConverter 1.0.0")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns the process exit code."""
    args = build_arg_parser().parse_args(argv)

    from ArcheoConverter.config import load_config
    from ArcheoConverter.logging_config import setup_logging

    try:
        config = load_config(args.config)
    except Exception as exc:  # ConfigError
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    if args.log_level:
        config.logging.level = args.log_level
    setup_logging(config.logging, force=True)
    logger = logging.getLogger("archeoconverter.main")

    host = args.host or config.server.host
    port = args.port or config.server.port

    import uvicorn

    from ArcheoConverter.application import create_app

    app = create_app(config)
    logger.info("starting ArcheoConverter on http://%s:%d (docs: /docs)", host, port)
    try:
        uvicorn.run(app, host=host, port=port, log_level=config.logging.level.lower())
    except KeyboardInterrupt:
        logger.info("stopped by user")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
