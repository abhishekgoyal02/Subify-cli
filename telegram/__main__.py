"""Package entry point for ``python -m telegram``."""

from .bot import main


if __name__ == "__main__":
    raise SystemExit(main())
