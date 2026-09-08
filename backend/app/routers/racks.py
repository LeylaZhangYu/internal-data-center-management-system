from typing import Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_roles
from app.models.models import Rack, User
from app.schemas.common import MessageResponse, PagedResponse, RackCreate, RackDetail, RackRead, RackUpdate
from app.services.audit import log_action
from app.services.rack import build_rack_occupancy, calculate_rack_utilization

router = APIRouter(prefix="/racks", tags=["racks"])


def auto_layout_coordinates(row_position: int, column_position: int) -> Tuple[float, float]:
    # 3D 展示使用固定间距，用户只需维护行列位置。
    return (max(column_position - 1, 0) * 2.2, max(row_position - 1, 0) * 4.0)


@router.get("", response_model=PagedResponse)
def list_racks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    keyword: Optional[str] = None,
    data_center_id: Optional[int] = None,
    area_id: Optional[int] = None,
):
    query = db.query(Rack)
    if keyword:
        query = query.filter(or_(Rack.code.contains(keyword), Rack.remark.contains(keyword)))
    if data_center_id:
        query = query.filter(Rack.data_center_id == data_center_id)
    if area_id:
        query = query.filter(Rack.area_id == area_id)
    total = query.count()
    items = query.order_by(Rack.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return PagedResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{rack_id}", response_model=RackDetail)
def get_rack(rack_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rack = db.query(Rack).options(joinedload(Rack.devices)).filter(Rack.id == rack_id).first()
    if not rack:
        raise HTTPException(status_code=404, detail="机柜不存在")
    return RackDetail(**rack.__dict__, utilization=calculate_rack_utilization(rack), device_count=len([d for d in rack.devices if d.rack_id == rack.id and d.start_u]), occupancy=build_rack_occupancy(rack))


@router.post("", response_model=RackRead)
def create_rack(
    payload: RackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    values = payload.dict()
    values["x_position"], values["y_position"] = auto_layout_coordinates(values["row_position"], values["column_position"])
    rack = Rack(**values)
    db.add(rack)
    log_action(db, user=current_user, action="create", module="rack", target_type="rack", target_id=None, message=f"新增机柜 {payload.code}")
    db.commit()
    db.refresh(rack)
    return rack


@router.put("/{rack_id}", response_model=RackRead)
def update_rack(
    rack_id: int,
    payload: RackUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    rack = db.query(Rack).filter(Rack.id == rack_id).first()
    if not rack:
        raise HTTPException(status_code=404, detail="机柜不存在")
    values = payload.dict()
    values["x_position"], values["y_position"] = auto_layout_coordinates(values["row_position"], values["column_position"])
    for key, value in values.items():
        setattr(rack, key, value)
    log_action(db, user=current_user, action="update", module="rack", target_type="rack", target_id=str(rack.id), message=f"更新机柜 {rack.code}")
    db.commit()
    db.refresh(rack)
    return rack


@router.post("/{rack_id}/deactivate", response_model=MessageResponse)
def deactivate_rack(
    rack_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    rack = db.query(Rack).filter(Rack.id == rack_id).first()
    if not rack:
        raise HTTPException(status_code=404, detail="机柜不存在")
    rack.is_active = False
    log_action(db, user=current_user, action="deactivate", module="rack", target_type="rack", target_id=str(rack.id), message=f"停用机柜 {rack.code}")
    db.commit()
    return MessageResponse(message="机柜已停用")
