import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import main
from backend.db import Base, Project, Workspace, Paper, Chunk, Job, Message
from backend.history import cleanup_history


@pytest.fixture
def workspace():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)

    def database():
        with sessions() as db:
            yield db

    main.app.dependency_overrides[main.db_session] = database
    main.requests.clear()
    client = TestClient(main.app)
    client.post("/api/auth/guest")
    pid = client.post("/api/projects", json={"title": "A saved result", "question": "How do neural networks learn?"}).json()["id"]
    yield client, sessions, pid
    client.close()
    main.app.dependency_overrides.clear()
    main.requests.clear()
    engine.dispose()


def test_pdf_is_extracted_without_retaining_bytes(workspace, monkeypatch):
    client, sessions, pid = workspace
    monkeypatch.setattr(main, "chunk_pdf", lambda raw: [{"page": 1, "section": "Introduction", "text": "Temporary source text."}])
    response = client.post(f"/api/projects/{pid}/upload", files={"file": ("paper.pdf", b"%PDF-test", "application/pdf")})
    assert response.status_code == 201
    assert response.json()["has_pdf"] is False
    with sessions() as db:
        paper = db.scalar(select(Paper).where(Paper.project_id == pid))
        assert paper.file == ""
        assert db.scalar(select(Chunk).where(Chunk.paper_id == paper.id)).text == "Temporary source text."


def test_archive_keeps_text_and_rejects_continuation(workspace, tmp_path):
    client, sessions, pid = workspace
    legacy_pdf = tmp_path / "old-paper.pdf"
    legacy_pdf.write_bytes(b"%PDF-old")
    with sessions() as db:
        project = db.get(Project, pid)
        project.report = "## Answer\nThe saved result."
        project.analysis = {"evidence": [{"text": "Raw passage"}]}
        paper = Paper(project_id=pid, title="Paper", file=str(legacy_pdf))
        db.add(paper)
        db.flush()
        paper_id = paper.id
        db.add(Chunk(paper_id=paper.id, page=1, section="Intro", text="Raw passage", embedding=[0.1, 0.2]))
        db.add(Message(project_id=pid, role="assistant", content="A follow-up answer [1].", evidence=[{"title": "Paper", "text": "Raw passage", "url": "https://example.org/paper"}]))
        db.add(Job(project_id=pid, kind="research", status="completed"))
        db.commit()
    response = client.post(f"/api/projects/{pid}/archive")
    assert response.status_code == 200
    assert response.json()["readonly"] is True
    assert response.json()["report"] == "## Answer\nThe saved result."
    assert not legacy_pdf.exists()
    with sessions() as db:
        assert db.get(Workspace, pid) is None
        for model in (Paper, Chunk, Job):
            assert db.scalar(select(model)) is None
        project = db.get(Project, pid)
        assert project.analysis == {} and project.plan == {}
        message = db.scalar(select(Message))
        assert "A follow-up answer" in message.content and "https://example.org/paper" in message.content
        assert "Raw passage" not in message.content and message.evidence == []
    for path, body in (("chat", {"content": "Continue this research"}), ("run/research", {})):
        assert client.post(f"/api/projects/{pid}/{path}", json=body).status_code == 409
    assert client.patch(f"/api/projects/{pid}/plan", json={"queries": ["more research"]}).status_code == 409
    assert client.patch(f"/api/projects/{pid}/papers/{paper_id}", json={"selected": True}).status_code == 409
    assert client.post(f"/api/projects/{pid}/upload", files={"file": ("paper.pdf", b"%PDF-test")}).status_code == 409


def test_closing_during_research_preserves_result_then_cleans_up(workspace):
    client, sessions, pid = workspace
    with sessions() as db:
        db.add(Job(project_id=pid, kind="research", status="running"))
        db.add(Paper(project_id=pid, title="Temporary paper"))
        db.commit()
    assert client.post(f"/api/projects/{pid}/archive").json()["readonly"] is True
    with sessions() as db:
        assert db.get(Workspace, pid).closed is True
        assert db.scalar(select(Paper)) is not None
        db.scalar(select(Job)).status = "completed"
        db.get(Project, pid).report = "A result that finished after leaving."
        db.commit()
        cleanup_history(db)
        assert db.get(Project, pid).status == "archived"
        assert db.get(Project, pid).report == "A result that finished after leaving."
        assert db.scalar(select(Paper)) is None


@pytest.mark.parametrize("legacy", [False, True])
def test_expired_or_legacy_workspace_is_pruned(workspace, legacy):
    _, sessions, pid = workspace
    with sessions() as db:
        if legacy:
            db.delete(db.get(Workspace, pid))
        else:
            db.get(Workspace, pid).expires = time.time() - 1
        db.get(Project, pid).analysis = {"overview": [{"text": "A partial answer."}]}
        db.commit()
        cleanup_history(db)
        assert db.get(Workspace, pid) is None
        assert "A partial answer." in db.get(Project, pid).report
