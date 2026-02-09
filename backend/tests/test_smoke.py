def test_smoke_flow(client):
    admin_payload = {
        "email": "admin@test.local",
        "password": "AdminPass123",
        "full_name": "Admin User",
    }
    member_payload = {
        "email": "member@test.local",
        "password": "MemberPass123",
        "full_name": "Member User",
    }

    r = client.post("/auth/register", json=admin_payload)
    assert r.status_code == 201
    r = client.post("/auth/register", json=member_payload)
    assert r.status_code == 201

    r = client.post(
        "/auth/login",
        data={"username": admin_payload["email"], "password": admin_payload["password"]},
    )
    assert r.status_code == 200
    admin_token = r.json()["access_token"]

    r = client.post(
        "/auth/login",
        data={"username": member_payload["email"], "password": member_payload["password"]},
    )
    assert r.status_code == 200
    member_token = r.json()["access_token"]

    headers = {"Authorization": f"Bearer {admin_token}"}
    r = client.post("/orgs", json={"name": "Test Org"}, headers=headers)
    assert r.status_code == 201
    org = r.json()

    r = client.post(
        "/orgs/join-request",
        json={"org_code": org["join_code"]},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert r.status_code == 201
    join_request = r.json()

    r = client.post(
        f"/orgs/{org['id']}/join-requests/{join_request['id']}/approve",
        headers=headers,
    )
    assert r.status_code == 200

    r = client.post(
        f"/orgs/{org['id']}/projects",
        json={"name": "Project X", "description": "Demo"},
        headers=headers,
    )
    assert r.status_code == 201
    project = r.json()

    r = client.post(
        f"/orgs/{org['id']}/teams",
        json={"name": "Team A", "project_id": project["id"]},
        headers=headers,
    )
    assert r.status_code == 201
    team = r.json()

    r = client.post(
        f"/orgs/{org['id']}/teams/{team['id']}/members",
        json={"user_id": join_request["user_id"]},
        headers=headers,
    )
    assert r.status_code == 200

    r = client.post(
        f"/orgs/{org['id']}/tasks",
        json={
            "title": "Task 1",
            "description": "Demo",
            "assignee_id": join_request["user_id"],
            "team_id": team["id"],
        },
        headers=headers,
    )
    assert r.status_code == 201

    r = client.get(
        f"/orgs/{org['id']}/reports/kpi",
        headers=headers,
    )
    assert r.status_code == 200

    r = client.get(
        f"/orgs/{org['id']}/reports/projects/kpi",
        headers=headers,
    )
    assert r.status_code == 200

    r = client.get(
        f"/orgs/{org['id']}/metrics/users/{join_request['user_id']}",
        headers=headers,
    )
    assert r.status_code == 200

    r = client.get(
        f"/orgs/{org['id']}/performance/activity-per-task",
        params={"user_id": join_request["user_id"], "project_id": project["id"]},
        headers=headers,
    )
    assert r.status_code == 200
