from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os

from app.config import settings
from app.database import engine, Base, SessionLocal, ensure_auth_columns
from app.models import Filament, PriceHistory, User
from app.auth import get_password_hash
from app.routers import filament_router, price_router, nfc_router, auth_router

# Initialize tables
Base.metadata.create_all(bind=engine)
ensure_auth_columns()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Filaments Warehouse API - 3D Printing Filament & NFC Weight Tracking"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static and Templates
base_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(base_dir, "static")
templates_dir = os.path.join(os.path.dirname(base_dir), "templates")

if not os.path.exists(static_dir):
    os.makedirs(static_dir)
if not os.path.exists(templates_dir):
    os.makedirs(templates_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# Include API Routers
app.include_router(auth_router.router)
app.include_router(filament_router.router)
app.include_router(price_router.router)
app.include_router(nfc_router.router)

@app.on_event("startup")
def seed_default_data():
    """Seed sample filaments on first run if database is empty"""
    if os.getenv("TESTING") == "true":
        return

    db = SessionLocal()
    try:
        default_admin = db.query(User).filter(User.username == settings.DEFAULT_ADMIN_USERNAME).first()
        if not default_admin:
            db.add(User(
                username=settings.DEFAULT_ADMIN_USERNAME,
                email=settings.DEFAULT_ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
                avatar_url=f"https://api.dicebear.com/7.x/bottts/svg?seed={settings.DEFAULT_ADMIN_USERNAME}",
                role="admin",
            ))
            db.commit()
        if db.query(Filament).count() == 0:
            samples = [
                {
                    "name": "Bambu Lab High Speed PLA",
                    "material_type": "PLA",
                    "color_name": "Jade Green",
                    "color_hex": "#00897B",
                    "vendor_name": "Bambu Lab",
                    "vendor_link": "https://store.bambulab.com/products/pla-basic",
                    "initial_weight_kg": 1.0,
                    "current_weight_kg": 0.85,
                    "spool_weight_g": 210,
                    "nfc_tag_uid": "NFC-SPOOL-001",
                    "notes": "High speed PLA, 220°C nozzle, 35mm/s",
                    "buy_price": 24.99,
                    "currency": "EUR"
                },
                {
                    "name": "Prusament PETG",
                    "material_type": "PETG",
                    "color_name": "Prusament Blue",
                    "color_hex": "#1E88E5",
                    "vendor_name": "Prusa Research",
                    "vendor_link": "https://www.prusa3d.com/category/prusament-petg/",
                    "initial_weight_kg": 1.0,
                    "current_weight_kg": 0.42,
                    "spool_weight_g": 190,
                    "nfc_tag_uid": "NFC-SPOOL-002",
                    "notes": "Durable PETG, good layer adhesion",
                    "buy_price": 29.90,
                    "currency": "EUR"
                },
                {
                    "name": "Sunlu Silk PLA",
                    "material_type": "SILK",
                    "color_name": "Deep Purple",
                    "color_hex": "#7B1FA2",
                    "vendor_name": "Sunlu",
                    "vendor_link": "https://www.sunlu.com/",
                    "initial_weight_kg": 1.0,
                    "current_weight_kg": 0.15,
                    "spool_weight_g": 180,
                    "nfc_tag_uid": "NFC-SPOOL-003",
                    "notes": "Silk finish, low stock!",
                    "buy_price": 18.50,
                    "currency": "EUR"
                },
                {
                    "name": "eSUN ABS+",
                    "material_type": "ABS",
                    "color_name": "Silver Grey",
                    "color_hex": "#B0BEC5",
                    "vendor_name": "eSUN",
                    "vendor_link": "https://www.esun3d.com/",
                    "initial_weight_kg": 1.0,
                    "current_weight_kg": 0.90,
                    "spool_weight_g": 200,
                    "nfc_tag_uid": "NFC-SPOOL-004",
                    "notes": "Heat resistant ABS+, 240°C",
                    "buy_price": 21.00,
                    "currency": "EUR"
                }
            ]

            for s in samples:
                fil = Filament(
                    user_id=1,
                    name=s["name"],
                    material_type=s["material_type"],
                    color_name=s["color_name"],
                    color_hex=s["color_hex"],
                    vendor_name=s["vendor_name"],
                    vendor_link=s["vendor_link"],
                    initial_weight_kg=s["initial_weight_kg"],
                    current_weight_kg=s["current_weight_kg"],
                    spool_weight_g=s["spool_weight_g"],
                    nfc_tag_uid=s["nfc_tag_uid"],
                    notes=s["notes"]
                )
                db.add(fil)
                db.commit()
                db.refresh(fil)

                p1 = PriceHistory(
                    filament_id=fil.id,
                    price=s["buy_price"] + 2.50,
                    currency=s["currency"],
                    store_name=s["vendor_name"],
                    notes="Original purchase"
                )
                p2 = PriceHistory(
                    filament_id=fil.id,
                    price=s["buy_price"],
                    currency=s["currency"],
                    store_name=s["vendor_name"] + " Sale",
                    notes="Discounted batch"
                )
                db.add(p1)
                db.add(p2)
                db.commit()

    finally:
        db.close()

@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"title": settings.PROJECT_NAME}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
