from datetime import datetime
from typing import Iterable, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.models import (
    Administrator,
    Device,
    DevicePlacementHistory,
    DevicePort,
    DeviceStatusEnum,
    PlacementActionEnum,
    Rack,
    User,
)
from app.services.audit import log_action


def ensure_unique_device_fields(db: Session, payload, existing_id: Optional[int] = None) -> None:
    queries = [
        (Device.asset_number, payload.asset_number, "资产编号已存在"),
        (Device.ip_address, payload.ip_address, "IP地址已存在"),
    ]
    if getattr(payload, "serial_number", None):
        queries.append((Device.serial_number, payload.serial_number, "序列号已存在"))

    for field, value, message in queries:
        if not value:
            continue
        query = db.query(Device).filter(field == value)
        if existing_id:
            query = query.filter(Device.id != existing_id)
        if query.first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)



def validate_rack_placement(db: Session, rack_id: Optional[int], start_u: Optional[int], u_height: int, device_id: Optional[int] = None) -> Optional[Rack]:
    if rack_id is None and start_u is None:
        return None
    if rack_id is None or start_u is None:
        raise HTTPException(status_code=400, detail="机柜和起始U位必须同时填写")

    rack = db.query(Rack).filter(Rack.id == rack_id, Rack.is_active.is_(True)).first()
    if not rack:
        raise HTTPException(status_code=404, detail="机柜不存在或已停用")

    end_u = start_u + u_height - 1
    if start_u < 1 or end_u > rack.total_u:
        raise HTTPException(status_code=400, detail="U位越界")

    conflicts = (
        db.query(Device)
        .filter(
            Device.rack_id == rack_id,
            Device.start_u.isnot(None),
            Device.status != DeviceStatusEnum.off_shelf,
        )
        .all()
    )
    for item in conflicts:
        if device_id and item.id == device_id:
            continue
        item_end = item.start_u + item.u_height - 1
        if not (end_u < item.start_u or start_u > item_end):
            raise HTTPException(status_code=400, detail=f"U位冲突，冲突设备: {item.asset_number}")
    return rack



def sync_administrators(db: Session, device: Device, administrator_ids: Iterable[int]) -> None:
    if administrator_ids:
        administrators = db.query(Administrator).filter(Administrator.id.in_(administrator_ids)).all()
    else:
        administrators = []
    device.administrators = administrators



def sync_ports(device: Device, ports_payload: List) -> None:
    existing = {port.name: port for port in device.ports}
    incoming_names = set()
    new_ports = []
    for port_payload in ports_payload:
        incoming_names.add(port_payload.name)
        port = existing.get(port_payload.name)
        if port:
            port.mac_address = port_payload.mac_address
            port.description = port_payload.description
            port.is_active = port_payload.is_active
            new_ports.append(port)
        else:
            new_ports.append(
                DevicePort(
                    name=port_payload.name,
                    mac_address=port_payload.mac_address,
                    description=port_payload.description,
                    is_active=port_payload.is_active,
                )
            )
    for port in list(device.ports):
        if port.name not in incoming_names:
            device.ports.remove(port)
    for port in new_ports:
        if port not in device.ports:
            device.ports.append(port)



def create_device(db: Session, payload, user: User) -> Device:
    ensure_unique_device_fields(db, payload)
    rack = validate_rack_placement(db, payload.rack_id, payload.start_u, payload.u_height)
    device = Device(
        asset_number=payload.asset_number,
        name=payload.name,
        device_type=payload.device_type,
        model=payload.model,
        serial_number=payload.serial_number,
        purpose=payload.purpose,
        status=payload.status,
        ip_address=payload.ip_address,
        rack_id=payload.rack_id,
        start_u=payload.start_u,
        u_height=payload.u_height,
        cpu=payload.cpu,
        memory_gb=payload.memory_gb,
        gpu=payload.gpu,
        storage_desc=payload.storage_desc,
        operating_system=payload.operating_system,
        notes=payload.notes,
        mounted_at=datetime.utcnow() if rack else None,
    )
    sync_administrators(db, device, payload.administrator_ids)
    sync_ports(device, payload.ports)
    db.add(device)
    db.flush()
    if rack:
        db.add(
            DevicePlacementHistory(
                device_id=device.id,
                action=PlacementActionEnum.mounted,
                to_rack_id=payload.rack_id,
                to_start_u=payload.start_u,
                u_height=payload.u_height,
                changed_by_id=user.id,
                comment="初始上架",
            )
        )
    log_action(
        db,
        user=user,
        action="create",
        module="device",
        target_type="device",
        target_id=str(device.id),
        message=f"新增设备 {device.asset_number}",
        detail_json={"rack_id": payload.rack_id, "start_u": payload.start_u},
    )
    db.commit()
    db.refresh(device)
    return device



def update_device(db: Session, device: Device, payload, user: User) -> Device:
    ensure_unique_device_fields(db, payload, existing_id=device.id)
    old_rack_id, old_start_u = device.rack_id, device.start_u
    validate_rack_placement(db, payload.rack_id, payload.start_u, payload.u_height, device_id=device.id)
    for field in [
        "asset_number",
        "name",
        "device_type",
        "model",
        "serial_number",
        "purpose",
        "status",
        "ip_address",
        "rack_id",
        "start_u",
        "u_height",
        "cpu",
        "memory_gb",
        "gpu",
        "storage_desc",
        "operating_system",
        "notes",
    ]:
        setattr(device, field, getattr(payload, field))
    if payload.rack_id and not device.mounted_at:
        device.mounted_at = datetime.utcnow()
    sync_administrators(db, device, payload.administrator_ids)
    sync_ports(device, payload.ports)
    if old_rack_id != device.rack_id or old_start_u != device.start_u:
        db.add(
            DevicePlacementHistory(
                device_id=device.id,
                action=PlacementActionEnum.moved,
                from_rack_id=old_rack_id,
                to_rack_id=device.rack_id,
                from_start_u=old_start_u,
                to_start_u=device.start_u,
                u_height=device.u_height,
                changed_by_id=user.id,
                comment="编辑位置",
            )
        )
    log_action(
        db,
        user=user,
        action="update",
        module="device",
        target_type="device",
        target_id=str(device.id),
        message=f"更新设备 {device.asset_number}",
    )
    db.commit()
    db.refresh(device)
    return device



def move_device(db: Session, device: Device, rack_id: int, start_u: int, comment: Optional[str], user: User) -> Device:
    if device.status == DeviceStatusEnum.off_shelf:
        raise HTTPException(status_code=400, detail="设备已下架，不能移动")
    validate_rack_placement(db, rack_id, start_u, device.u_height, device_id=device.id)
    old_rack_id, old_start_u = device.rack_id, device.start_u
    device.rack_id = rack_id
    device.start_u = start_u
    device.status = DeviceStatusEnum.active if device.status == DeviceStatusEnum.planned else device.status
    device.mounted_at = device.mounted_at or datetime.utcnow()
    db.add(
        DevicePlacementHistory(
            device_id=device.id,
            action=PlacementActionEnum.moved,
            from_rack_id=old_rack_id,
            to_rack_id=rack_id,
            from_start_u=old_start_u,
            to_start_u=start_u,
            u_height=device.u_height,
            changed_by_id=user.id,
            comment=comment,
        )
    )
    log_action(
        db,
        user=user,
        action="move",
        module="device",
        target_type="device",
        target_id=str(device.id),
        message=f"移动设备 {device.asset_number}",
        detail_json={"from_rack_id": old_rack_id, "to_rack_id": rack_id, "from_start_u": old_start_u, "to_start_u": start_u},
    )
    db.commit()
    db.refresh(device)
    return device



def unmount_device(db: Session, device: Device, comment: Optional[str], user: User) -> Device:
    old_rack_id, old_start_u = device.rack_id, device.start_u
    device.rack_id = None
    device.start_u = None
    device.status = DeviceStatusEnum.off_shelf
    device.unmounted_at = datetime.utcnow()
    db.add(
        DevicePlacementHistory(
            device_id=device.id,
            action=PlacementActionEnum.unmounted,
            from_rack_id=old_rack_id,
            from_start_u=old_start_u,
            u_height=device.u_height,
            changed_by_id=user.id,
            comment=comment,
        )
    )
    log_action(
        db,
        user=user,
        action="unmount",
        module="device",
        target_type="device",
        target_id=str(device.id),
        message=f"下架设备 {device.asset_number}",
        detail_json={"from_rack_id": old_rack_id, "from_start_u": old_start_u},
    )
    db.commit()
    db.refresh(device)
    return device
