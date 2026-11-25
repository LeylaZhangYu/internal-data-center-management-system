import csv
import io

import pytest
from openpyxl import Workbook

from conftest import TestingSessionLocal
from app.models.models import Area, DataCenter, Device, Rack


@pytest.fixture()
def other_room():
    with TestingSessionLocal() as db:
        room = DataCenter(name='第二机房', location='北京', owner='IT')
        db.add(room)
        db.flush()
        area = Area(data_center_id=room.id, name='B区')
        db.add(area)
        db.flush()
        rack = Rack(data_center_id=room.id, area_id=area.id, code='B01')
        db.add(rack)
        db.commit()
        return room.id, area.id, rack.id


def create(client, headers, **kwargs):
    payload = dict(name='服务器', device_type='server', rack_id=1, start_u=1, asset_number='001')
    payload.update(kwargs)
    return client.post('/api/devices', headers=headers, json=payload)


def test_asset_prefix_uniqueness_and_room_scope(client, admin_headers, other_room):
    first = create(client, admin_headers)
    assert first.status_code == 200, first.text
    assert first.json()['asset_number'] == '1_1_001'
    assert isinstance(first.json()['id'], int)
    for value in ('001', '1_1_001'):
        duplicate = create(client, admin_headers, rack_id=2, asset_number=value)
        assert duplicate.status_code == 400, duplicate.text
        assert duplicate.json()['detail'] == '资产编号已存在'
    room, area, rack = other_room
    second = create(client, admin_headers, rack_id=rack, asset_number='1_1_001')
    assert second.status_code == 200, second.text
    assert second.json()['asset_number'] == f'{room}_{area}_001'
    saved = client.put(f"/api/devices/{second.json()['id']}", headers=admin_headers, json=second.json())
    assert saved.status_code == 200, saved.text
    assert saved.json()['asset_number'] == second.json()['asset_number']


def test_existing_number_stays_stable_and_can_be_changed(client, admin_headers, other_room):
    with TestingSessionLocal() as db:
        legacy = Device(name='旧设备', device_type='server', asset_number='LEGACY', rack_id=1, start_u=1)
        db.add(legacy)
        db.commit()
        device_id = legacy.id
    detail = client.get(f'/api/devices/{device_id}', headers=admin_headers).json()
    saved = client.put(f'/api/devices/{device_id}', headers=admin_headers, json={**detail, 'name': '改名称'})
    assert saved.status_code == 200, saved.text
    assert saved.json()['asset_number'] == 'LEGACY'
    room, area, rack = other_room
    moved = client.post(f'/api/devices/{device_id}/move', headers=admin_headers, json={'rack_id': rack, 'start_u': 2})
    assert moved.status_code == 200, moved.text
    assert moved.json()['asset_number'] == 'LEGACY'
    renamed = client.put(f'/api/devices/{device_id}', headers=admin_headers, json={**moved.json(), 'asset_number': 'NEW'})
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()['asset_number'] == f'{room}_{area}_NEW'
    unmounted = client.post(f'/api/devices/{device_id}/unmount', headers=admin_headers, json={})
    assert unmounted.status_code == 200, unmounted.text
    assert unmounted.json()['asset_number'] == f'{room}_{area}_NEW'
    assert unmounted.json()['rack_id'] is None


@pytest.mark.parametrize('value', ['1_1_', '1_1_   ', 'x' * 97])
def test_invalid_or_too_long_code_is_rejected(client, admin_headers, value):
    response = create(client, admin_headers, asset_number=value)
    assert response.status_code == 400, response.text


def test_room_filter_combines_with_search_and_pagination(client, admin_headers, other_room):
    room, _, rack = other_room
    assert create(client, admin_headers, name='匹配-本地', status='active').status_code == 200
    for i in range(3):
        assert create(client, admin_headers, name=f'匹配-{i}', rack_id=rack, start_u=i + 1, asset_number=f'B{i}', status='active').status_code == 200
    assert create(client, admin_headers, name='匹配-维护', rack_id=rack, start_u=4, asset_number='B4', status='maintenance').status_code == 200
    assert create(client, admin_headers, name='匹配-未上架', rack_id=None, start_u=None, asset_number=None, status='active').status_code == 200
    params = dict(data_center_id=room, keyword='匹配', status='active', device_type='server', page_size=2)
    first = client.get('/api/devices', headers=admin_headers, params=params)
    assert first.status_code == 200, first.text
    assert first.json()['total'] == 3
    assert len(first.json()['items']) == 2
    assert all(item['rack_id'] == rack for item in first.json()['items'])
    second = client.get('/api/devices', headers=admin_headers, params={**params, 'page': 2}).json()
    assert second['total'] == 3
    assert len(second['items']) == 1
    assert second['items'][0]['id'] not in {item['id'] for item in first.json()['items']}
    assert client.get('/api/devices', headers=admin_headers).json()['total'] == 6
    assert client.get('/api/devices', headers=admin_headers, params={'data_center_id': 999}).json()['total'] == 0
    assert client.get('/api/devices', headers=admin_headers, params={**params, 'rack_id': 1}).json()['total'] == 0


@pytest.mark.parametrize('extension', ['csv', 'xlsx'])
def test_import_and_export_use_same_complete_number(client, admin_headers, extension):
    rows = [['设备名称', '设备类型', '资产编号', '机柜ID', '起始U位'], ['导入设备', 'server', 'S001', 1, 1]]
    if extension == 'csv':
        output = io.StringIO()
        csv.writer(output).writerows(rows)
        content = output.getvalue().encode('utf-8-sig')
    else:
        book = Workbook()
        for row in rows:
            book.active.append(row)
        output = io.BytesIO()
        book.save(output)
        book.close()
        content = output.getvalue()
    response = client.post('/api/devices/import', headers=admin_headers, files={'file': (f'import.{extension}', content)})
    assert response.status_code == 200, response.text
    assert response.json()['message'] == '导入完成，成功 1 条'
    exported = client.get('/api/devices/export/csv', headers=admin_headers)
    result = list(csv.DictReader(io.StringIO(exported.content.decode('utf-8-sig'))))
    assert result[0]['资产编号'] == '1_1_S001'
