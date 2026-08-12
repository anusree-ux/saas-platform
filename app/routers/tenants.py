
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models import Tenant, APIKey
from app.schemas import TenantCreate, TenantResponse
from app.security import generate_api_key, hash_api_key
from app.dependencies import get_current_tenant, get_db



router = APIRouter(prefix="/tenants", tags=["Tenants"])

@router.post("/", response_model=TenantResponse)
def create_tenant(
    tenant_data: TenantCreate,
    db: Session = Depends(get_db),
):
    # 1. Create tenant
    tenant = Tenant(
        name=tenant_data.name,
    )

    db.add(tenant)
    db.flush()

    # 2. Generate API key
    api_key = generate_api_key()

    # 3. Store only the hash
    api_key_record = APIKey(
        tenant_id=tenant.id,
        key_hash=hash_api_key(api_key),
    )

    db.add(api_key_record)
    db.commit()

    # 4. Return the raw API key only once
    return TenantResponse(
        tenant_id=tenant.id,
        name=tenant.name,
        api_key=api_key,
    )

@router.get("/me")
def get_my_tenant(
    tenant=Depends(get_current_tenant),
):
    return {
        "tenant_id": tenant.id,
        "name": tenant.name,
    }