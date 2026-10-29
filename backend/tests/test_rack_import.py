import io

import pytest
from openpyxl import Workbook, load_workbook
from sqlalchemy import event

from app.models.models import Area, DataCenter, Rack, AuditLog
from app.services.rack_import import COLUMNS, normalize_rack_row
from conftest import TestingSessionLocal

HEADERS = [label for _, label in COLUMNS]


def workbook_bytes(rows, headers=None):
    wb = Workbook()
    wb.active.append(headers if headers is not None else HEADERS)
    for row in rows:
        wb.active.append(row)
    stream = io.BytesIO()
    wb.save(stream)
    wb.close()
    return stream.getvalue()


def upload(client, auth, rows, **options):
    content = workbook_bytes(rows, **options)
    return client.post('/api/racks/import', headers=auth, files={'file': ('racks.xlsx', content)})


def test_template_roundtrip(client, admin_headers):
    response = client.get('/api/racks/template/xlsx', headers=admin_headers)
    assert response.status_code == 200
    assert 'spreadsheetml' in response.headers['content-type']
    assert 'racks_template.xlsx' in response.headers['content-disposition']
    wb = load_workbook(io.BytesIO(response.content))
    assert wb.sheetnames == ['机柜导入模板', '填写说明', '机房区域参考']
    ws = wb.active
    assert list(next(ws.values)) == HEADERS
    assert ws.max_row == 1
    assert ws.freeze_panes == 'A2'
    assert len(ws.data_validations.dataValidation) == 7
    assert list(wb['机房区域参考'].values)[1][:4] == (1, '测试机房', 1, 'A区')
    ws.append([1, 1, '001', 2, 3, '东向', 48, '停用', '测试备注'])
    stream = io.BytesIO()
    wb.save(stream)
    wb.close()
    imported = client.post('/api/racks/import', headers=admin_headers, files={'file': ('racks.xlsx', stream.getvalue())})
    assert imported.status_code == 200, imported.text
    assert imported.json()['imported'] == 1
    with TestingSessionLocal() as db:
        rack = db.query(Rack).filter(Rack.code == '001').one()
        assert (rack.row_position, rack.column_position, rack.total_u) == (2, 3, 48)
        assert (rack.x_position, rack.y_position) == (4.4, 4.0)
        assert rack.orientation.value == 'east' and not rack.is_active
        assert db.query(AuditLog).filter(AuditLog.target_id == str(rack.id), AuditLog.module == 'rack').count() == 1


def test_partial_import_and_actual_excel_rows(client, admin_headers):
    response = upload(client, admin_headers, [
        [1, 1, 'A01'],  # existing
        [None] * 9,    # skip blank row, preserve subsequent row numbers
        [1, 1, 'NEW1'],
        [1, 1, 'NEW1'],
        [1, 1, 'BAD', 1.5],
        [1, 1, 'NEW2', None, None, 'west', 42, 'true'],
    ])
    assert response.status_code == 200, response.text
    result = response.json()
    assert (result['total'], result['imported'], result['failed']) == (5, 2, 3)
    assert [e['row'] for e in result['errors']] == [2, 5, 6]
    with TestingSessionLocal() as db:
        assert db.query(Rack).count() == 4
        assert db.query(Rack).filter(Rack.code == 'A01').one().total_u == 42
        rack = db.query(Rack).filter(Rack.code == 'NEW1').one()
        assert (rack.row_position, rack.column_position, rack.total_u, rack.is_active) == (1, 1, 42, True)


def test_associations_and_disabled_parents(client, admin_headers):
    with TestingSessionLocal() as db:
        dc = DataCenter(name='其他机房', location='测试', owner='IT')
        db.add(dc)
        db.flush()
        db.add_all([Area(data_center_id=dc.id, name='其他区域'), Area(data_center_id=1, name='停用区域', is_active=False)])
        db.commit()
    response = upload(client, admin_headers, [[999, 1, 'BAD1'], [1, 999, 'BAD2'], [1, 2, 'BAD3'], [1, 3, 'BAD4'], [2, 2, 'A01']])
    assert response.json()['imported'] == 1
    assert response.json()['failed'] == 4
    with TestingSessionLocal() as db:
        dc = db.get(DataCenter, 2)
        dc.is_active = False
        db.commit()
    response = upload(client, admin_headers, [[2, 2, 'BAD5']])
    assert response.json()['failed'] == 1
    assert '机房不存在或已停用' in response.text


@pytest.mark.parametrize('field,value', [('row_position', 0), ('column_position', -1), ('total_u', '3.5'),
                                        ('total_u', 'NaN'), ('data_center_id', True), ('code', ' '),
                                        ('code', 'x' * 51), ('orientation', 'unknown'), ('is_active', 'unknown')])
def test_invalid_values(field, value):
    row = {'data_center_id': 1, 'area_id': 1, 'code': 'TEST', field: value}
    with pytest.raises(ValueError):
        normalize_rack_row(row)


def test_english_headers_and_formulas(client, admin_headers):
    response = upload(client, admin_headers, [[1, 1, 'ENGLISH'], [1, 1, '=1+1']], headers=[key for key, _ in COLUMNS])
    assert response.status_code == 200, response.text
    assert response.json()['imported'] == 1
    assert response.json()['errors'] == [{'row': 3, 'message': '不支持公式，请填写实际值'}]


@pytest.mark.parametrize('headers,rows', [([], []), (HEADERS, []), (['机房ID', '区域ID'], [[1, 1]]),
                                        (['机房ID', '区域ID', '机柜编号', '机柜编号'], [[1, 1, 'X', 'Y']]),
                                        (['机房ID', '区域ID', '错别字'], [[1, 1, 'X']])])
def test_bad_or_empty_workbooks(client, admin_headers, headers, rows):
    response = upload(client, admin_headers, rows, headers=headers)
    assert response.status_code == 400, response.text


def test_auth_and_file_limits(client, admin_headers):
    assert client.get('/api/racks/template/xlsx').status_code == 401
    assert upload(client, {}, [[1, 1, 'X']]).status_code == 401
    for name, content, expected in [('bad.xls', b'bad', 400), ('bad.xlsx', b'broken', 400), ('large.xlsx', b'x' * (5 * 1024 * 1024 + 1), 413)]:
        response = client.post('/api/racks/import', headers=admin_headers, files={'file': (name, content)})
        assert response.status_code == expected, response.text
    assert upload(client, admin_headers, [[1, 1, str(i)] for i in range(1001)]).status_code == 400


def test_single_create_uses_same_rules(client, admin_headers):
    payload = dict(data_center_id=1, area_id=1, code='MANUAL', row_position=2, column_position=3)
    created = client.post('/api/racks', headers=admin_headers, json=payload)
    assert created.status_code == 200, created.text
    assert created.json()['x_position'] == 4.4
    assert created.json()['y_position'] == 4.0
    assert client.post('/api/racks', headers=admin_headers, json=payload).status_code == 409
    assert client.post('/api/racks', headers=admin_headers, json=dict(payload, code='BAD', area_id=999)).status_code == 400


def test_failed_insert_rolls_back_and_continues(client, admin_headers):
    # Force a DB constraint error after validation; the next row must still succeed.
    def break_insert(mapper, connection, target):
        if target.code == 'FAIL':
            target.code = 'A01'
    event.listen(Rack, 'before_insert', break_insert)
    try:
        result = upload(client, admin_headers, [[1, 1, 'FAIL'], [1, 1, 'AFTER']])
        assert result.status_code == 200, result.text
        assert result.json()['failed'] == 1 and result.json()['imported'] == 1
        with TestingSessionLocal() as db:
            assert db.query(Rack).filter(Rack.code == 'AFTER').count() == 1
    finally:
        event.remove(Rack, 'before_insert', break_insert)
