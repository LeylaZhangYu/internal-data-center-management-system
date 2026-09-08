import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class RoleEnum(str, enum.Enum):
    admin = "admin"


class DeviceTypeEnum(str, enum.Enum):
    server = "server"
    gpu_server = "gpu_server"
    cpu_server = "cpu_server"
    management_node = "management_node"
    switch = "switch"
    storage = "storage"
    pdu = "pdu"
    firewall = "firewall"
    other = "other"


class DeviceStatusEnum(str, enum.Enum):
    planned = "planned"
    active = "active"
    standby = "standby"
    maintenance = "maintenance"
    retired = "retired"
    off_shelf = "off_shelf"


class RackOrientationEnum(str, enum.Enum):
    north = "north"
    south = "south"
    east = "east"
    west = "west"


class LinkStatusEnum(str, enum.Enum):
    up = "up"
    down = "down"
    planned = "planned"


class PlacementActionEnum(str, enum.Enum):
    mounted = "mounted"
    moved = "moved"
    unmounted = "unmounted"


class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


device_admin_association = Table(
    "device_admin_association",
    Base.metadata,
    Column("device_id", ForeignKey("devices.id"), primary_key=True),
    Column("administrator_id", ForeignKey("administrators.id"), primary_key=True),
)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(RoleEnum), nullable=False, default=RoleEnum.admin)
    is_active = Column(Boolean, default=True, nullable=False)


class DataCenter(TimestampMixin, Base):
    __tablename__ = "data_centers"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    location = Column(String(200), nullable=False)
    owner = Column(String(100), nullable=False)
    contact = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    areas = relationship("Area", back_populates="data_center", cascade="all, delete-orphan")
    racks = relationship("Rack", back_populates="data_center")


class Area(TimestampMixin, Base):
    __tablename__ = "areas"

    id = Column(Integer, primary_key=True)
    data_center_id = Column(Integer, ForeignKey("data_centers.id"), nullable=False)
    name = Column(String(100), nullable=False)
    row_count = Column(Integer, default=1, nullable=False)
    column_count = Column(Integer, default=1, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint("data_center_id", "name", name="uq_area_name_in_room"),)

    data_center = relationship("DataCenter", back_populates="areas")
    racks = relationship("Rack", back_populates="area")


class Rack(TimestampMixin, Base):
    __tablename__ = "racks"

    id = Column(Integer, primary_key=True)
    data_center_id = Column(Integer, ForeignKey("data_centers.id"), nullable=False)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False)
    code = Column(String(50), nullable=False)
    row_position = Column(Integer, default=1, nullable=False)
    column_position = Column(Integer, default=1, nullable=False)
    x_position = Column(Float, default=0.0, nullable=False)
    y_position = Column(Float, default=0.0, nullable=False)
    orientation = Column(Enum(RackOrientationEnum), default=RackOrientationEnum.north, nullable=False)
    total_u = Column(Integer, default=42, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    remark = Column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("data_center_id", "code", name="uq_rack_code_in_room"),)

    data_center = relationship("DataCenter", back_populates="racks")
    area = relationship("Area", back_populates="racks")
    devices = relationship("Device", back_populates="rack")


class Administrator(TimestampMixin, Base):
    __tablename__ = "administrators"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    department = Column(String(100), nullable=False)
    phone = Column(String(50), nullable=True)
    email = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    devices = relationship("Device", secondary=device_admin_association, back_populates="administrators")


class Device(TimestampMixin, Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True)
    asset_number = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    device_type = Column(Enum(DeviceTypeEnum), nullable=False)
    model = Column(String(100), nullable=False)
    serial_number = Column(String(100), unique=True, nullable=True)
    purpose = Column(String(200), nullable=True)
    status = Column(Enum(DeviceStatusEnum), default=DeviceStatusEnum.planned, nullable=False)
    ip_address = Column(String(50), unique=True, nullable=True)
    rack_id = Column(Integer, ForeignKey("racks.id"), nullable=True)
    start_u = Column(Integer, nullable=True)
    u_height = Column(Integer, default=1, nullable=False)
    cpu = Column(String(100), nullable=True)
    memory_gb = Column(Integer, nullable=True)
    gpu = Column(String(100), nullable=True)
    storage_desc = Column(String(200), nullable=True)
    operating_system = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    mounted_at = Column(DateTime, nullable=True)
    unmounted_at = Column(DateTime, nullable=True)

    rack = relationship("Rack", back_populates="devices")
    administrators = relationship("Administrator", secondary=device_admin_association, back_populates="devices")
    ports = relationship("DevicePort", back_populates="device", cascade="all, delete-orphan")
    placement_history = relationship("DevicePlacementHistory", back_populates="device", cascade="all, delete-orphan")


class DevicePlacementHistory(Base):
    __tablename__ = "device_placement_history"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    action = Column(Enum(PlacementActionEnum), nullable=False)
    from_rack_id = Column(Integer, ForeignKey("racks.id"), nullable=True)
    to_rack_id = Column(Integer, ForeignKey("racks.id"), nullable=True)
    from_start_u = Column(Integer, nullable=True)
    to_start_u = Column(Integer, nullable=True)
    u_height = Column(Integer, nullable=False)
    changed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    comment = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    device = relationship("Device", back_populates="placement_history")


class DevicePort(TimestampMixin, Base):
    __tablename__ = "device_ports"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    name = Column(String(50), nullable=False)
    mac_address = Column(String(50), nullable=True)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint("device_id", "name", name="uq_device_port_name"),)

    device = relationship("Device", back_populates="ports")
    local_links = relationship("NetworkLink", back_populates="local_port", foreign_keys="NetworkLink.local_port_id")
    remote_links = relationship("NetworkLink", back_populates="remote_port", foreign_keys="NetworkLink.remote_port_id")


class NetworkLink(TimestampMixin, Base):
    __tablename__ = "network_links"

    id = Column(Integer, primary_key=True)
    local_port_id = Column(Integer, ForeignKey("device_ports.id"), nullable=False)
    remote_port_id = Column(Integer, ForeignKey("device_ports.id"), nullable=False)
    bandwidth = Column(String(50), nullable=True)
    vlan = Column(String(50), nullable=True)
    status = Column(Enum(LinkStatusEnum), default=LinkStatusEnum.up, nullable=False)
    description = Column(String(255), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    local_port = relationship("DevicePort", foreign_keys=[local_port_id], back_populates="local_links")
    remote_port = relationship("DevicePort", foreign_keys=[remote_port_id], back_populates="remote_links")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(50), nullable=False)
    module = Column(String(50), nullable=False)
    target_type = Column(String(50), nullable=False)
    target_id = Column(String(50), nullable=True)
    message = Column(String(255), nullable=False)
    detail_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
