import pytest
from app.models.models import Area, DataCenter, Device, Rack
from conftest import TestingSessionLocal


def post_rack(client, headers, code, **fields):
    return client.post('/api/racks', headers=headers, json=dict(data_center_id=1, area_id=1, code=code, **fields))


def test_prefix_and_update_are_idempotent(client, admin_headers):
    created = post_rack(client, admin_headers, ' 001 ')
    assert created.status_code == 200, created.text
    rack = created.json()
    assert rack['code'] == '1_1_001'
    for code in ['001', '1_1_001']:
        response = client.put(f"/api/racks/{rack['id']}", headers=admin_headers, json={**rack, 'code': code})
        assert response.status_code == 200, response.text
        assert response.json()['code'] == '1_1_001'
    assert post_rack(client, admin_headers, '1_1_001').status_code == 409
    assert post_rack(client, admin_headers, 'A01').status_code == 409  # legacy same-area code
    assert post_rack(client, admin_headers, '1_1_A01').status_code == 409


def test_legacy_edit_keeps_device_relation(client, admin_headers):
    with TestingSessionLocal() as db:
        device = Device(name='设备', device_type='server', rack_id=1, start_u=1)
        db.add(device)
        db.commit()
        device_id = device.id
    old = client.get('/api/racks/1', headers=admin_headers).json()
    assert old['code'] == 'A01'
    updated = client.put('/api/racks/1', headers=admin_headers, json=old)
    assert updated.status_code == 200, updated.text
    assert updated.json()['code'] == '1_1_A01'
    assert client.get(f'/api/devices/{device_id}', headers=admin_headers).json()['rack_id'] == 1
    assert client.get('/api/racks/1', headers=admin_headers).json()['code'] == '1_1_A01'


def test_other_area_same_suffix_and_move_reprefix(client, admin_headers):
    with TestingSessionLocal() as db:
        area = Area(data_center_id=1, name='B区')
        db.add(area)
        db.commit()
        area_id = area.id
    response = client.post('/api/racks', headers=admin_headers, json=dict(data_center_id=1, area_id=area_id, code='A01'))
    assert response.status_code == 200, response.text
    assert response.json()['code'] == f'1_{area_id}_A01'
    rack = post_rack(client, admin_headers, 'MOVE').json()
    moved = client.put(f"/api/racks/{rack['id']}", headers=admin_headers, json={**rack, 'area_id': area_id})
    assert moved.status_code == 200, moved.text
    assert moved.json()['code'] == f'1_{area_id}_MOVE'
    # Reject a rename colliding with another rack, preserving original data.
    bad = client.put(f"/api/racks/{rack['id']}", headers=admin_headers, json={**moved.json(), 'code': 'A01'})
    assert bad.status_code == 409
    assert client.get(f"/api/racks/{rack['id']}", headers=admin_headers).json()['code'] == f'1_{area_id}_MOVE'
    wrong_area = client.put(f"/api/racks/{rack['id']}", headers=admin_headers, json={**moved.json(), 'area_id': 999})
    assert wrong_area.status_code == 400


@pytest.mark.parametrize('code', ['', ' ', '1_1_', 'x'*47])
def test_invalid_complete_code(client, admin_headers, code):
    assert post_rack(client, admin_headers, code).status_code == 400


def test_room_filter_combines_search_and_pagination(client, admin_headers):
    with TestingSessionLocal() as db:
        dc = DataCenter(name='第二机房', location='测试', owner='IT')
        db.add(dc)
        db.flush()
        area = Area(data_center_id=dc.id, name='区域')
        db.add(area)
        db.flush()
        dc_id, area_id = dc.id, area.id
        db.add_all([Rack(data_center_id=dc_id, area_id=area_id, code=f'{dc_id}_{area_id}_R{i}') for i in range(3)])
        db.commit()
    response = client.get('/api/racks', params={'data_center_id': dc_id, 'page_size': 1, 'page': 2}, headers=admin_headers)
    assert response.status_code == 200, response.text
    assert response.json()['total'] == 3 and len(response.json()['items']) == 1
    assert response.json()['items'][0]['data_center_id'] == dc_id
    result = client.get('/api/racks', params={'data_center_id': dc_id, 'keyword': 'R2'}, headers=admin_headers).json()
    assert result['total'] == 1 and result['items'][0]['code'].endswith('_R2')
    assert client.get('/api/racks', params={'data_center_id': 999}, headers=admin_headers).json()['total'] == 0
    assert client.get('/api/racks', headers=admin_headers).json()['total'] == 5
