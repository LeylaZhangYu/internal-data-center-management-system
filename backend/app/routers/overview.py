from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import AuditLog, DataCenter, Device, Rack, User
from app.schemas.common import OverviewSummary
from app.services.rack import calculate_rack_utilization

router = APIRouter(prefix="/overview", tags=["overview"])


@router.get("", response_model=OverviewSummary)
def overview(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    data_center_count = db.query(func.count(DataCenter.id)).scalar() or 0
    rack_count = db.query(func.count(Rack.id)).scalar() or 0
    device_count = db.query(func.count(Device.id)).scalar() or 0
    racks = db.query(Rack).all()
    avg_util = round(sum(calculate_rack_utilization(r)["utilization_rate"] for r in racks) / len(racks), 2) if racks else 0
    distribution = {key: 0 for key in ["planned", "active", "standby", "maintenance", "retired", "off_shelf"]}
    for item in db.query(Device.status, func.count(Device.id)).group_by(Device.status).all():
        distribution[item[0].value] = item[1]
    recent_changes = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(10).all()
    alerts = []
    for rack in racks:
        util = calculate_rack_utilization(rack)["utilization_rate"]
        if util >= 85:
            alerts.append(f"机柜 {rack.code} 利用率 {util}%")
    orphan_devices = db.query(Device).filter(Device.rack_id.is_(None), Device.status != "off_shelf").count()
    if orphan_devices:
        alerts.append(f"有 {orphan_devices} 台设备未上架")
    return OverviewSummary(
        data_center_count=data_center_count,
        rack_count=rack_count,
        device_count=device_count,
        average_rack_utilization=avg_util,
        device_status_distribution=distribution,
        recent_changes=recent_changes,
        alerts=alerts,
    )
