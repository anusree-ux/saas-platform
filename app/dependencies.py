import hashlib

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import APIKey, Tenant


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_tenant(
    x_api_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required",
        )

    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()

    api_key = (
        db.query(APIKey)
        .filter(
            APIKey.key_hash == key_hash,
            APIKey.revoked_at.is_(None),
        )
        .first()
    )

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
        )

    tenant = (
        db.query(Tenant)
        .filter(
            Tenant.id == api_key.tenant_id,
            Tenant.status == "active",
        )
        .first()
    )

    if not tenant:
        raise HTTPException(
            status_code=401,
            detail="Tenant inactive or not found",
        )

    return tenant