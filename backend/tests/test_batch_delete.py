import pytest
from sqlalchemy import text

from conftest import TestingSessionLocal, engine
from app.models.models import (
    Administrator, AuditLog, Device, DevicePlacementHistory, DevicePort,
    NetworkLink, Rack, device_admin_association,
)
from app.services import deletion


@pytest.fixture(autouse=True)
def enforce_foreign_keys(setup_database):
    # SQLite normally skips FK checks; these tests must also catch PostgreSQL failures.
    with engine.connect() as conn:
        conn.exec_driver_sql('PRAGMA foreign_keys=ON')
    yield
    with engine.connect() as conn:
        conn.exec_driver_sql('PRAGMA foreign_keys=OFF')


@pytest.fixture()
def inventory():
    with TestingSessionLocal() as db:
        administrator = Administrator(name='负责人', department='运维')
        db.add(administrator)
        db.add(Rack(id=3, code='EMPTY', data_center_id=1, area_id=1, is_active=False))
        devices = []
        for index in range(4):
            device = Device(name=f'设备{index}', device_type='server', rack_id=1 if index < 2 else 2,
                            start_u=index + 1, administrators=[administrator],
                            ports=[DevicePort(name=f'eth{i}') for i in range(3)])
            db.add(device)
            devices.append(device)
        db.flush()
        db.add_all([
            NetworkLink(local_port_id=devices[0].ports[0].id, remote_port_id=devices[2].ports[0].id),
            NetworkLink(local_port_id=devices[3].ports[0].id, remote_port_id=devices[1].ports[0].id),
            NetworkLink(local_port_id=devices[0].ports[1].id, remote_port_id=devices[1].ports[1].id),
            NetworkLink(local_port_id=devices[2].ports[1].id, remote_port_id=devices[3].ports[1].id),
        ])
        for device in devices:
            db.add(DevicePlacementHistory(device_id=device.id, action='mounted', to_rack_id=device.rack_id,
                                          u_height=1, changed_by_id=1))
        db.add(DevicePlacementHistory(device_id=devices[2].id, action='moved', from_rack_id=1, to_rack_id=2,
                                      u_height=1, changed_by_id=1))
        db.commit()
        return [device.id for device in devices]


def assert_clean_survivors(ids):
    with TestingSessionLocal() as db:
        assert {device.id for device in db.query(Device)} == set(ids[2:])
        assert db.query(DevicePort).count() == 6
        assert db.query(NetworkLink).count() == 1
        assert db.query(Administrator).count() == 1
        assert len(db.execute(device_admin_association.select()).all()) == 2
        assert db.query(DevicePlacementHistory).count() == 3
        assert not db.execute(text('PRAGMA foreign_key_check')).all()


def test_device_batch_removes_only_selected_and_related_records(client, admin_headers, inventory):
    ids = inventory
    response = client.post('/api/devices/batch-delete', headers=admin_headers, json={'ids': [ids[0], ids[1], ids[0]]})
    assert response.status_code == 200, response.text
    assert response.json()['deleted_count'] == 2
    assert_clean_survivors(ids)
    with TestingSessionLocal() as db:
        assert db.query(Rack).count() == 3
        logs = db.query(AuditLog).filter_by(module='device', action='delete').all()
        assert {log.target_id for log in logs} == {str(ids[0]), str(ids[1])}
    assert client.get('/api/devices', headers=admin_headers).json()['total'] == 2
    rack = client.get('/api/racks/1', headers=admin_headers).json()
    assert rack['device_count'] == 0


def test_rack_batch_deletes_devices_but_keeps_moved_out_history(client, admin_headers, inventory):
    response = client.post('/api/racks/batch-delete', headers=admin_headers, json={'ids': [1, 3, 1]})
    assert response.status_code == 200, response.text
    assert response.json()['deleted_count'] == 2
    assert response.json()['deleted_device_count'] == 2
    assert_clean_survivors(inventory)
    with TestingSessionLocal() as db:
        assert [rack.id for rack in db.query(Rack)] == [2]
        history = db.query(DevicePlacementHistory).filter_by(action='moved').one()
        assert history.from_rack_id is None
        assert history.to_rack_id == 2
        assert db.query(AuditLog).filter_by(module='rack', action='delete').count() == 2


def test_single_rack_delete_uses_same_cleanup(client, admin_headers, inventory):
    response = client.delete('/api/racks/1', headers=admin_headers)
    assert response.status_code == 200, response.text
    assert_clean_survivors(inventory)


@pytest.mark.parametrize('resource', ['racks', 'devices'])
def test_missing_record_prevents_entire_batch(client, admin_headers, inventory, resource):
    response = client.post(f'/api/{resource}/batch-delete', headers=admin_headers, json={'ids': [1, 999]})
    assert response.status_code == 404, response.text
    with TestingSessionLocal() as db:
        assert db.query(Device).count() == 4
        assert db.query(Rack).count() == 3
        assert db.query(NetworkLink).count() == 4
        assert db.query(AuditLog).filter_by(action='delete').count() == 0


def test_failure_after_device_flush_rolls_back_whole_rack_batch(client, admin_headers, inventory, monkeypatch):
    original = deletion.log_action

    def fail_on_rack(*args, **kwargs):
        if kwargs['module'] == 'rack':
            raise RuntimeError('test failure after device cleanup')
        return original(*args, **kwargs)

    monkeypatch.setattr(deletion, 'log_action', fail_on_rack)
    with pytest.raises(RuntimeError, match='test failure'):
        client.post('/api/racks/batch-delete', headers=admin_headers, json={'ids': [1, 3]})
    with TestingSessionLocal() as db:
        assert db.query(Rack).count() == 3
        assert db.query(Device).count() == 4
        assert db.query(DevicePort).count() == 12
        assert db.query(NetworkLink).count() == 4
        assert db.query(DevicePlacementHistory).count() == 5
        assert len(db.execute(device_admin_association.select()).all()) == 4
        assert db.query(AuditLog).filter_by(action='delete').count() == 0


@pytest.mark.parametrize('resource', ['racks', 'devices'])
@pytest.mark.parametrize('ids', [[], [0], [-1], [True], ['1'], list(range(1, 102))])
def test_invalid_batch_rejected(client, admin_headers, resource, ids):
    response = client.post(f'/api/{resource}/batch-delete', headers=admin_headers, json={'ids': ids})
    assert response.status_code == 422, response.text


@pytest.mark.parametrize('resource', ['racks', 'devices'])
def test_batch_delete_requires_authentication(client, resource):
    response = client.post(f'/api/{resource}/batch-delete', json={'ids': [1]})
    assert response.status_code == 401


def test_unmounted_device_can_be_deleted(client, admin_headers):
    created = client.post('/api/devices', headers=admin_headers,
                          json={'name': '下架设备', 'device_type': 'server', 'status': 'off_shelf'}).json()
    response = client.post('/api/devices/batch-delete', headers=admin_headers, json={'ids': [created['id']]})
    assert response.status_code == 200, response.text
    assert client.get(f"/api/devices/{created['id']}", headers=admin_headers).status_code == 404
