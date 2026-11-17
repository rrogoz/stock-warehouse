"""Entry point for `python -m engine`: `run` runs the pipeline (SW-16)."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Sequence

from engine import __version__
from engine.pipeline import STEPS, run_pipeline
from engine.storage import Config, ConfigError, from_config


def main(argv: Sequence[str] = ()) -> int:
    parser = argparse.ArgumentParser(prog="python -m engine")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("run", help="run the pipeline steps in order, then publish")
    args = parser.parse_args(argv)

    if args.command != "run":
        print(f"stock-warehouse engine {__version__}: use `run` to run the pipeline")
        return 0

    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(levelname)s %(message)s")
    try:
        cfg = Config.from_env(os.environ)
    except ConfigError as error:
        print(f"configuration error: {error}", file=sys.stderr)
        return 2
    result = run_pipeline(cfg, from_config(cfg), STEPS)
    print(f"run {result.run_id} {result.status}")
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
