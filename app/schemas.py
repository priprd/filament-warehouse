from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

# --- Auth Schemas ---
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    username_or_email: str
    password: str

class GoogleAuthSchema(BaseModel):
    credential: str  # Google JWT ID token from frontend

class UserUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    role: Optional[str] = Field(default=None, pattern="^(user|admin)$")
    is_blocked: Optional[bool] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    avatar_url: Optional[str] = None
    role: str
    is_blocked: bool
    is_active: bool
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    actor_user_id: Optional[int] = None
    actor_username: Optional[str] = None
    details: Optional[str] = None
    created_at: datetime

# --- Price History Schemas ---
class PriceHistoryCreate(BaseModel):
    price: float = Field(default=0.0)  # Allows any number (no minimum range constraint)
    currency: str = "EUR"
    quantity_bought: int = 1
    store_name: Optional[str] = None
    notes: Optional[str] = None
    bought_at: Optional[datetime] = None

class PriceHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filament_id: int
    price: float
    currency: str
    quantity_bought: int
    store_name: Optional[str] = None
    notes: Optional[str] = None
    bought_at: datetime

# --- Vendor Schemas ---
class VendorCreate(BaseModel):
    name: str
    website_url: Optional[str] = None
    logo_url: Optional[str] = None

class VendorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    website_url: Optional[str] = None
    logo_url: Optional[str] = None

# --- Filament Schemas ---
class FilamentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    material_type: str
    color_name: str
    color_hex: str = Field(default="#FFE135")  # Accepts HEX or RAL (e.g. RAL 1018, #FFE135)
    color_image_url: Optional[str] = None
    
    vendor_name: Optional[str] = None
    vendor_link: Optional[str] = None
    
    initial_weight_kg: float = Field(default=1.0)
    current_weight_kg: float = Field(default=1.0)
    spool_weight_g: float = Field(default=200.0)
    
    nfc_tag_uid: Optional[str] = None
    notes: Optional[str] = None
    
    # Purchase record (allow any number for price, plus editable buy/added date)
    buy_price: Optional[float] = None
    currency: str = Field(default="EUR")
    store_name: Optional[str] = None
    bought_at: Optional[datetime] = None

class FilamentUpdate(BaseModel):
    name: Optional[str] = None
    material_type: Optional[str] = None
    color_name: Optional[str] = None
    color_hex: Optional[str] = None
    color_image_url: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_link: Optional[str] = None
    initial_weight_kg: Optional[float] = None
    current_weight_kg: Optional[float] = None
    spool_weight_g: Optional[float] = None
    nfc_tag_uid: Optional[str] = None
    notes: Optional[str] = None
    bought_at: Optional[datetime] = None

class FilamentWeightUpdate(BaseModel):
    current_weight_kg: float = Field(..., ge=0.0)
    nfc_tag_uid: Optional[str] = None

class FilamentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    material_type: str
    color_name: str
    color_hex: str
    color_image_url: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_link: Optional[str] = None
    initial_weight_kg: float
    current_weight_kg: float
    spool_weight_g: float
    nfc_tag_uid: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    latest_price: Optional[float] = None
    latest_currency: Optional[str] = "EUR"
    price_history: List[PriceHistoryResponse] = []

# --- NFC Payload Schemas ---
class NfcScanPayload(BaseModel):
    nfc_tag_uid: str
    current_weight_kg: float = Field(..., ge=0.0)

class NfcScanResponse(BaseModel):
    success: bool
    message: str
    filament: Optional[FilamentResponse] = None
