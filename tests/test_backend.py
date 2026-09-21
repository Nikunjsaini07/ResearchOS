import time
from fastapi.testclient import TestClient
from sqlalchemy import select
from backend.main import app
from backend.db import Session, Project, Paper, Chunk, Job
from backend.research import (
    chunk_pdf,
    validate_claims,
    download_pdf,
    retrieve,
    WORKFLOWS,
)
from tests.pdf_fixture import sample_pdf
import pytest


def register(client, email="researcher@example.org"):
    result = client.post(
        "/api/auth/register",
        json={
            "name": "Alex Researcher",
            "email": email,
            "password": "secure-test-pass",
        },
    )
    assert result.status_code == 200
    assert "password" not in result.json()
    return result.json()


def project(client):
    register(client)
    result = client.post(
        "/api/projects",
        json={
            "title": "Grounded language models",
            "question": "What limitations affect retrieval augmented generation?",
        },
    )
    assert result.status_code == 201
    return result.json()["id"]


def upload(client, pid):
    result = client.post(
        f"/api/projects/{pid}/upload",
        files={"file": ("Research fixture.pdf", sample_pdf(), "application/pdf")},
    )
    assert result.status_code == 201, result.text
    return result.json()


def test_auth_session_and_logout(client):
    assert client.get("/api/projects").status_code == 401
    register(client)
    assert client.get("/api/auth/me").json()["name"] == "Alex Researcher"
    assert (
        "HttpOnly"
        in client.cookies.jar._cookies["testserver.local"]["/"][
            "researchos_session"
        ]._rest
    )
    client.post("/api/auth/logout")
    assert client.get("/api/projects").status_code == 401
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "researcher@example.org", "password": "wrong-password"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "researcher@example.org", "password": "secure-test-pass"},
        ).status_code
        == 200
    )


def test_cross_user_isolation(client):
    pid = project(client)
    paper = upload(client, pid)
    with TestClient(app) as other:
        register(other, "other@example.org")
        for suffix in (
            "",
            "/papers",
            "/evidence",
            "/messages",
            "/jobs",
            f'/papers/{paper["id"]}/pdf',
        ):
            assert other.get("/api/projects/" + pid + suffix).status_code == 404
        assert other.delete("/api/projects/" + pid).status_code == 404


def test_upload_pdf_evidence_and_retrieval(client):
    pid = project(client)
    paper = upload(client, pid)
    assert paper["status"] == "indexed"
    assert "file" not in paper
    evidence = client.get(f"/api/projects/{pid}/evidence").json()
    assert len(evidence) == 3
    assert {e["section"] for e in evidence} == {"Methods", "Results", "Limitations"}
    assert all(e["page"] == 1 for e in evidence)
    result = client.get(f"/api/projects/{pid}/evidence?q=English").json()
    assert result[0]["section"] == "Limitations"
    assert client.get(
        f'/api/projects/{pid}/papers/{paper["id"]}/pdf'
    ).content.startswith(b"%PDF")


def test_invalid_pdf_rejected(client):
    pid = project(client)
    result = client.post(
        f"/api/projects/{pid}/upload",
        files={"file": ("bad.pdf", b"not a pdf", "application/pdf")},
    )
    assert result.status_code == 422
    assert client.get(f"/api/projects/{pid}/papers").json() == []


def test_unsupported_question_abstains(client):
    pid = project(client)
    upload(client, pid)
    result = client.post(
        f"/api/projects/{pid}/chat",
        json={"content": "What quantum entanglement experiment was conducted?"},
    )
    assert result.status_code == 200
    assert "could not find supporting evidence" in result.json()["content"]
    assert result.json()["evidence"] == []


def test_no_key_returns_evidence_without_fabrication(client):
    pid = project(client)
    upload(client, pid)
    result = client.post(
        f"/api/projects/{pid}/chat",
        json={"content": "What English language limitations are reported?"},
    )
    assert "not configured" in result.json()["content"]
    assert len(result.json()["evidence"]) > 0
    assert len(client.get(f"/api/projects/{pid}/messages").json()) == 2
    assert client.post(f"/api/projects/{pid}/run/analyze").status_code == 409


def test_claims_require_exact_quotes():
    evidence = [
        {"id": "abc", "text": "The study only evaluated English language documents."}
    ]
    good = {
        "text": "English-only evaluation",
        "sources": [
            {"id": "abc", "quote": "only evaluated English language documents"}
        ],
    }
    bad = {
        "text": "Invented accuracy",
        "sources": [{"id": "abc", "quote": "The model achieved 99 percent accuracy."}],
    }
    forged = {
        "text": "Wrong source",
        "sources": [
            {"id": "fake", "quote": "only evaluated English language documents"}
        ],
    }
    result = validate_claims([good, bad, forged], evidence)
    assert len(result) == 1
    assert result[0]["status"] == "needs_review"


def test_download_rejects_private_and_untrusted_urls():
    for url in [
        "http://127.0.0.1/admin",
        "https://evil.example/paper.pdf",
        "https://arxiv.org.evil.example/pdf/1",
        "https://arxiv.org/admin",
    ]:
        with pytest.raises(ValueError):
            download_pdf(url)


def test_plan_job_completes(client):
    pid = project(client)
    result = client.post(f"/api/projects/{pid}/run/plan")
    assert result.status_code == 202
    for _ in range(40):
        job = client.get(f"/api/projects/{pid}/jobs").json()[0]
        if job["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)
    assert job["status"] == "completed", job
    assert client.get(f"/api/projects/{pid}").json()["plan"]["queries"]


def test_analysis_report_and_corpus_invalidation(client, monkeypatch):
    pid = project(client)
    paper = upload(client, pid)

    def fake_llm(system, content):
        import json

        data = json.loads(content)
        evidence = data["evidence"]
        e = next(e for e in evidence if e["section"] == "Limitations")
        return {
            "claims": [
                {
                    "text": "The study evaluates English documents only.",
                    "dimension": "Limitations",
                    "sources": [{"id": e["id"], "quote": e["text"]}],
                }
            ]
        }

    monkeypatch.setattr("backend.research.llm", fake_llm)
    with Session() as db:
        job = Job(project_id=pid, kind="analyze", status="running")
        db.add(job)
        db.commit()
        jid = job.id
    WORKFLOWS["analyze"].invoke({"project_id": pid, "job_id": jid, "kind": "analyze"})
    WORKFLOWS["report"].invoke({"project_id": pid, "job_id": jid, "kind": "report"})
    report = client.get(f"/api/projects/{pid}/export")
    assert report.status_code == 200
    assert "[1]" in report.text and "p. 1" in report.text
    assert "## Potential research gaps" in report.text
    with Session() as db:
        running = db.get(Job, jid)
        running.status = "completed"
        db.commit()
    analysis = client.get(f"/api/projects/{pid}").json()["analysis"]
    claim = analysis["papers"][0]["claims"][0]
    reviewed = client.patch(
        f"/api/projects/{pid}/review",
        json={
            "text": claim["text"],
            "source_ids": [s["id"] for s in claim["sources"]],
            "status": "unsupported",
        },
    )
    assert reviewed.status_code == 200
    assert client.get(f"/api/projects/{pid}/export").status_code == 409
    WORKFLOWS["report"].invoke({"project_id": pid, "job_id": jid, "kind": "report"})
    updated = client.get(f"/api/projects/{pid}/export").text
    assert "The study evaluates English documents only." not in updated

    with Session() as db:
        j = db.get(Job, jid)
        j.status = "completed"
        db.commit()
    assert (
        client.patch(
            f'/api/projects/{pid}/papers/{paper["id"]}', json={"selected": False}
        ).status_code
        == 200
    )
    assert client.get(f"/api/projects/{pid}").json()["analysis"] == {}
    assert client.get(f"/api/projects/{pid}/export").status_code == 409
    assert client.get(f"/api/projects/{pid}/evidence").json() == []


def test_csrf_origin_rejected(client):
    assert (
        client.post(
            "/api/auth/register", headers={"Origin": "https://evil.example"}, json={}
        ).status_code
        == 403
    )


def test_delete_removes_corpus(client):
    pid = project(client)
    upload(client, pid)
    assert client.delete(f"/api/projects/{pid}").status_code == 200
    with Session() as db:
        assert not list(db.scalars(select(Paper).where(Paper.project_id == pid)))
        assert not list(db.scalars(select(Chunk)))
    assert client.get(f"/api/projects/{pid}").status_code == 404


def test_guest_can_save_workspace_without_losing_projects(client):
    assert client.post("/api/auth/guest").status_code == 200
    pid = client.post(
        "/api/projects",
        json={
            "title": "Guest research",
            "question": "What methods support retrieval augmented generation?",
        },
    ).json()["id"]
    claimed = client.post(
        "/api/auth/claim",
        json={
            "name": "Saved Researcher",
            "email": "saved@example.org",
            "password": "safe-password-123",
        },
    )
    assert claimed.status_code == 200
    client.post("/api/auth/logout")
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "saved@example.org", "password": "safe-password-123"},
        ).status_code
        == 200
    )
    assert client.get(f"/api/projects/{pid}").status_code == 200


def test_full_workflow_uses_uploaded_corpus_and_honest_excerpt_mode(client):
    pid = project(client)
    upload(client, pid)
    response = client.post(f"/api/projects/{pid}/run/research")
    assert response.status_code == 202
    for _ in range(80):
        job = client.get(f"/api/projects/{pid}/jobs").json()[0]
        if job["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)
    assert job["status"] == "completed", job
    assert job["progress"] == 100
    assert {e["stage"] for e in job["events"]} == {
        "plan",
        "discover",
        "index",
        "analyze",
        "report",
    }
    data = client.get(f"/api/projects/{pid}").json()
    assert data["analysis"]["mode"] == "extractive"
    assert "Source excerpts only" in data["report"]
    assert data["analysis"]["gaps"] == []


def test_uploaded_corpus_skips_ai_search_planning(client, monkeypatch):
    pid = project(client)
    upload(client, pid)
    monkeypatch.setenv("LLM_API_KEY", "configured-but-not-needed")
    monkeypatch.setattr("backend.research.llm", lambda *args: pytest.fail("Uploads should not call AI search planning"))
    with Session() as db:
        job = Job(project_id=pid, kind="plan", status="running")
        db.add(job)
        db.commit()
        jid = job.id
    WORKFLOWS["plan"].invoke({"project_id": pid, "job_id": jid, "kind": "plan"})
    data = client.get(f"/api/projects/{pid}").json()
    assert data["plan"]["mode"] == "upload"
    assert data["plan"]["queries"] == []


def test_refine_preserves_queries_and_selection(client):
    pid = project(client)
    first = upload(client, pid)
    second = upload(client, pid)
    assert client.patch(f"/api/projects/{pid}/plan", json={"queries": ["custom retrieval query"]}).status_code == 200
    client.patch(f'/api/projects/{pid}/papers/{second["id"]}', json={"selected": False})
    assert client.post(f"/api/projects/{pid}/run/refine").status_code == 202
    for _ in range(80):
        job = client.get(f"/api/projects/{pid}/jobs").json()[0]
        if job["status"] in ("completed", "failed"): break
        time.sleep(0.1)
    assert job["status"] == "completed", job
    data = client.get(f"/api/projects/{pid}").json()
    assert data["plan"]["queries"] == ["custom retrieval query"]
    assert [p["paper_id"] for p in data["analysis"]["papers"]] == [first["id"]]
    client.patch(f'/api/projects/{pid}/papers/{first["id"]}', json={"selected": False})
    assert client.post(f"/api/projects/{pid}/run/refine").status_code == 422
