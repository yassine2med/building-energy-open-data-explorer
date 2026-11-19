import pandas as pd
import pytest

from energy_explorer.__main__ import main
from energy_explorer.core import add_metrics, load, rank, type_summary

HEADER = "building_id,name,property_type,sqft,electricity_kwh,gas_therms\n"


def table(rows):
    cols = ["building_id", "name", "property_type", "sqft", "electricity_kwh", "gas_therms"]
    return pd.DataFrame(rows, columns=cols)


def test_eui_calculation():
    t = add_metrics(table([["1", "A", "Office", 1000, 10000, 100]]))
    assert t.loc[0, "eui"] == pytest.approx((10000 * 3.412142 + 10000) / 1000, abs=0.05)


def test_percentile_is_within_type():
    t = add_metrics(table([
        ["1", "A", "Office", 1000, 1000, 0],
        ["2", "B", "Office", 1000, 2000, 0],
        ["3", "C", "School", 1000, 99000, 0],
    ]))
    assert t.set_index("building_id").loc["2", "percentile"] == 100
    assert t.set_index("building_id").loc["3", "percentile"] == 100


def test_outlier_flag():
    rows = [[str(i), f"B{i}", "Office", 1000, 20000 + i * 100, 0] for i in range(9)]
    rows.append(["x", "Hog", "Office", 1000, 400000, 0])
    t = add_metrics(table(rows)).set_index("building_id")
    assert bool(t.loc["x", "outlier"]) and not bool(t.loc["0", "outlier"])


def test_rank_orders_descending_and_limits():
    t = table([[str(i), f"B{i}", "Office", 1000, 1000 * (i + 1), 0] for i in range(5)])
    r = rank(t, top=2)
    assert list(r["building_id"]) == ["4", "3"]


def test_rank_filters_type_case_insensitive():
    t = table([["1", "A", "Office", 1000, 5, 0], ["2", "B", "School", 1000, 9, 0]])
    assert list(rank(t, "school")["building_id"]) == ["2"]


def test_rank_unknown_type():
    with pytest.raises(ValueError, match="no buildings"):
        rank(table([["1", "A", "Office", 1000, 5, 0]]), "Zoo")


def test_rank_bad_top():
    with pytest.raises(ValueError):
        rank(table([["1", "A", "Office", 1000, 5, 0]]), top=0)


def test_load_drops_bad_rows(tmp_path):
    p = tmp_path / "d.csv"
    p.write_text(HEADER + "1,A,Office,1000,5,5\n2,B,Office,,5,5\n3,C,Office,100,-5,5\n4,D,Office,0,5,5\n")
    frame, dropped = load(p)
    assert list(frame["building_id"]) == [1] and dropped == 3


def test_load_missing_columns(tmp_path):
    p = tmp_path / "d.csv"
    p.write_text("building_id,name\n1,A\n")
    with pytest.raises(ValueError, match="missing columns"):
        load(p)


def test_summary_counts():
    s = type_summary(table([["1", "A", "Office", 1000, 5, 0], ["2", "B", "Office", 1000, 7, 0]]))
    assert s.loc["Office", "buildings"] == 2


def test_example_file_runs(capsys):
    assert main(["examples/benchmarking.csv", "--top", "3"]) == 0
    out = capsys.readouterr().out
    assert "1 dropped" in out and "By property type" in out


def test_cli_bad_file():
    assert main(["nope.csv"]) == 1
