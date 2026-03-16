"""CLI entry point for freecad-lap converter."""

import logging

from .build import build_lap_files

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main():
    """Build .lap files from FreeCAD API stubs + docs."""
    build_lap_files()


if __name__ == "__main__":
    main()
