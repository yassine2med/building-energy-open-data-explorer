"""Command line: python -m energy_explorer FILE.csv [--type Office] [--top 10]."""
from __future__ import annotations

import argparse
import sys

from .core import load, rank, type_summary


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code."""
    parser = argparse.ArgumentParser(prog="energy_explorer", description="Rank buildings by site EUI")
    parser.add_argument("csv")
    parser.add_argument("--type", dest="property_type", help="only this property type")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args(argv)
    try:
        frame, dropped = load(args.csv)
        ranked = rank(frame, args.property_type, args.top)
        summary = type_summary(frame)
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"{len(frame)} buildings used, {dropped} dropped (bad area or energy)\n")
    print("By property type")
    print(summary.to_string())
    print(f"\nTop {len(ranked)} by EUI (kBtu/sqft)")
    cols = ["building_id", "name", "property_type", "sqft", "eui", "percentile", "outlier"]
    print(ranked[cols].to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
