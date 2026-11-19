from app.models.models import DataCenter, Area, Rack, Device, DevicePort, NetworkLink
from conftest import TestingSessionLocal


def test_network_scene_requires_login(client):
    assert client.get('/api/visualization/network').status_code == 401


def test_empty_scene_keeps_empty_rooms(client, admin_headers):
    response = client.get('/api/visualization/network', headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == {
        'data_centers': [{'id': 1, 'name': '测试机房'}], 'nodes': [], 'links': [],
    }


def test_scene_includes_isolated_unmounted_and_cross_room_devices(client, admin_headers):
    with TestingSessionLocal() as db:
        dc = DataCenter(name='外部机房', location='北京', owner='IT', is_active=False)
        db.add(dc)
        db.flush()
        area = Area(data_center_id=dc.id, name='外部区域')
        db.add(area)
        db.flush()
        rack = Rack(data_center_id=dc.id, area_id=area.id, code='B01')
        db.add(rack)
        db.flush()
        local = Device(name='同名设备', device_type='switch', rack_id=1, start_u=1, status='active')
        remote = Device(name='同名设备', device_type='server', rack_id=rack.id, start_u=3, status='maintenance')
        isolated = Device(name='未上架设备', device_type='storage', status='off_shelf')
        db.add_all([local, remote, isolated])
        db.flush()
        ports = [DevicePort(device_id=local.id, name='eth1'), DevicePort(device_id=remote.id, name='eth2'),
                 DevicePort(device_id=local.id, name='eth3'), DevicePort(device_id=remote.id, name='eth4')]
        db.add_all(ports)
        db.flush()
        db.add_all([
            NetworkLink(local_port_id=ports[0].id, remote_port_id=ports[1].id, bandwidth='100G', vlan='200', status='down', description='跨机房'),
            NetworkLink(local_port_id=ports[2].id, remote_port_id=ports[3].id, status='planned'),
        ])
        db.commit()
    response = client.get('/api/visualization/network', headers=admin_headers)
    assert response.status_code == 200, response.text
    result = response.json()
    assert len(result['data_centers']) == 2
    assert len(result['nodes']) == 3
    local, remote, isolated = result['nodes']
    assert local['id'] != remote['id']
    assert local['data_center_name'] == '测试机房'
    assert remote['data_center_name'] == '外部机房'
    assert remote['area_name'] == '外部区域'
    assert remote['rack_code'] == 'B01'
    assert remote['status'] == 'maintenance'
    assert isolated['data_center_id'] is None
    assert isolated['start_u'] is None
    assert isolated['asset_number'] is None
    assert isolated['administrators'] == []
    assert len(result['links']) == 2
    link = result['links'][0]
    assert (link['source'], link['target']) == (local['id'], remote['id'])
    assert (link['source_port'], link['target_port']) == ('eth1', 'eth2')
    assert link['bandwidth'] == '100G'
    assert link['vlan'] == '200'
    assert link['status'] == 'down'
    assert link['description'] == '跨机房'
    assert result['links'][1]['status'] == 'planned'
