"""Local preview, temporary matching and snapshot export; no catalog writes."""
import json
import zipfile
from xml.etree.ElementTree import ParseError
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool
from openpyxl.utils.exceptions import InvalidFileException
from ..st_preview import build_st_preview
from ..data_loader import get_nuvoton_parts
from ..matcher import find_matches, CORE_RANK
from ..workspace_matching import WorkspaceRequest, match_workspace
from ..comparison_export import create_snapshot, export_xlsx, MAX_BYTES

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


@router.post("/workspace/match")
def workspace_match(request: WorkspaceRequest):
    try:
        catalog = get_nuvoton_parts()
        result = match_workspace(request, catalog, find_matches, CORE_RANK)
        payload, token = create_snapshot(result, catalog)
        result["comparison_snapshot_json"] = payload
        result["snapshot_token"] = token
        return result
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


class ExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    snapshot_json: str = Field(max_length=MAX_BYTES)
    token: str = Field(pattern=r"^[0-9a-f]{64}$")
    selected: list[str] = Field(min_length=1, max_length=3)


@router.post("/workspace/export-xlsx")
async def export_workspace(request: Request):
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > 1_000_000:
            raise HTTPException(status_code=413, detail="Export request exceeds size limit")
        chunks.append(chunk)
    try:
        data = ExportRequest.model_validate(json.loads(b"".join(chunks)))
        content = await run_in_threadpool(export_xlsx, data.snapshot_json, data.token, data.selected)
    except (ValueError, TypeError, KeyError, RecursionError) as error:
        raise HTTPException(status_code=422, detail="Export rejected: " + str(error)[:300])
    return Response(content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="mcu-comparison.xlsx"', "Cache-Control":"no-store"})
