# Minions Filaments Warehouse 🍌🧵

> A 3D printing filament warehouse built with **FastAPI** and **SQLAlchemy**, with account-based access, price history, NFC spool weight scanning, and container/Kubernetes deployment support.

---

## 🌟 Key Features

1. **Filament Inventory Management**:
   - Track Filament Name, Material Type (PLA, PETG, ABS, TPU, ASA, PC, Silk, etc.), Color preview image & HEX code, Vendor name & URL, Initial & Remaining weight (in kg/g).
   - Dynamic remaining spool weight indicator with low stock alert (< 20%).

2. **Historical Buy Price Tracking**:
   - Shows latest buy price on filament cards.
   - Preserves complete purchase history over time (price, currency, store name, quantity bought, notes).

3. **Authentication**:
   - Google Sign-In (OAuth2 / OpenID Connect) when configured.
   - **Username & Password** authentication with bcrypt hashing & JWT tokens.
   - Optional bootstrap admin, JWT sessions, user/admin roles, blocked accounts, and admin-only user management.
   - Multiple OpenID Connect providers can be configured through `OAUTH_PROVIDERS_YAML`.

4. **Database Backends**:
   - Seamless support for **PostgreSQL** (`postgresql+psycopg2://...`), **MySQL** (`mysql+pymysql://...`), and **SQLite** (`sqlite:///./filaments.db`) via `DATABASE_URL` environment variable.

5. **NFC Spool Weight Integration**:
   - Native browser **Web NFC API** (`NDEFReader`) on supported mobile devices.
   - **Interactive Desktop NFC Simulator** to simulate scanning tag UIDs and updating remaining spool weight.

6. **Containerized & Versioned**:
   - Production `Dockerfile`, `docker-compose.yml`, `VERSION` (`v1.0.0`), and `build-container.sh` tag versioning script.

---

## 🚀 Quick Start (Podman)

### 1. Run Application
```bash
podman compose up -d --build
```
Open your browser at `http://localhost:8000`.

---

## Running Automated Tests

Install the listed dependencies and run the complete suite:
```bash
python3 -m pip install -r requirements.txt
python3 -m pytest tests/ -q
```

---

## 🐳 Docker Container & Versioning

### Build a local container image
Run the versioning build script:
```bash
./build-container.sh
```
This builds and tags Docker images as:
- `minions-filaments-warehouse:v1.0.0`
- `minions-filaments-warehouse:latest`

### Run with Podman Compose / Docker Compose
```bash
podman compose up -d
# OR
docker compose up -d
```

### Free GitHub Container Registry publishing

The GitHub Actions workflow runs the full test suite and builds the `Containerfile` on pull requests. Pushes to `main` and version tags (`v*`) publish `ghcr.io/<owner>/<repository>` using the built-in `GITHUB_TOKEN`; no paid registry or third-party credentials are needed. For a public project, make the published GHCR package public in its GitHub package settings so image storage and downloads stay on the public/free path. GitHub-hosted Actions minutes are subject to the repository/account's free quota.

## Kubernetes

Edit the image in `deploy/kubernetes.yaml` to your GHCR package, then configure a persistent JWT secret and initial admin password before applying:

```bash
kubectl create secret generic filaments-warehouse-secrets \
  --from-literal=secret-key="$(openssl rand -hex 32)" \
  --from-literal=admin-username=admin \
  --from-literal=admin-password='REPLACE_WITH_A_LONG_UNIQUE_PASSWORD' \
  --from-literal=admin-email=admin@example.com
kubectl apply -f deploy/kubernetes.yaml
kubectl port-forward service/filaments-warehouse 8000:80
```

Replace `ghcr.io/owner/repository:latest` with the lowercase path to your GHCR image. The manifest provides a ConfigMap-mounted `config.yaml` and runs one replica with SQLite on a 1 GiB persistent volume claim. Keep one replica when using SQLite; use an external PostgreSQL/MySQL database via the `database-url` Secret key or `DATABASE_URL` environment variable if you need multiple replicas. Non-secret environment settings override the ConfigMap. Optional Secret keys `google-client-id`, `google-client-secret`, and `oauth-providers-yaml` configure OAuth. `/livez` checks that the app process is alive; `/readyz` also checks database connectivity. The app runs as a non-root user.

---

## 🔑 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WAREHOUSE_CONFIG_FILE` | YAML configuration file path | `config.yaml` |
| `DATABASE_URL` | SQLAlchemy DB connection string (overrides DB fields in YAML) | `sqlite:///./filaments.db` |
| `DB_TYPE`, `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | Build the database URL when `DATABASE_URL` is unset | SQLite / local |
| `FEATURE_AUTH_REQUIRED` | Require a valid user token for warehouse APIs | `true` |
| `SECRET_KEY` | Stable JWT signing key; set it in production and store it as a Kubernetes Secret | generated per process if unset |
| `DEFAULT_ADMIN_USERNAME` | Username for the initial administrator | `admin` |
| `DEFAULT_ADMIN_PASSWORD` | Initial administrator password; no admin is bootstrapped when unset | unset |
| `DEFAULT_ADMIN_EMAIL` | Initial administrator email | `admin@example.invalid` |
| `PORT` | HTTP listen port | `8000` |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID | `""` |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client secret | `""` |
| `OAUTH_REDIRECT_URI` | OAuth callback URL | `http://localhost:8000/api/auth/oauth/callback` |
| `OAUTH_PROVIDERS_YAML` | YAML map of provider settings | `{}` |

Environment variables override values from `config.yaml`. Invalid YAML or invalid boolean settings stop startup with an explicit error. `config.yaml` does not contain a usable default admin password: set `DEFAULT_ADMIN_PASSWORD` (or `default_admin_password` in a private config file) to create the initial admin during startup. When auth is enabled and no bootstrap admin is configured, users can register and sign in but no administrator account is created. Never disable auth on an internet-facing deployment.

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
