from typing import Dict, List

from app.models.models import DeviceStatusEnum, Rack


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
