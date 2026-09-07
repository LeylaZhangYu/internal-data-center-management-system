from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.models import DeviceStatusEnum, DeviceTypeEnum, LinkStatusEnum, RackOrientationEnum, RoleEnum


class ORMModel(BaseModel):
    class Config:
        orm_mode = True
        use_enum_values = True


class MessageResponse(ORMModel):
    message: str


class TokenResponse(ORMModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserRead"


class UserLogin(BaseModel):
    username: str
    password: str


class UserRead(ORMModel):
    id: int
    username: str
    full_name: str
    role: RoleEnum
    is_active: bool
    created_at: datetime


class AreaBase(BaseModel):
    name: str
    row_count: int = 1
    column_count: int = 1
    description: Optional[str] = None
    is_active: bool = True


class AreaCreate(AreaBase):
    # 创建区域时机房已由 URL /datacenters/{datacenter_id} 指定
    data_center_id: Optional[int] = None


class AreaUpdate(AreaBase):
    pass


class AreaRead(AreaBase, ORMModel):
    id: int
    data_center_id: int
    created_at: datetime
    updated_at: datetime


class DataCenterBase(BaseModel):
    name: str
    location: str
    owner: str
    contact: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True


class DataCenterCreate(DataCenterBase):
    pass


class DataCenterUpdate(DataCenterBase):
    pass


class DataCenterRead(DataCenterBase, ORMModel):
    id: int
    created_at: datetime
    updated_at: datetime
    areas: List[AreaRead] = []


class RackBase(BaseModel):
    data_center_id: int
    area_id: int
    code: str
    row_position: int = 1
    column_position: int = 1
    x_position: float = 0
    y_position: float = 0
    orientation: RackOrientationEnum = RackOrientationEnum.north
    total_u: int = 42
    is_active: bool = True
    remark: Optional[str] = None


class RackCreate(RackBase):
    pass


class RackUpdate(RackBase):
    pass


class RackRead(RackBase, ORMModel):
    id: int
    created_at: datetime
    updated_at: datetime


class RackUtilization(ORMModel):
    occupied_u: int
    remaining_u: int
    utilization_rate: float


class RackDetail(RackRead):
    utilization: RackUtilization
    device_count: int
    occupancy: List[Dict[str, Any]]


class AdministratorBase(BaseModel):
    name: str
    department: str
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: bool = True


class AdministratorCreate(AdministratorBase):
    pass


class AdministratorUpdate(AdministratorBase):
    pass


class AdministratorRead(AdministratorBase, ORMModel):
    id: int
    created_at: datetime
    updated_at: datetime


class DevicePortBase(BaseModel):
    name: str
    mac_address: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True


class DevicePortCreate(DevicePortBase):
    pass


class DevicePortRead(DevicePortBase, ORMModel):
    id: int
    device_id: int


class DeviceBase(BaseModel):
    asset_number: str
    name: str
    device_type: DeviceTypeEnum
    model: str
    serial_number: Optional[str] = None
    purpose: Optional[str] = None
    status: DeviceStatusEnum = DeviceStatusEnum.planned
    ip_address: Optional[str] = None
    rack_id: Optional[int] = None
    start_u: Optional[int] = Field(default=None, ge=1)
    u_height: int = Field(default=1, ge=1)
    cpu: Optional[str] = None
    memory_gb: Optional[int] = None
    gpu: Optional[str] = None
    storage_desc: Optional[str] = None
    operating_system: Optional[str] = None
    notes: Optional[str] = None
    administrator_ids: List[int] = []
    ports: List[DevicePortCreate] = []


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(DeviceBase):
    pass


class DeviceMoveRequest(BaseModel):
    rack_id: int
    start_u: int = Field(ge=1)
    comment: Optional[str] = None


class DeviceUnmountRequest(BaseModel):
    comment: Optional[str] = None


class DeviceRead(DeviceBase, ORMModel):
    id: int
    mounted_at: Optional[datetime] = None
    unmounted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    administrators: List[AdministratorRead] = []
    ports: List[DevicePortRead] = []


class NetworkLinkBase(BaseModel):
    local_port_id: int
    remote_port_id: int
    bandwidth: Optional[str] = None
    vlan: Optional[str] = None
    status: LinkStatusEnum = LinkStatusEnum.up
    description: Optional[str] = None


class NetworkLinkCreate(NetworkLinkBase):
    pass


class NetworkLinkUpdate(NetworkLinkBase):
    pass


class NetworkLinkRead(NetworkLinkBase, ORMModel):
    id: int
    created_at: datetime
    updated_at: datetime
    local_device_name: str
    remote_device_name: str
    local_port_name: str
    remote_port_name: str


class AuditLogRead(ORMModel):
    id: int
    user_id: Optional[int] = None
    action: str
    module: str
    target_type: str
    target_id: Optional[str] = None
    message: str
    detail_json: Optional[Dict[str, Any]] = None
    created_at: datetime


class OverviewSummary(ORMModel):
    data_center_count: int
    rack_count: int
    device_count: int
    average_rack_utilization: float
    device_status_distribution: Dict[str, int]
    recent_changes: List[AuditLogRead]
    alerts: List[str]


class TopologyNode(ORMModel):
    id: str
    label: str
    type: str


class TopologyEdge(ORMModel):
    id: str
    source: str
    target: str
    label: str
    status: str


class TopologyResponse(ORMModel):
    nodes: List[TopologyNode]
    edges: List[TopologyEdge]


class VisualizationDevice(ORMModel):
    id: int
    asset_number: str
    name: str
    model: str
    ip_address: Optional[str]
    status: str
    start_u: Optional[int]
    u_height: int
    administrators: List[str]
    links: List[str]


class VisualizationRack(ORMModel):
    id: int
    code: str
    x_position: float
    y_position: float
    orientation: str
    total_u: int
    utilization_rate: float
    device_count: int
    devices: List[VisualizationDevice]


class VisualizationArea(ORMModel):
    id: int
    name: str
    racks: List[VisualizationRack]


class VisualizationDataCenter(ORMModel):
    id: int
    name: str
    areas: List[VisualizationArea]


class PagedResponse(ORMModel):
    items: List[Any]
    total: int
    page: int
    page_size: int


TokenResponse.update_forward_refs()
