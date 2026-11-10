"""Entry point for `python -m engine`. The pipeline command arrives in M1."""

from engine import __version__


def main() -> int:
    print(f"stock-warehouse engine {__version__}: no pipeline steps yet")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
