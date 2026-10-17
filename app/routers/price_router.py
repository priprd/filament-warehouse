from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone

from app.database import get_db
from app.models import Filament, PriceHistory, User
from app.auth import get_current_user
from app.schemas import PriceHistoryCreate, PriceHistoryResponse

router = APIRouter(prefix="/api/filaments", tags=["Price History"])

@router.post("/{filament_id}/prices", response_model=PriceHistoryResponse, status_code=status.HTTP_201_CREATED)
def add_price_history(
    filament_id: int,
    price_in: PriceHistoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    filament = db.query(Filament).filter(Filament.id == filament_id, Filament.user_id == current_user.id).first()
    if not filament:
        raise HTTPException(status_code=404, detail="Filament spool not found")

    new_price = PriceHistory(
        filament_id=filament.id,
        price=price_in.price,
        currency=price_in.currency,
        quantity_bought=price_in.quantity_bought,
        store_name=price_in.store_name,
        notes=price_in.notes,
        bought_at=price_in.bought_at or datetime.now(timezone.utc)
    )
    db.add(new_price)
    db.commit()
    db.refresh(new_price)
    return PriceHistoryResponse.model_validate(new_price)

@router.get("/{filament_id}/prices", response_model=List[PriceHistoryResponse])
def get_price_history(
    filament_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    filament = db.query(Filament).filter(Filament.id == filament_id, Filament.user_id == current_user.id).first()
    if not filament:
        raise HTTPException(status_code=404, detail="Filament spool not found")

    history = db.query(PriceHistory).filter(
        PriceHistory.filament_id == filament.id
    ).order_by(PriceHistory.bought_at.desc()).all()

    return [PriceHistoryResponse.model_validate(p) for p in history]
