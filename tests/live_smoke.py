"""Opt-in real-provider check: python -m tests.live_smoke (uses free-model quota).

Only synthetic PDF text is sent. No existing workspace is read or changed.
"""
import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
if os.getenv("LLM_FREE_ONLY") != "true":
    raise SystemExit("Enable LLM_FREE_ONLY=true before this smoke check.")
directory = tempfile.mkdtemp(prefix="researchos-live-")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(directory) / "test.db")
os.environ["DATA_DIR"] = directory
from backend.db import Base, engine, Session, Project, Paper, Chunk, Job
from backend.research import WORKFLOWS, chunk_pdf
from tests.pdf_fixture import sample_pdf

Base.metadata.create_all(engine)
with Session() as db:
    from backend.db import User
    user = User(name="Smoke test", email="smoke@example.org", password="unused")
    db.add(user); db.flush()
    project = Project(user_id=user.id, title="Synthetic live check", question="What limitations affect retrieval augmented generation in this supplied study?")
    db.add(project); db.flush()
    path = Path(directory) / "fixture.pdf"
    path.write_bytes(sample_pdf())
    paper = Paper(project_id=project.id, title="Synthetic study", selected=True, source="Upload", status="indexed", file=str(path))
    db.add(paper); db.flush()
    for chunk in chunk_pdf(sample_pdf()): db.add(Chunk(paper_id=paper.id, **chunk))
    job = Job(project_id=project.id, kind="research", status="running")
    db.add(job); db.commit()
    state = {"project_id": project.id, "job_id": job.id, "kind": "research"}
try:
    WORKFLOWS["research"].invoke(state)
    with Session() as db:
        result = db.get(Project, state["project_id"])
        claims = [c for paper in result.analysis["papers"] for c in paper["claims"]]
        assert claims and "References" in result.report
        assert all(c["sources"] for c in claims)
        print(f"Live free-model PDF workflow passed: {len(claims)} cited findings; report generated.")
except ValueError as error:
    print("Live check incomplete:", str(error))
    raise SystemExit(1)
finally:
    engine.dispose()
