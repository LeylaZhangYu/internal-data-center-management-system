from typing import Dict, List, Tuple

from fastapi import HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.models import Area, DataCenter, DeviceStatusEnum, Rack
from app.services.audit import log_action


ACTIVE_DEVICE_STATUSES = {
    DeviceStatusEnum.active,
    DeviceStatusEnum.standby,
    DeviceStatusEnum.maintenance,
    DeviceStatusEnum.planned,
}


def build_rack_occupancy(rack: Rack) -> List[Dict]:
    occupancy = []
    for device in rack.devices:
        if device.rack_id != rack.id or device.start_u is None or device.status == DeviceStatusEnum.off_shelf:
            continue
        occupancy.append(
            {
                "device_id": device.id,
                "asset_number": device.asset_number,
                "name": device.name,
                "start_u": device.start_u,
                "end_u": device.start_u + device.u_height - 1,
                "u_height": device.u_height,
                "status": device.status.value if hasattr(device.status, 'value') else str(device.status),
                "device_type": device.device_type.value if hasattr(device.device_type, 'value') else str(device.device_type),
            }
        )
    occupancy.sort(key=lambda item: item["start_u"])
    return occupancy


def calculate_rack_utilization(rack: Rack) -> Dict[str, float]:
    occupied = sum(device.u_height for device in rack.devices if device.rack_id == rack.id and device.start_u is not None and device.status != DeviceStatusEnum.off_shelf)
    remaining = max(rack.total_u - occupied, 0)
    utilization_rate = round((occupied / rack.total_u * 100) if rack.total_u else 0, 2)
    return {
        "occupied_u": occupied,
        "remaining_u": remaining,
        "utilization_rate": utilization_rate,
    }


def auto_layout_coordinates(row_position: int, column_position: int) -> Tuple[float, float]:
    return (max(column_position - 1, 0) * 2.2, max(row_position - 1, 0) * 4.0)


def rack_code_suffix(code: str, data_center_id: int, area_id: int) -> str:
    prefix = f"{data_center_id}_{area_id}_"
    code = code.strip()
    return code[len(prefix):] if code.startswith(prefix) else code


def rack_values(db: Session, payload, existing=None):
    dc = db.query(DataCenter).filter(DataCenter.id == payload.data_center_id).first()
    if not dc:
        raise HTTPException(status_code=400, detail="机房不存在")
    area = db.query(Area).filter(Area.id == payload.area_id).first()
    if not area or area.data_center_id != dc.id:
        raise HTTPException(status_code=400, detail="区域不存在或不属于指定机房")
    # Existing racks in disabled locations can still be edited without relocation.
    same_location = existing is not None and existing.data_center_id == dc.id and existing.area_id == area.id
    if not same_location and (not dc.is_active or not area.is_active):
        raise HTTPException(status_code=400, detail="机房不存在或已停用" if not dc.is_active else "区域已停用")
    raw_code = payload.code.strip()
    if existing is not None and raw_code == existing.code:
        suffix = rack_code_suffix(raw_code, existing.data_center_id, existing.area_id)
    else:
        suffix = rack_code_suffix(raw_code, dc.id, area.id)
    suffix = suffix.strip()
    code = f"{dc.id}_{area.id}_{suffix}"
    if not suffix:
        raise HTTPException(status_code=400, detail="请填写机柜编号末尾部分")
    if len(code) > 50:
        raise HTTPException(status_code=400, detail="完整机柜编号（含机房、区域前缀）不能超过50个字符")
    # Check legacy unprefixed codes in the same area, and canonical codes room-wide.
    query = db.query(Rack).filter(Rack.data_center_id == dc.id).filter(
        or_(Rack.code == code, and_(Rack.area_id == area.id, Rack.code == suffix)))
    if existing is not None:
        query = query.filter(Rack.id != existing.id)
    if query.first():
        raise HTTPException(status_code=409, detail="该区域内机柜编号已存在（含停用机柜）")
    values = payload.dict()
    values["code"] = code
    values["x_position"], values["y_position"] = auto_layout_coordinates(payload.row_position, payload.column_position)
    return values


def create_rack_record(db: Session, payload, user):
    rack = Rack(**rack_values(db, payload))
    db.add(rack)
    db.flush()
    log_action(db, user=user, action="create", module="rack", target_type="rack",
               target_id=str(rack.id), message=f"新增机柜 {rack.code}")
    db.commit()
    db.refresh(rack)
    return rack
