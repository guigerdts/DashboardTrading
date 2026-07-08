"""Imports module router — MT5 CSV upload, preview, and confirm.

Endpoints
---------
- POST /api/imports/mt5/preview  → PreviewResponse (200)
- POST /api/imports/mt5/confirm  → ImportResult (200)
"""

from fastapi import APIRouter, Depends, File, UploadFile

from app.modules.imports.dependencies import get_import_service
from app.modules.imports.schemas import ImportResult, PreviewResponse
from app.modules.imports.service import ImportService

router = APIRouter(prefix="/api/imports/mt5", tags=["Imports"])


@router.post("/preview", response_model=PreviewResponse)
async def preview_mt5(
    file: UploadFile = File(...),
    svc: ImportService = Depends(get_import_service),
):
    """Preview an MT5 CSV file: parse, normalize, validate.

    Read-only — never writes to the database.
    Returns a ``PreviewResponse`` with per-row valid/invalid status.
    """
    return await svc.preview(file)


@router.post("/confirm", response_model=ImportResult)
async def confirm_mt5(
    file: UploadFile = File(...),
    svc: ImportService = Depends(get_import_service),
):
    """Confirm and import an MT5 CSV file.

    Re-executes the full pipeline from scratch (parser → normalizer →
    validator → persistence). Valid rows are imported via ``TradeService.create()``
    with savepoint isolation.

    Returns an ``ImportResult`` with per-row import/skip/error status.
    """
    return await svc.confirm(file)
