# Minions Filaments Warehouse 🍌🧵

> A modern, highly responsive 3D printing filament warehouse web application built in Python with **FastAPI**, **SQLAlchemy** (PostgreSQL/MySQL/SQLite), **Google Auth & Password Login**, **Historical Purchase Price Tracking**, **Web NFC Spool Weight Scanner**, **Minions Easter Eggs**, and **Versioned Docker Containerization**.

---

## 🌟 Key Features

1. **Filament Inventory Management**:
   - Track Filament Name, Material Type (PLA, PETG, ABS, TPU, ASA, PC, Silk, etc.), Color preview image & HEX code, Vendor name & URL, Initial & Remaining weight (in kg/g).
   - Dynamic remaining spool weight indicator with low stock alert (< 20%).

2. **Historical Buy Price Tracking**:
   - Shows latest buy price on filament cards.
   - Preserves complete purchase history over time (price, currency, store name, quantity bought, notes).

3. **Authentication**:
   - **Google Sign-In** (OAuth2 / OpenID Connect).
   - **Username & Password** authentication with bcrypt hashing & JWT tokens.
   - Configured bootstrap admin, JWT sessions, user/admin roles, blocked accounts, and admin-only user management.
   - Multiple OpenID Connect providers can be configured through `OAUTH_PROVIDERS_YAML`.

4. **Database Backends**:
   - Seamless support for **PostgreSQL** (`postgresql+psycopg2://...`), **MySQL** (`mysql+pymysql://...`), and **SQLite** (`sqlite:///./filaments.db`) via `DATABASE_URL` environment variable.

5. **NFC Spool Weight Integration**:
   - Native browser **Web NFC API** (`NDEFReader`) on supported mobile devices.
   - **Interactive Desktop NFC Simulator** to simulate scanning tag UIDs and updating remaining spool weight.

6. **Minions Theme & Easter Eggs 🍌**:
   - Minion yellow (`#FFE135`) & blue aesthetic, glassmorphic cards, Google Fonts.
   - Web Audio API voice synthesizer ("Bello!", "Banana!", "Poopaye!").
   - Falling Banana 🍌 canvas particle animation overlay.
   - Single-eye (Stuart) vs Two-eye (Bob) Minion goggle toggle.

7. **Containerized & Versioned**:
   - Production `Dockerfile`, `docker-compose.yml`, `VERSION` (`v1.0.0`), and `build-container.sh` tag versioning script.

---

## 🚀 Quick Start (Podman)

### 1. Run Application
```bash
podman compose up -d --build
```
Open your browser at `http://localhost:8000`.

---

## 🧪 Running Automated Tests

Run the test suite inside a disposable container:
```bash
podman compose run --rm -e TESTING=true -e DATABASE_URL=sqlite:// web pytest tests/test_api.py -v
```

---

## 🐳 Docker Container & Versioning

### Build Versioned Container Image
Run the versioning build script:
```bash
./build-container.sh
```
This builds and tags Docker images as:
- `minions-filaments-warehouse:v1.0.0`
- `minions-filaments-warehouse:latest`

### Run with Podman Compose / Docker Compose (FastAPI + PostgreSQL)
```bash
podman compose up -d
# OR
docker compose up -d
```

---

## 🔑 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLAlchemy DB Connection String | `sqlite:///./filaments.db` |
| `SECRET_KEY` | JWT Secret Key | `bello_minions_secret_key...` |
| `DEFAULT_ADMIN_USERNAME` | Initial administrator username | `minion_master` |
| `DEFAULT_ADMIN_PASSWORD` | Initial administrator password | `banana123` |
| `DEFAULT_ADMIN_EMAIL` | Initial administrator email | `stuart@minions-warehouse.io` |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID | `""` |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client secret | `""` |
| `OAUTH_REDIRECT_URI` | OAuth callback URL | `http://localhost:8000/api/auth/oauth/callback` |
| `OAUTH_PROVIDERS_YAML` | YAML map of provider settings | `{}` |

Set `auth_enabled` to `false` in `config.yaml` for open access. In that mode the warehouse is usable without login; when it is `true`, the page requires login before showing inventory actions.

Example provider configuration:
```yaml
oauth_providers:
  google:
    label: Google
    client_id: "..."
    client_secret: "..."
    authorize_url: https://accounts.google.com/o/oauth2/v2/auth
    token_url: https://oauth2.googleapis.com/token
    userinfo_url: https://openidconnect.googleapis.com/v1/userinfo
    scope: openid email profile
```
