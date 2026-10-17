from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # Null if only Google login
    google_id = Column(String(255), unique=True, index=True, nullable=True)
    oauth_provider = Column(String(50), nullable=True)
    oauth_subject = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    is_blocked = Column(Boolean, default=False, nullable=False)
    role = Column(String(20), default="user", nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now)

    filaments = relationship("Filament", back_populates="owner", cascade="all, delete-orphan")

class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), unique=True, index=True, nullable=False)
    website_url = Column(String(500), nullable=True)
    logo_url = Column(String(500), nullable=True)

    filaments = relationship("Filament", back_populates="vendor")

class Filament(Base):
    __tablename__ = "filaments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False, index=True)
    material_type = Column(String(50), nullable=False, index=True)  # e.g., PLA, PETG, ABS, TPU, ASA, PC, Silk
    color_name = Column(String(100), nullable=False)
    color_hex = Column(String(10), nullable=False, default="#FFE135")
    color_image_url = Column(String(500), nullable=True)
    
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    vendor_name = Column(String(150), nullable=True)
    vendor_link = Column(String(500), nullable=True)

    initial_weight_kg = Column(Float, nullable=False, default=1.0)
    current_weight_kg = Column(Float, nullable=False, default=1.0)
    spool_weight_g = Column(Float, nullable=False, default=200.0)  # Empty spool weight
    
    nfc_tag_uid = Column(String(100), unique=True, index=True, nullable=True)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    owner = relationship("User", back_populates="filaments")
    vendor = relationship("Vendor", back_populates="filaments")
    price_history = relationship("PriceHistory", back_populates="filament", cascade="all, delete-orphan", order_by="desc(PriceHistory.bought_at)")
    nfc_logs = relationship("NfcScanLog", back_populates="filament", cascade="all, delete-orphan")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(30), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, default="filament")
    entity_id = Column(Integer, nullable=True, index=True)
    actor_user_id = Column(Integer, nullable=True, index=True)
    actor_username = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    filament_id = Column(Integer, ForeignKey("filaments.id"), nullable=False)
    price = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default="EUR")
    quantity_bought = Column(Integer, default=1)
    store_name = Column(String(150), nullable=True)
    notes = Column(String(255), nullable=True)
    bought_at = Column(DateTime, default=utc_now)

    filament = relationship("Filament", back_populates="price_history")

class NfcScanLog(Base):
    __tablename__ = "nfc_scan_logs"

    id = Column(Integer, primary_key=True, index=True)
    filament_id = Column(Integer, ForeignKey("filaments.id"), nullable=False)
    nfc_tag_uid = Column(String(100), nullable=False)
    scanned_weight_kg = Column(Float, nullable=False)
    weight_change_kg = Column(Float, nullable=True)
    scanned_at = Column(DateTime, default=utc_now)

    filament = relationship("Filament", back_populates="nfc_logs")
