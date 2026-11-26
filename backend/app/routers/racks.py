from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_roles
from app.models.models import Rack, User
from app.schemas.common import BatchDeleteRequest, BatchDeleteResponse, MessageResponse, PagedResponse, RackCreate, RackDetail, RackRead, RackUpdate, RackImportResult
from app.services.audit import log_action
from app.services.deletion import delete_racks, deletion_targets
from app.services.rack import build_rack_occupancy, calculate_rack_utilization, rack_values, create_rack_record
from app.services.rack_import import import_racks, parse_rack_upload, template_response

router = APIRouter(prefix="/racks", tags=["racks"])


@router.get("", response_model=PagedResponse)
def list_racks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    keyword: Optional[str] = None,
    data_center_id: Optional[int] = None,
    area_id: Optional[int] = None,
    category: Optional[str] = None,
):
    query = db.query(Rack)
    if keyword:
        query = query.filter(or_(Rack.code.contains(keyword), Rack.remark.contains(keyword)))
    if data_center_id:
        query = query.filter(Rack.data_center_id == data_center_id)
    if area_id:
        query = query.filter(Rack.area_id == area_id)
    if category:
        query = query.filter(Rack.category == category)
    total = query.count()
    items = query.order_by(Rack.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return PagedResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/template/xlsx")
def download_rack_template(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return template_response(db)


@router.post("/import", response_model=RackImportResult)
def import_rack_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    return import_racks(db, parse_rack_upload(file), current_user)


@router.post("/batch-delete", response_model=BatchDeleteResponse)
def batch_delete_racks(
    payload: BatchDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    racks = deletion_targets(db, Rack, payload.ids, "机柜")
    device_count = delete_racks(db, racks, current_user)
    db.commit()
    return BatchDeleteResponse(message=f"已删除 {len(racks)} 个机柜及 {device_count} 台设备",
                               deleted_count=len(racks), deleted_device_count=device_count)


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
    return create_rack_record(db, payload, current_user)


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
    values = rack_values(db, payload, existing=rack)
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


@router.post("/{rack_id}/activate", response_model=MessageResponse)
def activate_rack(
    rack_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    rack = db.query(Rack).filter(Rack.id == rack_id).first()
    if not rack:
        raise HTTPException(status_code=404, detail="机柜不存在")
    rack.is_active = True
    log_action(db, user=current_user, action="activate", module="rack", target_type="rack", target_id=str(rack_id), message=f"启用机柜 {rack.code}")
    db.commit()
    return MessageResponse(message="机柜已启用")


@router.delete("/{rack_id}", response_model=MessageResponse)
def delete_rack(
    rack_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    rack = db.query(Rack).filter(Rack.id == rack_id).first()
    if not rack:
        raise HTTPException(status_code=404, detail="机柜不存在")
    delete_racks(db, [rack], current_user)
    db.commit()
    return MessageResponse(message="机柜已删除")
