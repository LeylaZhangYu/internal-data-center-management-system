from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_roles
from app.models.models import Area, DataCenter, Rack, User
from app.schemas.common import (
    AreaCreate,
    AreaRead,
    AreaUpdate,
    DataCenterCreate,
    DataCenterRead,
    DataCenterUpdate,
    MessageResponse,
)
from app.services.audit import log_action

router = APIRouter(prefix="/datacenters", tags=["datacenters"])


@router.get("", response_model=List[DataCenterRead])
def list_datacenters(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(DataCenter).options(joinedload(DataCenter.areas)).order_by(DataCenter.id.desc()).all()


@router.post("", response_model=DataCenterRead)
def create_datacenter(
    payload: DataCenterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    dc = DataCenter(**payload.dict())
    db.add(dc)
    log_action(db, user=current_user, action="create", module="datacenter", target_type="datacenter", target_id=None, message=f"新增机房 {payload.name}")
    db.commit()
    db.refresh(dc)
    return dc


@router.put("/{datacenter_id}", response_model=DataCenterRead)
def update_datacenter(
    datacenter_id: int,
    payload: DataCenterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    dc = db.query(DataCenter).filter(DataCenter.id == datacenter_id).first()
    if not dc:
        raise HTTPException(status_code=404, detail="机房不存在")
    for key, value in payload.dict().items():
        setattr(dc, key, value)
    log_action(db, user=current_user, action="update", module="datacenter", target_type="datacenter", target_id=str(dc.id), message=f"更新机房 {dc.name}")
    db.commit()
    db.refresh(dc)
    return dc


@router.post("/{datacenter_id}/deactivate", response_model=MessageResponse)
def deactivate_datacenter(
    datacenter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    dc = db.query(DataCenter).filter(DataCenter.id == datacenter_id).first()
    if not dc:
        raise HTTPException(status_code=404, detail="机房不存在")
    dc.is_active = False
    log_action(db, user=current_user, action="deactivate", module="datacenter", target_type="datacenter", target_id=str(dc.id), message=f"停用机房 {dc.name}")
    db.commit()
    return MessageResponse(message="机房已停用")


@router.post("/{datacenter_id}/activate", response_model=MessageResponse)
def activate_datacenter(
    datacenter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    dc = db.query(DataCenter).filter(DataCenter.id == datacenter_id).first()
    if not dc:
        raise HTTPException(status_code=404, detail="机房不存在")
    dc.is_active = True
    log_action(db, user=current_user, action="activate", module="datacenter", target_type="datacenter", target_id=str(datacenter_id), message=f"启用机房 {dc.name}")
    db.commit()
    return MessageResponse(message="机房已启用")


@router.delete("/{datacenter_id}", response_model=MessageResponse)
def delete_datacenter(
    datacenter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    dc = db.query(DataCenter).filter(DataCenter.id == datacenter_id).first()
    if not dc:
        raise HTTPException(status_code=404, detail="机房不存在")
    if db.query(Area).filter(Area.data_center_id == datacenter_id).first():
        raise HTTPException(status_code=409, detail="机房下存在区域，无法删除，请先删除区域")
    if db.query(Rack).filter(Rack.data_center_id == datacenter_id).first():
        raise HTTPException(status_code=409, detail="机房下存在机柜，无法删除，请先移除机柜")
    name = dc.name
    db.delete(dc)
    log_action(db, user=current_user, action="delete", module="datacenter", target_type="datacenter", target_id=str(datacenter_id), message=f"删除机房 {name}")
    db.commit()
    return MessageResponse(message="机房已删除")


@router.post("/{datacenter_id}/areas", response_model=AreaRead)
def create_area(
    datacenter_id: int,
    payload: AreaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    datacenter = db.query(DataCenter).filter(DataCenter.id == datacenter_id).first()
    if not datacenter:
        raise HTTPException(status_code=404, detail="机房不存在")
    area_data = payload.dict(exclude={"data_center_id"})
    area = Area(**area_data, data_center_id=datacenter_id)
    db.add(area)
    log_action(db, user=current_user, action="create", module="area", target_type="area", target_id=None, message=f"新增区域 {payload.name}")
    db.commit()
    db.refresh(area)
    return area


@router.put("/areas/{area_id}", response_model=AreaRead)
def update_area(
    area_id: int,
    payload: AreaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    area = db.query(Area).filter(Area.id == area_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="区域不存在")
    for key, value in payload.dict().items():
        setattr(area, key, value)
    log_action(db, user=current_user, action="update", module="area", target_type="area", target_id=str(area.id), message=f"更新区域 {area.name}")
    db.commit()
    db.refresh(area)
    return area


@router.delete("/areas/{area_id}", response_model=MessageResponse)
def delete_area(
    area_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    area = db.query(Area).filter(Area.id == area_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="区域不存在")
    if db.query(Rack).filter(Rack.area_id == area_id).first():
        raise HTTPException(status_code=409, detail="区域下存在机柜，无法删除，请先移除机柜")
    name = area.name
    db.delete(area)
    log_action(db, user=current_user, action="delete", module="area", target_type="area", target_id=str(area_id), message=f"删除区域 {name}")
    db.commit()
    return MessageResponse(message="区域已删除")
