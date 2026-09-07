from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
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


@router.get("/export/csv")
def export_csv(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["asset_number", "name", "device_type", "model", "serial_number", "purpose", "status", "ip_address", "rack_id", "start_u", "u_height", "cpu", "memory_gb", "gpu", "storage_desc", "operating_system", "notes"])
    for d in db.query(Device).order_by(Device.id).all():
        writer.writerow([d.asset_number, d.name, d.device_type.value, d.model, d.serial_number or "", d.purpose or "", d.status.value, d.ip_address or "", d.rack_id or "", d.start_u or "", d.u_height, d.cpu or "", d.memory_gb or "", d.gpu or "", d.storage_desc or "", d.operating_system or "", d.notes or ""])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=devices.csv"})


@router.get("/export/xlsx")
def export_xlsx(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    import io

    wb = Workbook()
    ws = wb.active
    ws.title = "devices"
    headers = ["asset_number", "name", "device_type", "model", "serial_number", "purpose", "status", "ip_address", "rack_id", "start_u", "u_height", "cpu", "memory_gb", "gpu", "storage_desc", "operating_system", "notes"]
    ws.append(headers)
    for d in db.query(Device).order_by(Device.id).all():
        ws.append([d.asset_number, d.name, d.device_type.value, d.model, d.serial_number or "", d.purpose or "", d.status.value, d.ip_address or "", d.rack_id or "", d.start_u or "", d.u_height, d.cpu or "", d.memory_gb or "", d.gpu or "", d.storage_desc or "", d.operating_system or "", d.notes or ""])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=devices.xlsx"})
