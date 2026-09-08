from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_roles
from app.models.models import Device, User
from app.schemas.common import (
    DeviceCreate,
    DeviceMoveRequest,
    DeviceRead,
    DeviceUnmountRequest,
    DeviceUpdate,
    MessageResponse,
    PagedResponse,
)
from app.services.device import create_device, move_device, unmount_device, update_device
from app.services.import_export import import_devices, parse_upload
from app.services.device_sheet import sheet_response

router = APIRouter(prefix="/devices", tags=["devices"])


def serialize_device_query(query):
    return query.options(joinedload(Device.administrators), joinedload(Device.ports))


@router.get("", response_model=PagedResponse)
def list_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    keyword: Optional[str] = None,
    device_type: Optional[str] = None,
    status: Optional[str] = None,
    rack_id: Optional[int] = None,
):
    query = db.query(Device)
    if keyword:
        query = query.filter(or_(Device.asset_number.contains(keyword), Device.name.contains(keyword), Device.ip_address.contains(keyword), Device.model.contains(keyword)))
    if device_type:
        query = query.filter(Device.device_type == device_type)
    if status:
        query = query.filter(Device.status == status)
    if rack_id:
        query = query.filter(Device.rack_id == rack_id)
    total = query.count()
    items = serialize_device_query(query).order_by(Device.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return PagedResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/export/{file_format}")
def export_devices(file_format: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if file_format not in ("csv", "xlsx"):
        raise HTTPException(status_code=400, detail="仅支持CSV或XLSX文件")
    return sheet_response(file_format, db.query(Device).options(joinedload(Device.administrators), joinedload(Device.ports)).order_by(Device.id).all())


@router.get("/template/{file_format}")
def download_template(file_format: str, current_user: User = Depends(get_current_user)):
    if file_format not in ("csv", "xlsx"):
        raise HTTPException(status_code=400, detail="仅支持CSV或XLSX文件")
    return sheet_response(file_format, template=True)


@router.get("/{device_id}", response_model=DeviceRead)
def get_device(device_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    device = serialize_device_query(db.query(Device)).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    return device


@router.post("", response_model=DeviceRead)
def add_device(
    payload: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    return create_device(db, payload, current_user)


@router.put("/{device_id}", response_model=DeviceRead)
def edit_device(
    device_id: int,
    payload: DeviceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    return update_device(db, device, payload, current_user)


@router.post("/{device_id}/move", response_model=DeviceRead)
def move_device_api(
    device_id: int,
    payload: DeviceMoveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    return move_device(db, device, payload.rack_id, payload.start_u, payload.comment, current_user)


@router.post("/{device_id}/unmount", response_model=DeviceRead)
def unmount_device_api(
    device_id: int,
    payload: DeviceUnmountRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    return unmount_device(db, device, payload.comment, current_user)


@router.post("/import", response_model=MessageResponse)
def import_device_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    rows = parse_upload(file)
    imported, errors = import_devices(db, rows, current_user)
    message = f"导入完成，成功 {imported} 条"
    if errors:
        message += "；失败：" + "；".join(errors[:5])
    return MessageResponse(message=message)


