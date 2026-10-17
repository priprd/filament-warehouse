from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from typing import Optional
from urllib.parse import urlencode
import secrets
import requests
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import AuditLog, User
from app.schemas import AuditLogResponse, UserRegister, UserLogin, GoogleAuthSchema, UserResponse, Token, UserUpdate
from app.auth import get_password_hash, verify_password, create_access_token, get_current_user, require_admin, verify_google_token

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.get("/status")
def auth_status():
    return {"auth_enabled": settings.FEATURE_AUTH_REQUIRED}

@router.post("/register", response_model=Token)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    # Check existing user
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pw = get_password_hash(user_in.password)
    new_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed_pw,
        avatar_url=f"https://api.dicebear.com/7.x/bottts/svg?seed={user_in.username}",
        role="user"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(data={"sub": str(new_user.id)})
    return Token(access_token=access_token, token_type="bearer", user=UserResponse.model_validate(new_user))

@router.post("/login", response_model=Token)
def login(login_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.username == login_in.username_or_email) | (User.email == login_in.username_or_email)
    ).first()

    if not user or not user.hashed_password or not verify_password(login_in.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username/email or password")
    if user.is_blocked or not user.is_active:
        raise HTTPException(status_code=403, detail="This account is blocked")

    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token, token_type="bearer", user=UserResponse.model_validate(user))

@router.post("/google", response_model=Token)
def google_auth(payload: GoogleAuthSchema, db: Session = Depends(get_db)):
    google_data = verify_google_token(payload.credential)
    google_id = google_data.get("sub")
    email = google_data.get("email")
    name = google_data.get("name", email.split("@")[0] if email else "MinionUser")
    picture = google_data.get("picture", f"https://api.dicebear.com/7.x/bottts/svg?seed={google_id}")

    # Find user by google_id or email
    user = db.query(User).filter((User.google_id == google_id) | (User.email == email)).first()

    if not user:
        # Create new Google user
        username = name.replace(" ", "_").lower()
        # ensure unique username
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            username = f"{username}_{google_id[:5]}"

        user = User(
            username=username,
            email=email,
            google_id=google_id,
            avatar_url=picture
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if not user.google_id:
            user.google_id = google_id
            db.commit()
    if user.is_blocked or not user.is_active:
        raise HTTPException(status_code=403, detail="This account is blocked")

    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token, token_type="bearer", user=UserResponse.model_validate(user))

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)

@router.get("/providers")
def oauth_providers():
    return [{"name": name, "label": provider.get("label", name.title())} for name, provider in settings.OAUTH_PROVIDERS.items()]

@router.get("/{provider}/authorize")
def oauth_authorize(provider: str):
    config = settings.OAUTH_PROVIDERS.get(provider)
    if not config or not config.get("client_id"):
        raise HTTPException(status_code=404, detail="OAuth provider is not configured")
    state = create_access_token({"provider": provider, "nonce": secrets.token_urlsafe(16)}, expires_delta=__import__("datetime").timedelta(minutes=10))
    params = {
        "client_id": config["client_id"],
        "redirect_uri": config.get("redirect_uri", settings.OAUTH_REDIRECT_URI),
        "response_type": "code",
        "scope": config.get("scope", "openid email profile"),
        "state": state,
    }
    return RedirectResponse(f"{config['authorize_url']}?{urlencode(params)}")

@router.get("/oauth/callback")
def oauth_callback(code: str, state: str, provider: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        claims = jwt.decode(state, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid OAuth state") from exc
    state_provider = claims.get("provider")
    if not isinstance(state_provider, str) or (provider and state_provider != provider):
        raise HTTPException(status_code=400, detail="OAuth provider mismatch")
    provider = state_provider
    config = settings.OAUTH_PROVIDERS.get(provider)
    if not config:
        raise HTTPException(status_code=404, detail="OAuth provider is not configured")
    token_response = requests.post(config["token_url"], data={
        "code": code, "client_id": config["client_id"], "client_secret": config.get("client_secret", ""),
        "redirect_uri": config.get("redirect_uri", settings.OAUTH_REDIRECT_URI), "grant_type": "authorization_code"
    }, timeout=10)
    token_response.raise_for_status()
    userinfo = requests.get(config["userinfo_url"], headers={"Authorization": f"Bearer {token_response.json()['access_token']}"}, timeout=10).json()
    email = userinfo.get("email")
    provider_id = userinfo.get("sub") or userinfo.get("id")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        username = (userinfo.get("name") or email.split("@")[0]).replace(" ", "_").lower()
        if db.query(User).filter(User.username == username).first():
            username = f"{username}_{provider_id[:6]}"
        user = User(username=username, email=email, oauth_provider=provider, oauth_subject=provider_id, avatar_url=userinfo.get("picture"))
        db.add(user)
        db.commit()
        db.refresh(user)
    if user.is_blocked or not user.is_active:
        raise HTTPException(status_code=403, detail="This account is blocked")
    return {"access_token": create_access_token({"sub": user.id}), "token_type": "bearer", "user": UserResponse.model_validate(user)}

@router.get("/users", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return db.query(User).order_by(User.created_at.desc()).all()

@router.get("/audit", response_model=list[AuditLogResponse])
def list_audit_logs(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(500).all()

@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, update: UserUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id and (update.role == "user" or update.is_blocked is True or update.is_active is False):
        raise HTTPException(status_code=400, detail="You cannot remove your own administrator access")
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user

@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
