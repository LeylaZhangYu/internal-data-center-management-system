from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.permissions import require_roles
from app.models.models import DevicePort, NetworkLink, User
from app.schemas.common import NetworkLinkCreate, NetworkLinkRead, NetworkLinkUpdate, TopologyEdge, TopologyNode, TopologyResponse
from app.services.audit import log_action

router = APIRouter(prefix="/network", tags=["network"])



def ensure_port_available(db: Session, local_port_id: int, remote_port_id: int, exclude_id: Optional[int] = None):
    if local_port_id == remote_port_id:
        raise HTTPException(status_code=400, detail="不能连接同一端口")
    query = db.query(NetworkLink).filter(
        or_(
            NetworkLink.local_port_id.in_([local_port_id, remote_port_id]),
            NetworkLink.remote_port_id.in_([local_port_id, remote_port_id]),
        )
    )
    if exclude_id:
        query = query.filter(NetworkLink.id != exclude_id)
    if query.first():
        raise HTTPException(status_code=400, detail="端口已被占用")



def serialize_link(link: NetworkLink) -> NetworkLinkRead:
    return NetworkLinkRead(
        id=link.id,
        local_port_id=link.local_port_id,
        remote_port_id=link.remote_port_id,
        bandwidth=link.bandwidth,
        vlan=link.vlan,
        status=link.status,
        description=link.description,
        created_at=link.created_at,
        updated_at=link.updated_at,
        local_device_name=link.local_port.device.name,
        remote_device_name=link.remote_port.device.name,
        local_port_name=link.local_port.name,
        remote_port_name=link.remote_port.name,
    )


@router.get("/ports")
def list_ports(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ports = db.query(DevicePort).options(joinedload(DevicePort.device)).order_by(DevicePort.id.desc()).all()
    return [{"id": p.id, "name": p.name, "device_id": p.device_id, "device_name": p.device.name} for p in ports]


@router.get("/links", response_model=List[NetworkLinkRead])
def list_links(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    links = db.query(NetworkLink).options(joinedload(NetworkLink.local_port).joinedload(DevicePort.device), joinedload(NetworkLink.remote_port).joinedload(DevicePort.device)).order_by(NetworkLink.id.desc()).all()
    return [serialize_link(item) for item in links]


@router.post("/links", response_model=NetworkLinkRead)
def create_link(
    payload: NetworkLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    ensure_port_available(db, payload.local_port_id, payload.remote_port_id)
    link = NetworkLink(**payload.dict(), created_by_id=current_user.id, updated_by_id=current_user.id)
    db.add(link)
    db.commit()
    db.refresh(link)
    link = db.query(NetworkLink).options(joinedload(NetworkLink.local_port).joinedload(DevicePort.device), joinedload(NetworkLink.remote_port).joinedload(DevicePort.device)).filter(NetworkLink.id == link.id).first()
    log_action(db, user=current_user, action="create", module="network", target_type="link", target_id=str(link.id), message="新增网络连接")
    db.commit()
    return serialize_link(link)


@router.put("/links/{link_id}", response_model=NetworkLinkRead)
def update_link(
    link_id: int,
    payload: NetworkLinkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    link = db.query(NetworkLink).filter(NetworkLink.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="链路不存在")
    ensure_port_available(db, payload.local_port_id, payload.remote_port_id, exclude_id=link_id)
    for key, value in payload.dict().items():
        setattr(link, key, value)
    link.updated_by_id = current_user.id
    db.commit()
    link = db.query(NetworkLink).options(joinedload(NetworkLink.local_port).joinedload(DevicePort.device), joinedload(NetworkLink.remote_port).joinedload(DevicePort.device)).filter(NetworkLink.id == link.id).first()
    log_action(db, user=current_user, action="update", module="network", target_type="link", target_id=str(link.id), message="更新网络连接")
    db.commit()
    return serialize_link(link)


@router.delete("/links/{link_id}")
def delete_link(
    link_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    link = db.query(NetworkLink).filter(NetworkLink.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="链路不存在")
    db.delete(link)
    log_action(db, user=current_user, action="delete", module="network", target_type="link", target_id=str(link_id), message="删除网络连接")
    db.commit()
    return {"message": "链路已删除"}


@router.get("/topology", response_model=TopologyResponse)
def topology(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    links = db.query(NetworkLink).options(joinedload(NetworkLink.local_port).joinedload(DevicePort.device), joinedload(NetworkLink.remote_port).joinedload(DevicePort.device)).all()
    nodes = {}
    edges = []
    for link in links:
        local_device = link.local_port.device
        remote_device = link.remote_port.device
        nodes[f"device-{local_device.id}"] = TopologyNode(id=f"device-{local_device.id}", label=f"{local_device.name}\n{link.local_port.name}", type=local_device.device_type.value)
        nodes[f"device-{remote_device.id}"] = TopologyNode(id=f"device-{remote_device.id}", label=f"{remote_device.name}\n{link.remote_port.name}", type=remote_device.device_type.value)
        edges.append(TopologyEdge(id=f"link-{link.id}", source=f"device-{local_device.id}", target=f"device-{remote_device.id}", label=f"{link.bandwidth or '-'} / VLAN {link.vlan or '-'}", status=link.status.value))
    return TopologyResponse(nodes=list(nodes.values()), edges=edges)
