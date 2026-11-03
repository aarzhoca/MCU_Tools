"""Run from backend/: python preview_st_xlsx.py vendor.xlsx --out preview.json"""
import argparse
import json
from pathlib import Path
from app.st_xlsx import parse_st_xlsx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--sheet", default="ProductsList")
    parser.add_argument("--out", type=Path, default=Path("st-xlsx-preview.json"))
    args = parser.parse_args()
    protected = Path(__file__).resolve().parent / "data"
    output = args.out.resolve()
    source = args.workbook.resolve()
    if output == source or output == protected or protected in output.parents:
        parser.error("Output must not overwrite the workbook or backend/data")
    if output.exists():
        parser.error("Output already exists; choose another --out path")
    if source.stat().st_size > 20 * 1024 * 1024:
        parser.error("Workbook exceeds 20 MiB")
    result = parse_st_xlsx(source.read_bytes(), source.name, args.sheet)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False, allow_nan=False)
    print("Parsed:", result["parsed_count"], "Row errors:", len(result["errors"]))
    print("Preview written:", output)
    print("No catalog was changed. Do not submit staging records to legacy /bulk.")


if __name__ == "__main__":
    main()
