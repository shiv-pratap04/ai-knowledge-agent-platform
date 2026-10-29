import pytest
from fastapi.testclient import TestClient

from app.core.security import OrganizationContext
from app.main import app
from app.core import security


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_create_and_list_tickets(monkeypatch):
    from app.services.ticket_service import create_ticket, list_tickets, get_ticket

    called = {}

    class FakeCursor:
        def __init__(self):
            self.rows = []
            self.params = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params=None):
            self.params.append(params)
            if "INSERT INTO tickets" in query:
                self.rows = [("ticket-uuid", "TKT-1001", "VPN outage", "Not working", "NETWORK", "HIGH", "OPEN", "2024-01-01T00:00:00Z", "2024-01-01T00:00:00Z")]
            elif "SELECT" in query and "FROM tickets" in query:
                self.rows = [("ticket-uuid", "TKT-1001", "VPN outage", "Not working", "NETWORK", "HIGH", "OPEN", "2024-01-01T00:00:00Z", "2024-01-01T00:00:00Z")]

        def fetchone(self):
            if not self.rows:
                return None
            return self.rows.pop(0)

        def fetchall(self):
            rows = list(self.rows)
            self.rows = []
            return rows

    class FakeConnection:
        def __init__(self):
            self.cursor_obj = FakeCursor()
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def cursor(self):
            return self.cursor_obj
        def close(self):
            pass

    monkeypatch.setattr("app.services.ticket_service.get_db_connection", lambda: FakeConnection())

    ticket = create_ticket("org-1", "user-1", "VPN outage", "The VPN is failing for the entire team.", "NETWORK", "HIGH")
    assert ticket["ticket_id"] == "TKT-1001"
    assert ticket["status"] == "OPEN"

    rows = list_tickets("org-1")
    assert len(rows) == 1
    assert rows[0]["ticket_id"] == "TKT-1001"

    selected = get_ticket("TKT-1001", "org-1")
    assert selected["category"] == "NETWORK"


def test_ticket_service_rejects_cross_org_lookup(monkeypatch):
    from app.services.ticket_service import get_ticket

    class FakeConnection:
        def cursor(self):
            return self
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def execute(self, query, params=None):
            pass
        def fetchone(self):
            return None
        def fetchall(self):
            return []
        def close(self):
            pass

    monkeypatch.setattr("app.services.ticket_service.get_db_connection", lambda: FakeConnection())

    with pytest.raises(ValueError, match="not found"):
        get_ticket("TKT-1001", "org-other")


def test_ticket_agent_tool_calls_service(monkeypatch):
    from app.services.langgraph_agent import create_support_ticket_tool

    captured = {}

    def fake_create_ticket(*, organization_id, user_id, title, description, category, priority, **kwargs):
        captured["context"] = (organization_id, user_id)
        return {
            "ticket_id": "TKT-1002",
            "title": title,
            "description": description,
            "category": category,
            "priority": priority,
            "status": "OPEN",
        }

    monkeypatch.setattr("app.services.langgraph_agent.create_ticket", fake_create_ticket)

    result = create_support_ticket_tool(
        title="VPN issues",
        description="Unable to connect to VPN",
        category="NETWORK",
        priority="HIGH",
        org_id="org-1",
        user_id="user-1",
    )

    assert "TKT-1002" in result
    assert captured["context"] == ("org-1", "user-1")


def test_ticket_api_requires_org_scope(monkeypatch):
    from app.api import tickets

    test_client = TestClient(app)
    app.dependency_overrides[security.get_current_org] = lambda: OrganizationContext(org_id="org-1", role="member", user_id="user-1")

    def fake_create_ticket(*, organization_id, user_id, title, description, category, priority, **kwargs):
        assert organization_id == "org-1"
        assert user_id == "user-1"
        return {
            "ticket_id": "TKT-2001",
            "organization_id": organization_id,
            "created_by": user_id,
            "title": title,
            "description": description,
            "category": category,
            "priority": priority,
            "status": "OPEN",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

    monkeypatch.setattr(tickets, "create_ticket", fake_create_ticket)

    response = test_client.post(
        "/tickets",
        json={"title": "VPN issue", "description": "Cannot connect to company VPN.", "category": "NETWORK", "priority": "HIGH"},
    )

    assert response.status_code == 200
    assert response.json()["ticket_id"] == "TKT-2001"

    app.dependency_overrides.clear()
