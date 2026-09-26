"""Account transitions must preserve ownership of saved research."""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db import Base, Message
from backend.main import app, db_session, requests


def test_guest_research_survives_claim_logout_and_login():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)

    def test_session():
        with sessions() as db:
            yield db

    app.dependency_overrides[db_session] = test_session
    requests.clear()
    try:
        client = TestClient(app)
        try:
            assert client.post("/api/auth/guest").status_code == 200
            created = client.post(
                "/api/projects",
                json={"title": "Saved question", "question": "How do neural networks classify images?"},
            )
            assert created.status_code == 201
            project_id = created.json()["id"]
            with sessions() as db:
                db.add(Message(project_id=project_id, role="user", content="Does this evidence answer my question?"))
                db.commit()

            claim = client.post(
                "/api/auth/claim",
                json={"name": "Ada", "email": "ada@example.com", "password": "good-password"},
            )
            assert claim.status_code == 200
            assert [p["id"] for p in client.get("/api/projects/library").json()] == [project_id]
            assert client.post("/api/auth/logout").status_code == 200
            assert client.get(f"/api/projects/{project_id}").status_code == 401
            login = client.post(
                "/api/auth/login",
                json={"email": "ada@example.com", "password": "good-password"},
            )
            assert login.status_code == 200
            assert client.get(f"/api/projects/{project_id}").status_code == 200
            assert client.get(f"/api/projects/{project_id}/messages").json()[0]["content"] == "Does this evidence answer my question?"

            assert client.post("/api/auth/logout").status_code == 200
            assert client.post("/api/auth/guest").status_code == 200
            second = client.post(
                "/api/projects",
                json={"title": "Another question", "question": "What limits the accuracy of neural networks?"},
            ).json()["id"]
            assert client.post(
                "/api/auth/login",
                json={"email": "ada@example.com", "password": "good-password"},
            ).status_code == 200
            assert {p["id"] for p in client.get("/api/projects/library").json()} == {project_id, second}
            assert client.get(f"/api/projects/{second}").status_code == 200
        finally:
            client.close()
    finally:
        app.dependency_overrides.clear()
        requests.clear()
        engine.dispose()
