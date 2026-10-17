"""
Minions Filaments Warehouse — Comprehensive Test Suite
======================================================
Tests run inside the container using ONLY packages already in requirements.txt.
No extra installs needed: pytest + httpx + sqlalchemy are already present.

Run from the running container:
    podman exec minions_warehouse_web pytest tests/ -v
"""

import os

# ── CRITICAL: override DATABASE_URL BEFORE any app module is imported ──────────
os.environ["DATABASE_URL"] = "sqlite://"   # pure in-memory
os.environ["TESTING"] = "true"
os.environ["FEATURE_AUTH_REQUIRED"] = "true"  # this suite covers protected mode

# ── Now set up the test database engine ───────────────────────────────────────
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

test_engine = create_engine(
    "sqlite://",                               # in-memory
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,                      # single shared connection
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# ── Patch app.database BEFORE importing app.main ──────────────────────────────
import app.database as _db_module
_db_module.engine = test_engine
_db_module.SessionLocal = TestingSession

# ── Now it is safe to import the FastAPI app ──────────────────────────────────
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, get_db


# ── Dependency override: all API requests use TestingSession ──────────────────
def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


# ── Fixtures ──────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def reset_db():
    """Fresh schema for every test — full isolation guaranteed."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    """
    Use TestClient as a context manager.
    """
    with TestClient(app) as c:
        yield c


# ── Helpers ───────────────────────────────────────────────────────────────────
def register_and_login(client, username="minion_bob", email="bob@warehouse.io", password="bananaPassword123"):
    """Registers and logs in a test user, returns authorization headers."""
    reg_res = client.post("/api/auth/register", json={
        "username": username,
        "email": email,
        "password": password
    })
    if reg_res.status_code == 200:
        token = reg_res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    # Fallback to login if user already registered
    login_res = client.post("/api/auth/login", json={
        "username_or_email": username,
        "password": password
    })
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_sample_filament(client, headers, *, nfc_uid="NFC-TEST-001", name="Test PLA", buy_price=25.0):
    """Create a filament spool and return the JSON response."""
    payload = {
        "name": name,
        "material_type": "PLA",
        "color_name": "Minion Yellow",
        "color_hex": "#FFE135",
        "vendor_name": "Bambu Lab",
        "vendor_link": "https://store.bambulab.com",
        "initial_weight_kg": 1.0,
        "current_weight_kg": 0.85,
        "spool_weight_g": 200.0,
        "nfc_tag_uid": nfc_uid,
        "notes": "Test spool",
        "buy_price": buy_price,
        "currency": "EUR",
    }
    res = client.post("/api/filaments", json=payload, headers=headers)
    assert res.status_code == 201, f"create filament failed: {res.text}"
    return res.json()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. UNLOGGED / UNAUTHENTICATED USER TESTS (TRULY CANNOT SEE OR MODIFY ANYTHING)
# ═══════════════════════════════════════════════════════════════════════════════
class TestUnauthenticatedAccess:
    """Verify that unauthenticated users are strictly blocked from all warehouse operations."""

    def test_unlogged_cannot_get_filaments_list(self, client):
        """Unlogged user cannot see filament stock list."""
        res = client.get("/api/filaments")
        assert res.status_code == 401
        assert res.json()["detail"] == "Could not validate credentials"

    def test_unlogged_cannot_get_single_filament(self, client):
        """Unlogged user cannot view specific spool details."""
        res = client.get("/api/filaments/1")
        assert res.status_code == 401

    def test_unlogged_cannot_create_filament(self, client):
        """Unlogged user cannot create new filament spools."""
        payload = {
            "name": "Hacked Filament",
            "material_type": "PLA",
            "color_name": "Red",
            "color_hex": "#FF0000",
            "initial_weight_kg": 1.0,
            "current_weight_kg": 1.0
        }
        res = client.post("/api/filaments", json=payload)
        assert res.status_code == 401

    def test_unlogged_cannot_update_filament(self, client):
        """Unlogged user cannot edit any filament."""
        res = client.put("/api/filaments/1", json={"name": "Hacked"})
        assert res.status_code == 401

    def test_unlogged_cannot_patch_filament_weight(self, client):
        """Unlogged user cannot update filament weight."""
        res = client.patch("/api/filaments/1/weight", json={"current_weight_kg": 0.1})
        assert res.status_code == 401

    def test_unlogged_cannot_delete_filament(self, client):
        """Unlogged user cannot delete any filament."""
        res = client.delete("/api/filaments/1")
        assert res.status_code == 401

    def test_unlogged_cannot_get_price_history(self, client):
        """Unlogged user cannot view purchase prices."""
        res = client.get("/api/filaments/1/prices")
        assert res.status_code == 401

    def test_unlogged_cannot_add_price_history(self, client):
        """Unlogged user cannot log purchase price history."""
        res = client.post("/api/filaments/1/prices", json={"price": 19.99})
        assert res.status_code == 401

    def test_unlogged_cannot_lookup_nfc(self, client):
        """Unlogged user cannot scan/lookup NFC tags."""
        res = client.get("/api/nfc/lookup/NFC-MINION-001")
        assert res.status_code == 401

    def test_unlogged_cannot_update_nfc_weight(self, client):
        """Unlogged user cannot update spool weight via NFC."""
        res = client.post("/api/nfc/update-weight", json={
            "nfc_tag_uid": "NFC-MINION-001",
            "current_weight_kg": 0.5
        })
        assert res.status_code == 401

    def test_unlogged_cannot_get_me(self, client):
        """Unlogged user cannot query auth profile."""
        res = client.get("/api/auth/me")
        assert res.status_code == 401

    def test_invalid_bearer_token_is_401(self, client):
        """Malformed or forged tokens are strictly rejected with 401."""
        res = client.get("/api/filaments", headers={"Authorization": "Bearer invalid.jwt.token"})
        assert res.status_code == 401

    def test_empty_bearer_token_is_401(self, client):
        """Empty or null tokens are rejected with 401."""
        res = client.get("/api/filaments", headers={"Authorization": "Bearer "})
        assert res.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# 2. AUTHENTICATED USER TESTS (SEE STOCKS, EDIT, LOG PRICES, SCAN NFC, CRUD)
# ═══════════════════════════════════════════════════════════════════════════════
class TestAuthenticatedWarehouse:
    """Verify that logged in users can see stocks, create, edit, log prices, and manage warehouse."""

    def test_logged_in_user_initially_sees_empty_stock(self, client):
        """A new registered user starts with 0 filaments."""
        headers = register_and_login(client, username="alice_minion", email="alice@m.io")
        res = client.get("/api/filaments", headers=headers)
        assert res.status_code == 200
        assert res.json() == []

    def test_logged_in_user_can_create_and_see_filament(self, client):
        """Logged in user can create a spool and immediately see it in warehouse stock."""
        headers = register_and_login(client, username="bob_builder", email="bob@m.io")
        spool = create_sample_filament(client, headers, name="Bambu Yellow PLA", buy_price=24.99)
        assert spool["name"] == "Bambu Yellow PLA"
        assert spool["material_type"] == "PLA"
        assert spool["current_weight_kg"] == 0.85
        assert spool["latest_price"] == 24.99

        # View in list
        res = client.get("/api/filaments", headers=headers)
        assert res.status_code == 200
        items = res.json()
        assert len(items) == 1
        assert items[0]["name"] == "Bambu Yellow PLA"

    def test_logged_in_user_can_view_single_spool_details(self, client):
        """Logged in user can fetch a specific spool by ID."""
        headers = register_and_login(client, username="kevin_minion", email="kevin@m.io")
        created = create_sample_filament(client, headers, name="Prusa PETG")
        fid = created["id"]
        res = client.get(f"/api/filaments/{fid}", headers=headers)
        assert res.status_code == 200
        assert res.json()["id"] == fid
        assert res.json()["name"] == "Prusa PETG"

    def test_logged_in_user_can_edit_spool(self, client):
        """Logged in user can edit spool name, notes, color, and vendor."""
        headers = register_and_login(client, username="stuart_minion", email="stuart@m.io")
        created = create_sample_filament(client, headers, name="Original Name")
        fid = created["id"]

        update_payload = {
            "name": "Updated Super PLA",
            "material_type": "PLA",
            "color_name": "Bright Gold",
            "color_hex": "#FFD700",
            "notes": "Optimal printing at 215C"
        }
        res = client.put(f"/api/filaments/{fid}", json=update_payload, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "Updated Super PLA"
        assert data["color_name"] == "Bright Gold"
        assert data["notes"] == "Optimal printing at 215C"

    def test_logged_in_user_can_update_remaining_weight(self, client):
        """Logged in user can patch spool weight when filament is used."""
        headers = register_and_login(client, username="dave_minion", email="dave@m.io")
        created = create_sample_filament(client, headers)
        fid = created["id"]

        res = client.patch(f"/api/filaments/{fid}/weight", json={"current_weight_kg": 0.45}, headers=headers)
        assert res.status_code == 200
        assert res.json()["current_weight_kg"] == 0.45

        # Verify stock list reflects updated weight
        list_res = client.get("/api/filaments", headers=headers)
        assert list_res.json()[0]["current_weight_kg"] == 0.45

    def test_logged_in_user_can_add_and_view_price_history(self, client):
        """Logged in user can record multiple purchases over time with any price."""
        headers = register_and_login(client, username="carl_minion", email="carl@m.io")
        created = create_sample_filament(client, headers, buy_price=20.0)
        fid = created["id"]

        # Log second purchase
        p2_res = client.post(f"/api/filaments/{fid}/prices", json={
            "price": 17.50,
            "currency": "EUR",
            "store_name": "Black Friday Sale",
            "notes": "Bought 3 spools in bundle"
        }, headers=headers)
        assert p2_res.status_code == 201
        assert p2_res.json()["price"] == 17.50

        # Fetch history
        hist_res = client.get(f"/api/filaments/{fid}/prices", headers=headers)
        assert hist_res.status_code == 200
        prices = hist_res.json()
        assert len(prices) == 2
        assert prices[0]["price"] == 17.50  # Latest first
        assert prices[1]["price"] == 20.0

    def test_logged_in_user_can_use_nfc_scanner(self, client):
        """Logged in user can lookup spool by NFC tag and scan new weight."""
        headers = register_and_login(client, username="phil_minion", email="phil@m.io")
        create_sample_filament(client, headers, nfc_uid="NFC-PHIL-999")

        # Lookup
        lookup_res = client.get("/api/nfc/lookup/NFC-PHIL-999", headers=headers)
        assert lookup_res.status_code == 200
        assert lookup_res.json()["nfc_tag_uid"] == "NFC-PHIL-999"

        # Update weight via NFC scan
        scan_res = client.post("/api/nfc/update-weight", json={
            "nfc_tag_uid": "NFC-PHIL-999",
            "current_weight_kg": 0.35
        }, headers=headers)
        assert scan_res.status_code == 200
        assert scan_res.json()["success"] is True
        assert scan_res.json()["filament"]["current_weight_kg"] == 0.35

    def test_logged_in_user_can_delete_spool(self, client):
        """Logged in user can remove a finished spool."""
        headers = register_and_login(client, username="tim_minion", email="tim@m.io")
        created = create_sample_filament(client, headers)
        fid = created["id"]

        del_res = client.delete(f"/api/filaments/{fid}", headers=headers)
        assert del_res.status_code == 204

        # Verify it's gone
        get_res = client.get(f"/api/filaments/{fid}", headers=headers)
        assert get_res.status_code == 404

    def test_user_stock_isolation(self, client):
        """User A and User B cannot view, modify, or delete each other's filaments."""
        headers_a = register_and_login(client, username="user_alpha", email="alpha@m.io", password="passAlpha123")
        headers_b = register_and_login(client, username="user_beta", email="beta@m.io", password="passBeta123")

        # User A creates a spool
        spool_a = create_sample_filament(client, headers_a, name="Alpha Spool", nfc_uid="NFC-ALPHA")

        # User B lists filaments -> empty
        res_b = client.get("/api/filaments", headers=headers_b)
        assert res_b.json() == []

        # User B attempts to access User A's spool -> 404
        assert client.get(f"/api/filaments/{spool_a['id']}", headers=headers_b).status_code == 404
        assert client.put(f"/api/filaments/{spool_a['id']}", json={"name": "Hacked"}, headers=headers_b).status_code == 404
        assert client.delete(f"/api/filaments/{spool_a['id']}", headers=headers_b).status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# 3. AUTHENTICATION (REGISTER / LOGIN) UNIT TESTS
# ═══════════════════════════════════════════════════════════════════════════════
class TestAuthFlow:
    def test_register_and_login_flow(self, client):
        reg = client.post("/api/auth/register", json={
            "username": "minion_master_test",
            "email": "master@warehouse.io",
            "password": "bananaMaster123"
        })
        assert reg.status_code == 200
        assert "access_token" in reg.json()

        # Login with username
        login_u = client.post("/api/auth/login", json={
            "username_or_email": "minion_master_test",
            "password": "bananaMaster123"
        })
        assert login_u.status_code == 200
        assert "access_token" in login_u.json()

        # Login with email
        login_e = client.post("/api/auth/login", json={
            "username_or_email": "master@warehouse.io",
            "password": "bananaMaster123"
        })
        assert login_e.status_code == 200
        assert "access_token" in login_e.json()

    def test_wrong_password_rejected(self, client):
        client.post("/api/auth/register", json={
            "username": "tester", "email": "tester@m.io", "password": "correct_pass"
        })
        res = client.post("/api/auth/login", json={
            "username_or_email": "tester", "password": "wrong_pass"
        })
        assert res.status_code == 401
        assert "Incorrect" in res.json()["detail"]

    def test_duplicate_user_rejected(self, client):
        client.post("/api/auth/register", json={
            "username": "unique_user", "email": "u1@m.io", "password": "password123"
        })
        res = client.post("/api/auth/register", json={
            "username": "unique_user", "email": "u2@m.io", "password": "password123"
        })
        assert res.status_code == 400
        assert "Username" in res.json()["detail"]
