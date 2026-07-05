from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root():
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_login_wrong_credentials():
    res = client.post("/api/auth/login", json={
        "identifier": "wrong@test.com",
        "password": "wrongpass",
        "deviceId": "test-device"
    })

    assert res.status_code in [401, 429]


def test_protected_profile_without_token():
    res = client.get("/api/users/profile")
    assert res.status_code in [401, 403]


def test_store_without_token():
    res = client.get("/api/store/courses")
    assert res.status_code in [401, 403]


def test_notifications_without_token():
    res = client.get("/api/notifications")
    assert res.status_code in [401, 403]


def test_progress_without_token():
    res = client.get("/api/my-progress")    