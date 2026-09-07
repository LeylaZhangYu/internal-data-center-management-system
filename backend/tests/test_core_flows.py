def test_u_conflict_validation(client, admin_headers):
    payload = {
        "asset_number": "SRV-001",
        "name": "Server 1",
        "device_type": "server",
        "model": "Dell",
        "rack_id": 1,
        "start_u": 1,
        "u_height": 2,
        "administrator_ids": [],
        "ports": [{"name": "eth0"}],
    }
    r1 = client.post("/api/devices", json=payload, headers=admin_headers)
    assert r1.status_code == 200, r1.text

    payload2 = payload.copy()
    payload2["asset_number"] = "SRV-002"
    payload2["name"] = "Server 2"
    payload2["start_u"] = 2
    r2 = client.post("/api/devices", json=payload2, headers=admin_headers)
    assert r2.status_code == 400
    assert "U位冲突" in r2.text


def test_move_device_releases_previous_u(client, admin_headers):
    payload = {
        "asset_number": "SRV-010",
        "name": "Server 10",
        "device_type": "server",
        "model": "Dell",
        "rack_id": 1,
        "start_u": 5,
        "u_height": 2,
        "administrator_ids": [],
        "ports": [{"name": "eth0"}],
    }
    created = client.post("/api/devices", json=payload, headers=admin_headers).json()
    moved = client.post(f"/api/devices/{created['id']}/move", json={"rack_id": 2, "start_u": 10, "comment": "迁移"}, headers=admin_headers)
    assert moved.status_code == 200, moved.text

    payload2 = payload.copy()
    payload2["asset_number"] = "SRV-011"
    payload2["name"] = "Server 11"
    payload2["start_u"] = 5
    r2 = client.post("/api/devices", json=payload2, headers=admin_headers)
    assert r2.status_code == 200, r2.text


def test_port_occupancy_validation(client, admin_headers):
    device1 = client.post("/api/devices", json={
        "asset_number": "SW-100",
        "name": "Switch A",
        "device_type": "switch",
        "model": "Cisco",
        "rack_id": 1,
        "start_u": 20,
        "u_height": 1,
        "administrator_ids": [],
        "ports": [{"name": "Gi0/1"}, {"name": "Gi0/2"}],
    }, headers=admin_headers).json()
    device2 = client.post("/api/devices", json={
        "asset_number": "SRV-100",
        "name": "Server A",
        "device_type": "server",
        "model": "Dell",
        "rack_id": 1,
        "start_u": 22,
        "u_height": 2,
        "administrator_ids": [],
        "ports": [{"name": "eth0"}, {"name": "eth1"}],
    }, headers=admin_headers).json()
    ports = client.get("/api/network/ports", headers=admin_headers).json()
    switch_port = next(p for p in ports if p["device_id"] == device1["id"] and p["name"] == "Gi0/1")
    server_port1 = next(p for p in ports if p["device_id"] == device2["id"] and p["name"] == "eth0")
    server_port2 = next(p for p in ports if p["device_id"] == device2["id"] and p["name"] == "eth1")

    r1 = client.post("/api/network/links", json={"local_port_id": switch_port["id"], "remote_port_id": server_port1["id"], "bandwidth": "10G", "vlan": "100", "status": "up"}, headers=admin_headers)
    assert r1.status_code == 200, r1.text
    r2 = client.post("/api/network/links", json={"local_port_id": switch_port["id"], "remote_port_id": server_port2["id"], "bandwidth": "10G", "vlan": "100", "status": "up"}, headers=admin_headers)
    assert r2.status_code == 400
    assert "端口已被占用" in r2.text


def test_permission_control(client, viewer_headers):
    response = client.post("/api/devices", json={
        "asset_number": "SRV-200",
        "name": "Forbidden",
        "device_type": "server",
        "model": "Dell",
        "rack_id": 1,
        "start_u": 1,
        "u_height": 1,
        "administrator_ids": [],
        "ports": [],
    }, headers=viewer_headers)
    assert response.status_code == 403
