from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.models import Filament, NfcScanLog, User
from app.auth import get_current_user
from app.schemas import NfcScanPayload, NfcScanResponse, FilamentResponse
from app.routers.filament_router import build_filament_response

router = APIRouter(prefix="/api/nfc", tags=["NFC Tag Spool Scanner"])

@router.get("/lookup/{nfc_tag_uid}", response_model=FilamentResponse)
def lookup_nfc_filament(
    nfc_tag_uid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    filament = db.query(Filament).filter(Filament.nfc_tag_uid == nfc_tag_uid, Filament.user_id == current_user.id).first()
    if not filament:
        raise HTTPException(
            status_code=404,
            detail=f"No spool registered with NFC Tag UID '{nfc_tag_uid}'"
        )
    return build_filament_response(filament)

@router.post("/update-weight", response_model=NfcScanResponse)
def update_weight_via_nfc(
    payload: NfcScanPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    filament = db.query(Filament).filter(Filament.nfc_tag_uid == payload.nfc_tag_uid, Filament.user_id == current_user.id).first()
    if not filament:
        return NfcScanResponse(
            success=False,
            message=f"No filament spool registered with NFC Tag UID '{payload.nfc_tag_uid}'"
        )

    old_weight = filament.current_weight_kg
    filament.current_weight_kg = payload.current_weight_kg
    filament.updated_at = datetime.now(timezone.utc)

    weight_change = payload.current_weight_kg - old_weight
    scan_log = NfcScanLog(
        filament_id=filament.id,
        nfc_tag_uid=payload.nfc_tag_uid,
        scanned_weight_kg=payload.current_weight_kg,
        weight_change_kg=weight_change
    )
    db.add(scan_log)
    db.commit()
    db.refresh(filament)

    return NfcScanResponse(
        success=True,
        message=f"Updated weight for '{filament.name}' ({filament.color_name}) to {payload.current_weight_kg:.2f} kg",
        filament=build_filament_response(filament)
    )
