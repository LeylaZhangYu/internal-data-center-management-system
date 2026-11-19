from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import Area, DataCenter, Device, DevicePort, NetworkLink, Rack, User
from app.schemas.common import VisualizationArea, VisualizationDataCenter, VisualizationDevice, VisualizationRack
from app.schemas.common import NetworkSceneResponse
from app.services.rack import calculate_rack_utilization

router = APIRouter(prefix="/visualization", tags=["visualization"])


@router.get("/layout", response_model=List[VisualizationDataCenter])
def get_layout(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    areas = db.query(Area).options(joinedload(Area.data_center), joinedload(Area.racks).joinedload(Rack.devices).joinedload(Device.administrators)).all()
    links = db.query(NetworkLink).options(joinedload(NetworkLink.local_port).joinedload(DevicePort.device), joinedload(NetworkLink.remote_port).joinedload(DevicePort.device)).all()
    device_links = {}
    for link in links:
        device_links.setdefault(link.local_port.device_id, []).append(f"{link.local_port.name} → {link.remote_port.device.name}:{link.remote_port.name}")
        device_links.setdefault(link.remote_port.device_id, []).append(f"{link.remote_port.name} → {link.local_port.device.name}:{link.local_port.name}")

    grouped = {}
    for area in areas:
        dc = area.data_center
        grouped.setdefault(dc.id, {"id": dc.id, "name": dc.name, "areas": []})
        area_payload = VisualizationArea(
            id=area.id,
            name=area.name,
            racks=[
                VisualizationRack(
                    id=rack.id,
                    code=rack.code,
                    x_position=rack.x_position,
                    y_position=rack.y_position,
                    orientation=rack.orientation.value,
                    total_u=rack.total_u,
                    utilization_rate=calculate_rack_utilization(rack)["utilization_rate"],
                    device_count=len([d for d in rack.devices if d.rack_id == rack.id and d.start_u]),
                    devices=[
                        VisualizationDevice(
                            id=d.id,
                            asset_number=d.asset_number,
                            name=d.name,
                            model=d.model,
                            ip_address=d.ip_address,
                            status=d.status.value,
                            start_u=d.start_u,
                            u_height=d.u_height,
                            administrators=[a.name for a in d.administrators],
                            links=device_links.get(d.id, []),
                        )
                        for d in sorted([x for x in rack.devices if x.start_u], key=lambda x: x.start_u)
                    ],
                )
                for rack in area.racks
            ],
        )
        grouped[dc.id]["areas"].append(area_payload)
    return [VisualizationDataCenter(**value) for value in grouped.values()]


@router.get("/network", response_model=NetworkSceneResponse)
def get_network_scene(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Include unmounted/isolated devices; only stored port links become edges."""
    devices = db.query(Device).options(
        joinedload(Device.rack).joinedload(Rack.data_center),
        joinedload(Device.rack).joinedload(Rack.area),
        joinedload(Device.administrators),
    ).order_by(Device.id).all()
    links = db.query(NetworkLink).options(
        joinedload(NetworkLink.local_port), joinedload(NetworkLink.remote_port),
    ).order_by(NetworkLink.id).all()
    nodes = []
    for device in devices:
        rack = device.rack
        nodes.append({
            "id": device.id, "name": device.name, "device_type": device.device_type.value,
            "status": device.status.value, "asset_number": device.asset_number,
            "model": device.model, "ip_address": device.ip_address,
            "purpose": device.purpose, "notes": device.notes,
            "data_center_id": rack.data_center_id if rack else None,
            "data_center_name": rack.data_center.name if rack else None,
            "area_name": rack.area.name if rack else None,
            "rack_code": rack.code if rack else None,
            "start_u": device.start_u, "u_height": device.u_height,
            "administrators": [admin.name for admin in device.administrators],
        })
    return {
        "data_centers": [{"id": dc.id, "name": dc.name} for dc in db.query(DataCenter).order_by(DataCenter.id).all()],
        "nodes": nodes,
        "links": [{
            "id": link.id, "source": link.local_port.device_id, "target": link.remote_port.device_id,
            "source_port": link.local_port.name, "target_port": link.remote_port.name,
            "bandwidth": link.bandwidth, "vlan": link.vlan, "status": link.status.value,
            "description": link.description,
        } for link in links],
    }
