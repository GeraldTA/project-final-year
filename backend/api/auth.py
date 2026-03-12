"""
JWT Authentication router for EcoGuard AI
Users and sessions are stored in MySQL (users + user_sessions tables).

Roles:
  admin    - full access
  employee - Dashboard, Flagged Areas, Reports, Account
"""
from __future__ import annotations

import hashlib
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from database.db_manager import get_db_manager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    "ECOGUARD_SECRET_KEY",
    "ecoguard-ai-super-secret-key-change-in-production-2024",
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

# ---------------------------------------------------------------------------
# Crypto helpers
# ---------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _hash_token(token: str) -> str:
    """SHA-256 hash of a JWT for safe storage in user_sessions."""
    return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def _db():
    return get_db_manager()


def _get_user_by_email(email: str) -> Optional[dict]:
    rows = _db().execute_query(
        "SELECT * FROM users WHERE email = %s AND is_active = TRUE LIMIT 1",
        (email,),
    )
    return rows[0] if rows else None


def _get_user_by_id(user_id: str) -> Optional[dict]:
    rows = _db().execute_query(
        "SELECT * FROM users WHERE id = %s AND is_active = TRUE LIMIT 1",
        (user_id,),
    )
    return rows[0] if rows else None


def _get_session(session_id: str) -> Optional[dict]:
    rows = _db().execute_query(
        "SELECT * FROM user_sessions WHERE id = %s LIMIT 1",
        (session_id,),
    )
    return rows[0] if rows else None


def _update_last_login(user_id: str) -> None:
    _db().execute_query(
        "UPDATE users SET last_login = %s WHERE id = %s",
        (datetime.now(timezone.utc), user_id),
        fetch=False,
    )


# ---------------------------------------------------------------------------
# Seed default users (runs once on startup if table is empty)
# ---------------------------------------------------------------------------
def _seed_default_users() -> None:
    try:
        rows = _db().execute_query("SELECT COUNT(*) AS cnt FROM users")
        if rows and rows[0]["cnt"] > 0:
            return
        now = datetime.now(timezone.utc)
        defaults = [
            (str(uuid.uuid4()), "Administrator", "admin@ecoguard.ai",    "admin123",    "admin"),
            (str(uuid.uuid4()), "Employee",      "employee@ecoguard.ai", "employee123", "employee"),
        ]
        for uid, full_name, email, password, role in defaults:
            _db().execute_query(
                """
                INSERT INTO users
                    (id, full_name, email, password_hash, role, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, TRUE, %s, %s)
                """,
                (uid, full_name, email, _hash_password(password), role, now, now),
                fetch=False,
            )
            logger.info("Seeded default user: %s (%s)", email, role)
    except Exception as exc:
        logger.warning("Could not seed default users (DB may not be ready): %s", exc)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------
def _create_access_token(
    user_id: str,
    role: str,
    email: str,
    session_id: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": user_id,
        "jti": session_id,
        "role": role,
        "email": email,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ---------------------------------------------------------------------------
# Dependency: get_current_user
# ---------------------------------------------------------------------------
async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        session_id: str = payload.get("jti")
        if not user_id or not session_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    session = _get_session(session_id)
    if not session or session["is_revoked"]:
        raise credentials_exception

    user = _get_user_by_id(user_id)
    if not user:
        raise credentials_exception

    user["_session_id"] = session_id
    return user


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    email: str
    full_name: str


class UserInfo(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class CreateUserRequest(BaseModel):
    full_name: str
    email: str
    password: str
    role: str


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/api/auth", tags=["auth"])

_seed_default_users()


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """Authenticate with email + password and return a Bearer JWT."""
    user = _get_user_by_email(form_data.username.strip().lower())
    if not user or not _verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session_id = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    token = _create_access_token(
        user_id=str(user["id"]),
        role=user["role"],
        email=user["email"],
        session_id=session_id,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    _db().execute_query(
        """
        INSERT INTO user_sessions
            (id, user_id, token_hash, ip_address, user_agent, expires_at, is_revoked)
        VALUES (%s, %s, %s, %s, %s, %s, FALSE)
        """,
        (session_id, str(user["id"]), _hash_token(token), ip, ua, expires_at),
        fetch=False,
    )
    _update_last_login(str(user["id"]))

    return Token(
        access_token=token,
        token_type="bearer",
        role=user["role"],
        email=user["email"],
        full_name=user["full_name"],
    )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Revoke the current session so the JWT is immediately invalidated."""
    _db().execute_query(
        "UPDATE user_sessions SET is_revoked = TRUE WHERE id = %s",
        (current_user["_session_id"],),
        fetch=False,
    )
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserInfo)
async def me(current_user: dict = Depends(get_current_user)):
    """Return the currently authenticated user profile."""
    return UserInfo(
        id=str(current_user["id"]),
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        is_active=bool(current_user["is_active"]),
    )


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
):
    """Allow any authenticated user to change their own password."""
    if not _verify_password(body.current_password, current_user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    if len(body.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters",
        )
    _db().execute_query(
        "UPDATE users SET password_hash = %s, updated_at = %s WHERE id = %s",
        (_hash_password(body.new_password), datetime.now(timezone.utc), str(current_user["id"])),
        fetch=False,
    )
    return {"message": "Password changed successfully"}


# ---------------------------------------------------------------------------
# Admin-only user management
# ---------------------------------------------------------------------------
@router.get("/users")
async def list_users(admin: dict = Depends(require_admin)):
    """List all users - admin only."""
    rows = _db().execute_query(
        "SELECT id, full_name, email, role, is_active, last_login, created_at FROM users ORDER BY created_at"
    )
    return {
        "users": [
            {
                "id": str(r["id"]),
                "full_name": r["full_name"],
                "email": r["email"],
                "role": r["role"],
                "is_active": bool(r["is_active"]),
                "last_login": r["last_login"].isoformat() if r["last_login"] else None,
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ]
    }


@router.post("/users")
async def create_user(
    body: CreateUserRequest,
    admin: dict = Depends(require_admin),
):
    """Create a new user - admin only."""
    if body.role not in ("admin", "employee"):
        raise HTTPException(status_code=400, detail="Role must be admin or employee")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    email_lower = body.email.strip().lower()
    if _get_user_by_email(email_lower):
        raise HTTPException(status_code=400, detail="Email already exists")

    now = datetime.now(timezone.utc)
    uid = str(uuid.uuid4())
    _db().execute_query(
        """
        INSERT INTO users (id, full_name, email, password_hash, role, is_active, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, TRUE, %s, %s)
        """,
        (uid, body.full_name.strip(), email_lower, _hash_password(body.password), body.role, now, now),
        fetch=False,
    )
    return {"message": f"User created", "id": uid, "email": email_lower, "role": body.role}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(require_admin)):
    """Soft-delete a user - admin only. Cannot deactivate yourself."""
    if user_id == str(admin["id"]):
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    target = _get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    _db().execute_query(
        "UPDATE users SET is_active = FALSE, updated_at = %s WHERE id = %s",
        (datetime.now(timezone.utc), user_id),
        fetch=False,
    )
    return {"message": f"User deactivated"}


# ---------------------------------------------------------------------------
# Notification preferences (stored in system_metadata)
# ---------------------------------------------------------------------------
_NOTIF_KEY = "admin_notification_preferences"


@router.get("/notification-preferences")
async def get_notification_preferences(admin: dict = Depends(require_admin)):
    """Return the admin email notification preferences from the database."""
    import json as _json
    rows = _db().execute_query(
        "SELECT value_data FROM system_metadata WHERE key_name = %s LIMIT 1",
        (_NOTIF_KEY,),
    )
    if not rows:
        return {
            "adminEmail": admin.get("email", ""),
            "onNewDetection": True,
            "weeklyReport": False,
            "monthlyReport": True,
            "annualReport": False,
        }
    raw = rows[0]["value_data"]
    if isinstance(raw, str):
        return _json.loads(raw)
    return raw


class NotificationPrefsRequest(BaseModel):
    adminEmail: str
    onNewDetection: bool
    weeklyReport: bool
    monthlyReport: bool
    annualReport: bool
    smtpServer: str = "smtp.gmail.com"
    smtpPort: int = 587
    smtpUser: str = ""
    smtpPassword: str = ""


@router.put("/notification-preferences")
async def save_notification_preferences(
    body: NotificationPrefsRequest,
    admin: dict = Depends(require_admin),
):
    """Persist admin email notification preferences to system_metadata."""
    import json as _json
    value = _json.dumps(body.dict())
    existing = _db().execute_query(
        "SELECT id FROM system_metadata WHERE key_name = %s LIMIT 1",
        (_NOTIF_KEY,),
    )
    if existing:
        _db().execute_query(
            "UPDATE system_metadata SET value_data = %s, updated_at = %s WHERE key_name = %s",
            (value, datetime.now(timezone.utc), _NOTIF_KEY),
            fetch=False,
        )
    else:
        _db().execute_query(
            "INSERT INTO system_metadata (key_name, value_data) VALUES (%s, %s)",
            (_NOTIF_KEY, value),
            fetch=False,
        )
    return {"message": "Preferences saved", "data": body.dict()}


# ---------------------------------------------------------------------------
# Shared helper — send a detection-alert email via stored SMTP credentials
# ---------------------------------------------------------------------------
def _send_notification_email(
    to_address: str,
    subject: str,
    html_body: str,
    prefs: dict,
) -> None:
    """Send an email using the SMTP settings stored in notification preferences."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    smtp_server = prefs.get("smtpServer", "smtp.gmail.com")
    smtp_port = int(prefs.get("smtpPort", 587))
    smtp_user = prefs.get("smtpUser", "")
    smtp_password = prefs.get("smtpPassword", "")

    if not smtp_user or not smtp_password:
        raise ValueError("SMTP credentials are not configured. Set smtpUser and smtpPassword in Email Preferences.")

    # Use adminEmail as the human-readable From address so it doesn't look like
    # a machine address and avoids spam filters. Fall back to smtp_user.
    admin_email = prefs.get("adminEmail", "").strip() or smtp_user
    from_header = f"ML Deforestation Monitoring System <{admin_email}>"

    msg = MIMEMultipart("alternative")
    msg["From"] = from_header
    msg["To"] = to_address
    msg["Subject"] = subject
    msg["Reply-To"] = admin_email
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as server:
        server.ehlo()
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, to_address, msg.as_string())


def _get_prefs() -> dict:
    """Load notification preferences from DB (returns defaults if not set)."""
    import json as _json
    rows = _db().execute_query(
        "SELECT value_data FROM system_metadata WHERE key_name = %s LIMIT 1",
        (_NOTIF_KEY,),
    )
    if not rows:
        return {}
    raw = rows[0]["value_data"]
    if isinstance(raw, str):
        return _json.loads(raw)
    return raw or {}


# ---------------------------------------------------------------------------
# Shared email builder — uses real DB data
# ---------------------------------------------------------------------------
def _build_detection_email_html(areas: list, is_test: bool = False) -> str:
    """Build an HTML email body from real deforestation detection records."""
    now_str = datetime.now().strftime("%B %d, %Y at %H:%M UTC")
    intro = (
        "This is a <strong>test alert</strong> showing your latest real deforestation data."
        if is_test else
        "New deforestation has been detected in the following monitored areas."
    )

    rows_html = ""
    for area in areas:
        loss = float(area.get("forest_loss_percent") or 0)
        cover_before = float(area.get("forest_cover_before") or 0)
        cover_after  = float(area.get("forest_cover_after") or 0)
        before_date  = str(area.get("before_date") or "")
        after_date   = str(area.get("after_date") or "")
        trend        = str(area.get("vegetation_trend") or "decline").title()
        name         = area.get("name") or "Unknown Area"
        last_mon     = str(area.get("last_monitored") or "")[:10]

        rows_html += f"""
        <div style="background:#fef2f2;border:1px solid #fca5a5;border-radius:6px;padding:16px;margin:12px 0;">
          <p style="margin:0 0 8px 0;font-weight:bold;font-size:15px;color:#991b1b;">&#9888; {name}</p>
          <table style="width:100%;font-size:13px;color:#374151;border-collapse:collapse;">
            <tr><td style="padding:3px 0;font-weight:600;width:180px;">Forest Loss:</td>
                <td style="color:#dc2626;font-weight:bold;">{loss:.2f}%</td></tr>
            <tr><td style="padding:3px 0;font-weight:600;">Forest Cover Before:</td>
                <td>{cover_before:.4f} km&sup2;</td></tr>
            <tr><td style="padding:3px 0;font-weight:600;">Forest Cover After:</td>
                <td>{cover_after:.4f} km&sup2;</td></tr>
            <tr><td style="padding:3px 0;font-weight:600;">Vegetation Trend:</td>
                <td>{trend}</td></tr>
            <tr><td style="padding:3px 0;font-weight:600;">Detection Period:</td>
                <td>{before_date} &rarr; {after_date}</td></tr>
            <tr><td style="padding:3px 0;font-weight:600;">Last Monitored:</td>
                <td>{last_mon}</td></tr>
            <tr><td style="padding:3px 0;font-weight:600;">Status:</td>
                <td><span style="background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:9999px;font-size:12px;">Awaiting Response</span></td></tr>
          </table>
        </div>"""

    if not rows_html:
        rows_html = "<p style='color:#6b7280;'>No deforestation records found in the database yet.</p>"

    return f"""
    <div style="font-family:Arial,sans-serif;max-width:620px;margin:0 auto;background:#f9fafb;padding:24px;border-radius:8px;">
      <div style="background:#b91c1c;color:#fff;padding:16px 20px;border-radius:6px 6px 0 0;">
        <h2 style="margin:0;font-size:18px;">&#9888; DEFORESTATION DETECTION ALERT</h2>
        <p style="margin:6px 0 0 0;font-size:13px;opacity:0.85;">ML Deforestation Monitoring System &mdash; {now_str}</p>
      </div>
      <div style="background:#fff;border:1px solid #e5e7eb;border-top:none;padding:20px;border-radius:0 0 6px 6px;">
        <p style="color:#374151;font-size:14px;">{intro}</p>
        {rows_html}
        <p style="color:#6b7280;font-size:12px;margin-top:20px;border-top:1px solid #e5e7eb;padding-top:12px;">
          This is an automated alert from the ML Deforestation Monitoring System.<br/>
          Log in to the system to view full details, satellite images, and respond to alerts.
        </p>
      </div>
    </div>"""


def _fetch_deforested_areas() -> list:
    """Query the real deforested areas with their latest detection data."""
    return _db().execute_query("""
        SELECT ma.id, ma.name, ma.last_monitored, ma.detection_count,
               dh.forest_loss_percent, dh.forest_cover_before, dh.forest_cover_after,
               dh.before_date, dh.after_date, dh.vegetation_trend
        FROM monitored_areas ma
        JOIN detection_history dh ON dh.area_id = ma.id
        WHERE dh.deforestation_detected = 1
        ORDER BY dh.timestamp DESC
    """) or []


# ---------------------------------------------------------------------------
# Test email endpoint
# ---------------------------------------------------------------------------
class TestEmailRequest(BaseModel):
    toEmail: str


@router.post("/test-email")
async def send_test_email(body: TestEmailRequest, admin: dict = Depends(require_admin)):
    """Send a test detection-alert email using real data from the database."""
    prefs = _get_prefs()
    areas = _fetch_deforested_areas()
    subject = f"ML Deforestation Monitoring System — Detection Alert ({len(areas)} area(s) flagged)"
    html_body = _build_detection_email_html(areas, is_test=True)
    try:
        _send_notification_email(body.toEmail, subject, html_body, prefs)
        return {"message": f"Test email sent to {body.toEmail} with {len(areas)} real detection(s)"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")
