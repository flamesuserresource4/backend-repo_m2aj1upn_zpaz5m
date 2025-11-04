import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List
import base64
import hmac
import hashlib
import json

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import Service, Galleryitem, Testimonial, Message, Adminuser, Mediaasset

# App and CORS
app = FastAPI(title="Compass Remodeling CMS API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth setup (no external deps)
SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret-key-change")
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8


def _hash_password(password: str) -> str:
    return hashlib.sha256((password + SECRET_KEY).encode()).hexdigest()


def _sign(data: dict) -> str:
    payload = data.copy()
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    sig = hmac.new(SECRET_KEY.encode(), payload_bytes, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload_bytes + b"." + sig).decode()


def _verify(token: str) -> Optional[dict]:
    try:
        raw = base64.urlsafe_b64decode(token.encode())
        payload_bytes, sig = raw.rsplit(b".", 1)
        expected = hmac.new(SECRET_KEY.encode(), payload_bytes, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            return None
        data = json.loads(payload_bytes.decode())
        if data.get("exp") and datetime.now(timezone.utc).timestamp() > data["exp"]:
            return None
        return data
    except Exception:
        return None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: str
    password: str


def get_admin_by_email(email: str) -> Optional[dict]:
    users = get_documents("adminuser", {"email": email})
    return users[0] if users else None


# Bootstrap default admin
DEFAULT_ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@compassremodeling.com")
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Compass2025!")
try:
    if db is not None:
        existing = get_documents("adminuser", {"email": DEFAULT_ADMIN_EMAIL})
        if not existing:
            create_document(
                "adminuser",
                Adminuser(
                    email=DEFAULT_ADMIN_EMAIL,
                    password_hash=_hash_password(DEFAULT_ADMIN_PASSWORD),
                    name="Compass Admin",
                ),
            )
except Exception:
    pass


@app.get("/")
def read_root():
    return {"message": "Compass Remodeling CMS API running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": [],
    }
    try:
        if db is not None:
            response["database"] = "✅ Connected"
            response["database_url"] = "✅ Set"
            response["database_name"] = getattr(db, "name", "✅ Set")
            try:
                response["collections"] = db.list_collection_names()
            except Exception:
                pass
    except Exception as e:
        response["database"] = f"⚠️ {str(e)[:80]}"
    return response


@app.get("/schema")
def get_schema_definitions():
    return {
        "collections": [
            "adminuser",
            "service",
            "galleryitem",
            "testimonial",
            "message",
            "mediaasset",
        ]
    }


# Auth endpoints
@app.post("/api/auth/login", response_model=Token)
def login(data: LoginRequest):
    user = get_admin_by_email(data.email)
    if not user or user.get("password_hash") != _hash_password(data.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    exp = (datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()
    token = _sign({"sub": user["email"], "exp": exp})
    return Token(access_token=token)


# Public content
@app.get("/api/services")
def list_services_public() -> List[Service]:
    docs = get_documents("service", {})
    docs.sort(key=lambda d: d.get("order", 0))
    for d in docs:
        d.pop("_id", None)
    return docs


@app.get("/api/gallery")
def list_gallery_public() -> List[Galleryitem]:
    docs = get_documents("galleryitem", {})
    docs.sort(key=lambda d: d.get("order", 0))
    for d in docs:
        d.pop("_id", None)
    return docs


@app.get("/api/testimonials")
def list_testimonials_public() -> List[Testimonial]:
    docs = get_documents("testimonial", {})
    docs.sort(key=lambda d: d.get("order", 0))
    for d in docs:
        d.pop("_id", None)
    return docs


@app.post("/api/messages")
def submit_message(msg: Message):
    mid = create_document("message", msg)
    return {"id": mid, "status": "received"}


# Admin CRUD (Header auth)

def _require_auth(authorization: Optional[str]):
    if not authorization or not authorization.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")
    data = _verify(authorization.split(' ',1)[1])
    if not data or not data.get('sub'):
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/api/admin/messages")
def list_messages_admin(authorization: Optional[str] = Header(None)):
    _require_auth(authorization)
    docs = get_documents("message", {})
    for d in docs:
        d["id"] = str(d.pop("_id", ""))
    return docs


@app.post("/api/admin/services")
def create_service_admin(svc: Service, authorization: Optional[str] = Header(None)):
    _require_auth(authorization)
    sid = create_document("service", svc)
    return {"id": sid}


@app.post("/api/admin/gallery")
def create_gallery_item_admin(item: Galleryitem, authorization: Optional[str] = Header(None)):
    _require_auth(authorization)
    gid = create_document("galleryitem", item)
    return {"id": gid}


@app.post("/api/admin/testimonials")
def create_testimonial_admin(item: Testimonial, authorization: Optional[str] = Header(None)):
    _require_auth(authorization)
    tid = create_document("testimonial", item)
    return {"id": tid}


@app.post("/api/admin/media-url")
def save_media_url(asset: Mediaasset, authorization: Optional[str] = Header(None)):
    _require_auth(authorization)
    aid = create_document("mediaasset", asset)
    return {"id": aid, "url": asset.url}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
