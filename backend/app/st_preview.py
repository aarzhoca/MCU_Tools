"""Build bounded ST preview responses without storing uploads or catalogs."""
from .st_xlsx import COLUMNS, parse_st_xlsx


def build_st_preview(content, filename, sheet="ProductsList", part_number=""):
    parsed = parse_st_xlsx(content, filename, sheet)
    query = part_number.strip().upper()
    matches = [record for record in parsed["records"]
               if not query or record["part_number"].upper() == query]
    # Raw workbook columns can be large; only normalized preview records leave here.
    records = [{key: value for key, value in record.items() if key != "source_values"}
               for record in matches[:20]]
    return {"parsed_count": parsed["parsed_count"], "matched_count": len(matches),
        "records": records, "error_count": len(parsed["errors"]),
        "errors": parsed["errors"][:20], "warnings": parsed["warnings"],
        "sheet": parsed["sheet"], "exact_query": query,
        "mapping": {**COLUMNS, "core": "Core + FPU", "package": "Package (LQFP only)"},
        "preview_only": True}
