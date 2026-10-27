import os
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
from fastapi.testclient import TestClient
from webapp.main import app

client = TestClient(app)

def test_health_endpoint_does_not_require_database():
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "personnel-api"}

def test_reference_creation_rejects_blank_name_before_database():
    response = client.post('/api/reference/employee-types', json={"name": "   "})
    assert response.status_code == 422

def test_report_rejects_empty_filters_before_database():
    response = client.post('/api/reports/employees', json={
        "department_ids": [], "room_ids": [1],
        "period_start": "2026-09-01T00:00:00Z", "period_end": "2026-10-01T00:00:00Z"
    })
    assert response.status_code == 422
