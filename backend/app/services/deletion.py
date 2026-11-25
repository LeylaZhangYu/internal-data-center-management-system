"""Deletion helpers share the caller's transaction; no partial commits."""
from fastapi import HTTPException
from sqlalchemy import or_

from app.models.models import Device, DevicePlacementHistory, DevicePort, NetworkLink
from app.services.audit import log_action


def deletion_targets(db, model, ids, label):
    ids = set(ids)
    records = db.query(model).filter(model.id.in_(ids)).order_by(model.id).with_for_update().all()
    missing = ids - {record.id for record in records}
    if missing:
        raise HTTPException(status_code=404, detail=f"部分{label}已不存在（ID：{', '.join(map(str, sorted(missing)))}），未执行删除，请刷新列表")
    return records


def delete_devices(db, devices, user):
    if not devices:
        return
    port_ids = db.query(DevicePort.id).filter(DevicePort.device_id.in_([device.id for device in devices]))
    db.query(NetworkLink).filter(or_(NetworkLink.local_port_id.in_(port_ids), NetworkLink.remote_port_id.in_(port_ids))).delete(synchronize_session="fetch")
    for device in devices:
        log_action(db, user=user, action="delete", module="device", target_type="device",
                   target_id=str(device.id), message=f"删除设备 {device.asset_number or device.name}",
                   detail_json={"rack_id": device.rack_id})
        # ORM cascades remove ports/history and the administrator association, not administrators.
        db.delete(device)
    db.flush()


def delete_racks(db, racks, user):
    rack_ids = [rack.id for rack in racks]
    devices = db.query(Device).filter(Device.rack_id.in_(rack_ids)).with_for_update().all()
    delete_devices(db, devices, user)
    # Devices that previously moved out keep their history without dangling rack references.
    for field in (DevicePlacementHistory.from_rack_id, DevicePlacementHistory.to_rack_id):
        db.query(DevicePlacementHistory).filter(field.in_(rack_ids)).update({field: None}, synchronize_session="fetch")
    for rack in racks:
        log_action(db, user=user, action="delete", module="rack", target_type="rack",
                   target_id=str(rack.id), message=f"删除机柜 {rack.code}")
        db.delete(rack)
    db.flush()
    return len(devices)
