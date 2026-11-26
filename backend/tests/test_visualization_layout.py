from app.models.models import DataCenter, Device, DevicePort, NetworkLink, Rack
from conftest import TestingSessionLocal


def test_layout_requires_auth_and_keeps_empty_rooms(client, admin_headers):
    assert client.get('/api/visualization/layout').status_code == 401
    with TestingSessionLocal() as db:
        db.add(DataCenter(name='无区域机房', location='测试', owner='IT'))
        db.commit()
    result = client.get('/api/visualization/layout', headers=admin_headers)
    assert result.status_code == 200, result.text
    assert [dc['name'] for dc in result.json()] == ['测试机房', '无区域机房']
    assert result.json()[1]['areas'] == []


def test_layout_count_and_capacity_exclude_off_shelf_devices(client, admin_headers):
    with TestingSessionLocal() as db:
        db.add_all([
            Device(name='已上架', device_type='server', rack_id=1, start_u=1, u_height=2, status='active'),
            Device(name='已下架但遗留U位', device_type='server', rack_id=1, start_u=5, u_height=4, status='off_shelf'),
            Device(name='无U位', device_type='server', rack_id=1, status='planned'),
        ])
        db.commit()
    result = client.get('/api/visualization/layout', headers=admin_headers)
    assert result.status_code == 200, result.text
    rack = next(r for r in result.json()[0]['areas'][0]['racks'] if r['id'] == 1)
    assert rack['device_count'] == len(rack['devices']) == 1
    assert rack['devices'][0]['name'] == '已上架'
    assert rack['utilization_rate'] == round(2 / 42 * 100, 2)
    # Network topology intentionally keeps off-shelf and isolated nodes.
    network = client.get('/api/visualization/network', headers=admin_headers).json()
    assert len(network['nodes']) == 3


def test_layout_passes_rack_categories_through_for_3d_rendering(client, admin_headers):
    with TestingSessionLocal() as db:
        rack = db.get(Rack, 1)
        rack.category = 'row_air_conditioner'
        db.get(Rack, 2).category = 'power_distribution_cabinet'
        db.commit()
    result = client.get('/api/visualization/layout', headers=admin_headers)
    assert result.status_code == 200, result.text
    categories = {rack['id']: rack['category'] for rack in result.json()[0]['areas'][0]['racks']}
    assert categories == {1: 'row_air_conditioner', 2: 'power_distribution_cabinet'}


def test_legacy_dangling_links_do_not_break_either_scene(client, admin_headers):
    with TestingSessionLocal() as db:
        device = Device(name='正常设备', device_type='server', rack_id=1, start_u=1)
        db.add(device)
        db.flush()
        port = DevicePort(device_id=device.id, name='eth0')
        db.add(port)
        db.flush()
        # Old SQLite installations did not enable FK checks.
        db.add(NetworkLink(local_port_id=port.id, remote_port_id=999999, status='up'))
        db.commit()
    for endpoint in ('layout', 'network'):
        response = client.get('/api/visualization/' + endpoint, headers=admin_headers)
        assert response.status_code == 200, response.text
    assert client.get('/api/visualization/network', headers=admin_headers).json()['links'] == []
