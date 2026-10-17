from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from app.database import get_db
from app.models import AuditLog, Filament, PriceHistory, User
from app.auth import get_current_user
from app.schemas import FilamentCreate, FilamentUpdate, FilamentWeightUpdate, FilamentResponse, PriceHistoryResponse

router = APIRouter(prefix="/api/filaments", tags=["Filaments"])

def record_audit(db: Session, action: str, filament: Filament, user: User, details: str = None):
    db.add(AuditLog(
        action=action,
        entity_type="filament",
        entity_id=filament.id,
        actor_user_id=user.id,
        actor_username=user.username,
        details=details,
    ))

def build_filament_response(filament: Filament) -> FilamentResponse:
    latest_price = None
    latest_currency = "EUR"
    if filament.price_history:
        latest = filament.price_history[0]
        latest_price = latest.price
        latest_currency = latest.currency

    history_responses = [PriceHistoryResponse.model_validate(p) for p in filament.price_history]

    return FilamentResponse(
        id=filament.id,
        user_id=filament.user_id,
        name=filament.name,
        material_type=filament.material_type,
        color_name=filament.color_name,
        color_hex=filament.color_hex,
        color_image_url=filament.color_image_url,
        vendor_name=filament.vendor_name,
        vendor_link=filament.vendor_link,
        initial_weight_kg=filament.initial_weight_kg,
        current_weight_kg=filament.current_weight_kg,
        spool_weight_g=filament.spool_weight_g,
        nfc_tag_uid=filament.nfc_tag_uid,
        notes=filament.notes,
        created_at=filament.created_at,
        updated_at=filament.updated_at,
        latest_price=latest_price,
        latest_currency=latest_currency,
        price_history=history_responses
    )

@router.get("", response_model=List[FilamentResponse])
def get_filaments(
    material: Optional[str] = None,
    vendor: Optional[str] = None,
    search: Optional[str] = None,
    low_stock: Optional[bool] = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Filament).filter(Filament.user_id == current_user.id)

    if material:
        query = query.filter(Filament.material_type.ilike(f"%{material}%"))
    if vendor:
        query = query.filter(Filament.vendor_name.ilike(f"%{vendor}%"))
    if search:
        query = query.filter(
            (Filament.name.ilike(f"%{search}%")) |
            (Filament.color_name.ilike(f"%{search}%")) |
            (Filament.notes.ilike(f"%{search}%"))
        )
    if low_stock:
        query = query.filter(Filament.current_weight_kg <= Filament.initial_weight_kg * 0.2)

    filaments = query.order_by(Filament.updated_at.desc()).all()
    return [build_filament_response(f) for f in filaments]

@router.post("", response_model=FilamentResponse, status_code=status.HTTP_201_CREATED)
def create_filament(
    filament_in: FilamentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    created_date = filament_in.bought_at or datetime.now(timezone.utc)

    new_filament = Filament(
        user_id=current_user.id,
        name=filament_in.name,
        material_type=filament_in.material_type.upper(),
        color_name=filament_in.color_name,
        color_hex=filament_in.color_hex,
        color_image_url=filament_in.color_image_url,
        vendor_name=filament_in.vendor_name,
        vendor_link=filament_in.vendor_link,
        initial_weight_kg=filament_in.initial_weight_kg,
        current_weight_kg=filament_in.current_weight_kg,
        spool_weight_g=filament_in.spool_weight_g,
        nfc_tag_uid=filament_in.nfc_tag_uid,
        notes=filament_in.notes,
        created_at=created_date,
        updated_at=created_date
    )
    try:
        db.add(new_filament)
        db.commit()
        db.refresh(new_filament)
    except IntegrityError as exc:
        db.rollback()
        if new_filament.nfc_tag_uid:
            raise HTTPException(
                status_code=400,
                detail="NFC Tag UID already exists. Use a unique tag or leave it blank."
            ) from exc
        raise HTTPException(status_code=400, detail="Filament could not be saved.") from exc

    record_audit(db, "created", new_filament, current_user, f"Created spool '{new_filament.name}'")
    db.commit()

    if filament_in.buy_price is not None:
        price_rec = PriceHistory(
            filament_id=new_filament.id,
            price=filament_in.buy_price,
            currency=filament_in.currency,
            store_name=filament_in.store_name or filament_in.vendor_name,
            notes="Initial Purchase",
            bought_at=created_date
        )
        try:
            db.add(price_rec)
            db.commit()
            db.refresh(new_filament)
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=400, detail="Could not save purchase history for this filament.") from exc

    return build_filament_response(new_filament)

@router.get("/{filament_id}", response_model=FilamentResponse)
def get_filament(
    filament_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    filament = db.query(Filament).filter(Filament.id == filament_id, Filament.user_id == current_user.id).first()
    if not filament:
        raise HTTPException(status_code=404, detail="Filament spool not found")
    return build_filament_response(filament)

@router.put("/{filament_id}", response_model=FilamentResponse)
def update_filament(
    filament_id: int,
    filament_in: FilamentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    filament = db.query(Filament).filter(Filament.id == filament_id, Filament.user_id == current_user.id).first()
    if not filament:
        raise HTTPException(status_code=404, detail="Filament spool not found")

    update_data = filament_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "material_type" and value:
            value = value.upper()
        if field == "bought_at" and value:
            filament.created_at = value
        else:
            setattr(filament, field, value)

    filament.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
        db.refresh(filament)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="NFC Tag UID already exists. Use a unique tag or leave it blank."
        ) from exc
    record_audit(db, "updated", filament, current_user, f"Updated spool '{filament.name}'")
    db.commit()
    return build_filament_response(filament)

@router.patch("/{filament_id}/weight", response_model=FilamentResponse)
def update_filament_weight(
    filament_id: int,
    weight_in: FilamentWeightUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    filament = db.query(Filament).filter(Filament.id == filament_id, Filament.user_id == current_user.id).first()
    if not filament:
        raise HTTPException(status_code=404, detail="Filament spool not found")

    filament.current_weight_kg = weight_in.current_weight_kg
    if weight_in.nfc_tag_uid:
        filament.nfc_tag_uid = weight_in.nfc_tag_uid

    filament.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()
        db.refresh(filament)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="NFC Tag UID already exists. Use a unique tag or leave it blank."
        ) from exc
    return build_filament_response(filament)

@router.delete("/{filament_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_filament(
    filament_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    filament = db.query(Filament).filter(Filament.id == filament_id, Filament.user_id == current_user.id).first()
    if not filament:
        raise HTTPException(status_code=404, detail="Filament spool not found")

    record_audit(db, "deleted", filament, current_user, f"Deleted spool '{filament.name}'")
    db.delete(filament)
    db.commit()
    return None
