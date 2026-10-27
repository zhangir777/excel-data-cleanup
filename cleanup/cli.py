"""clean-table messy.csv --out clean.xlsx"""

import argparse
import csv
from pathlib import Path

from openpyxl import load_workbook

from cleanup.clean import clean_rows
from cleanup.report import STAT_LABELS, write_report


def read_table(path: Path) -> list[dict]:
    """CSV (comma or semicolon, UTF-8 with or without BOM) or the first sheet of an .xlsx."""
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        ws = load_workbook(path, read_only=True, data_only=True).active
        rows = list(ws.iter_rows(values_only=True))
        headers = [str(h or "") for h in rows[0]]
        return [dict(zip(headers, r, strict=False)) for r in rows[1:]]
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    # the most frequent separator in the header wins: "Date;Amount, KZT" is ;-separated
    delimiter = max(";\t,", key=lines[0].count) if lines else ","
    return list(csv.DictReader(lines, delimiter=delimiter))


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Clean a messy sales/leads table into an Excel report")
    p.add_argument("source", type=Path, help=".csv or .xlsx")
    p.add_argument("--out", type=Path, default=Path("out/clean.xlsx"))
    p.add_argument("--month-first", action="store_true", help="read 02/03/2026 as Feb 3 (US)")
    args = p.parse_args(argv)

    result = clean_rows(read_table(args.source), month_first=args.month_first)
    write_report(result, args.out)
    for key, value in result.stats.items():
        print(f"{STAT_LABELS[key]}: {value}")
    print(f"Saved: {args.out}")


if __name__ == "__main__":
    main()
