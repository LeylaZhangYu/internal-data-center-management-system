from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_roles
from app.models.models import Administrator, User
from app.schemas.common import AdministratorCreate, AdministratorRead, AdministratorUpdate
from app.services.audit import log_action

router = APIRouter(prefix="/administrators", tags=["administrators"])


@router.get("", response_model=List[AdministratorRead])
def list_administrators(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Administrator).order_by(Administrator.id.desc()).all()


@router.post("", response_model=AdministratorRead)
def create_administrator(
    payload: AdministratorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    admin = Administrator(**payload.dict())
    db.add(admin)
    log_action(db, user=current_user, action="create", module="administrator", target_type="administrator", target_id=None, message=f"新增管理员 {payload.name}")
    db.commit()
    db.refresh(admin)
    return admin


@router.put("/{administrator_id}", response_model=AdministratorRead)
def update_administrator(
    administrator_id: int,
    payload: AdministratorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    admin = db.query(Administrator).filter(Administrator.id == administrator_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="管理员不存在")
    for key, value in payload.dict().items():
        setattr(admin, key, value)
    log_action(db, user=current_user, action="update", module="administrator", target_type="administrator", target_id=str(admin.id), message=f"更新管理员 {admin.name}")
    db.commit()
    db.refresh(admin)
    return admin
