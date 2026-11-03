"""Local preview endpoint only; no catalog or workspace persistence."""
import zipfile
from xml.etree.ElementTree import ParseError
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from openpyxl.utils.exceptions import InvalidFileException
from ..st_preview import build_st_preview

router = APIRouter(prefix="/api", tags=["ST Excel preview"])
LIMIT = 20 * 1024 * 1024


@router.post("/chips/competitor/st-xlsx-preview")
def preview_st_xlsx(file: UploadFile = File(...), sheet: str = Form("ProductsList"),
                    part_number: str = Form("")):
    try:
        filename = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
        if not filename.lower().endswith(".xlsx"):
            raise HTTPException(status_code=400, detail="Select an ST .xlsx workbook")
        if len(sheet) > 100 or len(part_number) > 100:
            raise HTTPException(status_code=422, detail="Sheet or part number is too long")
        content = file.file.read(LIMIT + 1)
        if len(content) > LIMIT:
            raise HTTPException(status_code=413, detail="Workbook exceeds 20 MiB")
        try:
            return build_st_preview(content, filename, sheet, part_number)
        except (ValueError, KeyError, zipfile.BadZipFile, InvalidFileException, ParseError, OSError):
            raise HTTPException(status_code=422,
                detail="Cannot preview this workbook. Check XLSX format, ProductsList sheet, ST headers, and size limits.")
    finally:
        file.file.close()


from ..data_loader import get_nuvoton_parts
from ..matcher import find_matches, CORE_RANK
from ..workspace_matching import WorkspaceRequest, match_workspace


@router.post("/workspace/match")
def workspace_match(request: WorkspaceRequest):
    try:
        return match_workspace(request, get_nuvoton_parts(), find_matches, CORE_RANK)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
