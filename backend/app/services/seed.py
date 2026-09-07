from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.models import (
    Administrator,
    Area,
    DataCenter,
    Device,
    DevicePort,
    DeviceStatusEnum,
    DeviceTypeEnum,
    NetworkLink,
    Rack,
    RackOrientationEnum,
    RoleEnum,
    User,
)


def seed_demo_data(db: Session) -> None:
    if db.query(User).count() > 0:
        return

    admin_user = User(username="admin", full_name="系统管理员", hashed_password=get_password_hash("admin123"), role=RoleEnum.admin)
    db.add(admin_user)
    db.flush()

    dc = DataCenter(name="上海主机房", location="上海市浦东新区XX路18号", owner="基础设施部", contact="infra@example.com", description="总部核心机房")
    db.add(dc)
    db.flush()

    area_a = Area(data_center_id=dc.id, name="A区", row_count=4, column_count=6, description="计算区")
    area_b = Area(data_center_id=dc.id, name="B区", row_count=2, column_count=4, description="网络与存储区")
    db.add_all([area_a, area_b])
    db.flush()

    racks = [
        Rack(data_center_id=dc.id, area_id=area_a.id, code="A01", row_position=1, column_position=1, x_position=0, y_position=0, orientation=RackOrientationEnum.north),
        Rack(data_center_id=dc.id, area_id=area_a.id, code="A02", row_position=1, column_position=2, x_position=2.2, y_position=0, orientation=RackOrientationEnum.north),
        Rack(data_center_id=dc.id, area_id=area_b.id, code="B01", row_position=1, column_position=1, x_position=0, y_position=4, orientation=RackOrientationEnum.east),
    ]
    db.add_all(racks)
    db.flush()

    admins = [
        Administrator(name="张运维", department="基础设施部", phone="13800000001", email="zhang_ops@example.com"),
        Administrator(name="李网络", department="网络部", phone="13800000002", email="li_net@example.com"),
        Administrator(name="王系统", department="平台部", phone="13800000003", email="wang_sys@example.com"),
    ]
    db.add_all(admins)
    db.flush()

    server1 = Device(
        asset_number="SRV-001",
        name="业务服务器01",
        device_type=DeviceTypeEnum.server,
        model="Dell R750",
        serial_number="SN-SRV-001",
        purpose="ERP业务",
        status=DeviceStatusEnum.active,
        ip_address="10.0.0.11",
        rack_id=racks[0].id,
        start_u=1,
        u_height=2,
        cpu="2 x Xeon Gold",
        memory_gb=256,
        gpu="None",
        storage_desc="2TB SSD x4",
        operating_system="Ubuntu 22.04",
    )
    server1.administrators = [admins[0], admins[2]]
    server1.ports = [DevicePort(name="eth0"), DevicePort(name="eth1")]

    switch1 = Device(
        asset_number="SW-001",
        name="接入交换机01",
        device_type=DeviceTypeEnum.switch,
        model="Cisco C9300",
        serial_number="SN-SW-001",
        purpose="接入汇聚",
        status=DeviceStatusEnum.active,
        ip_address="10.0.0.21",
        rack_id=racks[2].id,
        start_u=20,
        u_height=1,
    )
    switch1.administrators = [admins[1]]
    switch1.ports = [DevicePort(name="Gi1/0/1"), DevicePort(name="Gi1/0/2")]

    storage1 = Device(
        asset_number="STO-001",
        name="存储阵列01",
        device_type=DeviceTypeEnum.storage,
        model="NetApp AFF",
        serial_number="SN-STO-001",
        purpose="共享存储",
        status=DeviceStatusEnum.standby,
        ip_address="10.0.0.31",
        rack_id=racks[1].id,
        start_u=10,
        u_height=4,
        storage_desc="All Flash",
    )
    storage1.administrators = [admins[2]]
    storage1.ports = [DevicePort(name="fc0"), DevicePort(name="fc1")]

    db.add_all([server1, switch1, storage1])
    db.flush()

    link = NetworkLink(
        local_port_id=server1.ports[0].id,
        remote_port_id=switch1.ports[0].id,
        bandwidth="10G",
        vlan="100",
        status="up",
        description="业务上联",
        created_by_id=admin_user.id,
        updated_by_id=admin_user.id,
    )
    db.add(link)
    db.commit()
