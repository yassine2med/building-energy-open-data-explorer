"""Rank buildings from a benchmarking table by energy use intensity within property type."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED = ["building_id", "name", "property_type", "sqft", "electricity_kwh", "gas_therms"]
KWH_TO_KBTU = 3.412142
THERM_TO_KBTU = 100.0


def load(path: str | Path) -> tuple[pd.DataFrame, int]:
    """Read the CSV and return (clean table, number of rows dropped).

    Rows without a positive floor area or with negative energy are dropped."""
    frame = pd.read_csv(path)
    missing = [c for c in REQUIRED if c not in frame.columns]
    if missing:
        raise ValueError(f"missing columns: {', '.join(missing)}")
    for col in ("sqft", "electricity_kwh", "gas_therms"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    energy = frame[["electricity_kwh", "gas_therms"]]
    good = (frame["sqft"] > 0) & energy.notna().all(axis=1) & (energy >= 0).all(axis=1)
    return frame[good].copy(), int((~good).sum())


def add_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    """Add site EUI (kBtu/sqft), percentile within property type and an outlier flag.

    Percentile 100 is the highest use in its type. An outlier is above Q3 + 1.5 x IQR
    of its property type."""
    out = frame.copy()
    kbtu = out["electricity_kwh"] * KWH_TO_KBTU + out["gas_therms"] * THERM_TO_KBTU
    out["eui"] = (kbtu / out["sqft"]).round(1)
    groups = out.groupby("property_type")["eui"]
    out["percentile"] = (groups.rank(pct=True) * 100).round(0).astype(int)
    q1 = groups.transform(lambda s: s.quantile(0.25))
    q3 = groups.transform(lambda s: s.quantile(0.75))
    out["outlier"] = out["eui"] > q3 + 1.5 * (q3 - q1)
    return out


def rank(frame: pd.DataFrame, property_type: str | None = None, top: int = 10) -> pd.DataFrame:
    """Return the `top` highest-EUI buildings, optionally for one property type."""
    if top < 1:
        raise ValueError("top must be at least 1")
    table = add_metrics(frame)
    if property_type is not None:
        table = table[table["property_type"].str.lower() == property_type.lower()]
        if table.empty:
            raise ValueError(f"no buildings of type {property_type!r}")
    return table.sort_values("eui", ascending=False).head(top)


def type_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Count, median EUI and outlier count for each property type."""
    table = add_metrics(frame)
    summary = table.groupby("property_type").agg(
        buildings=("eui", "size"), median_eui=("eui", "median"), outliers=("outlier", "sum")
    )
    return summary.sort_values("median_eui", ascending=False)
