"""HTTP API and background job worker. Start with create_project, run, and worker."""

import hashlib
import hmac
import logging
import os
import re
import secrets
import threading
import time
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from pathlib import Path
from collections import defaultdict, deque
from fastapi import FastAPI, HTTPException, Request, Response, Depends, UploadFile, Form
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select, delete, func, update, text
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.exc import IntegrityError
from backend.db import (
    Base,
    engine,
    Session,
    User,
    AuthSession,
    Project,
    Paper,
    Chunk,
    Job,
    Message,
    Workspace,
    DATA,
)
from backend.research import (
    WORKFLOWS,
    configured,
    free_only,
    embeddings_enabled,
    retrieve,
    llm,
    validate_claims,
    chunk_pdf,
)
import json
from backend.storage import read_pdf, delete_pdf
from backend.history import WORKSPACE_TTL, close_project, cleanup_history
from backend.ideator import (
    generate_thesis_proposals,
    refine_proposal_chat,
    generate_export_markdown,
    prepare_paper_context,
    SAMPLE_PROPOSALS,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("researchos")
stop = threading.Event()


def worker():
    next_cleanup = 0
    while not stop.wait(0.7):
        try:
            with Session() as db:
                if time.time() >= next_cleanup:
                    cleanup_history(db)
                    next_cleanup = time.time() + 60
                job = db.scalar(
                    select(Job).where(Job.status == "queued").order_by(Job.created)
                )
                if not job:
                    continue
                claimed = db.execute(
                    update(Job)
                    .where(Job.id == job.id, Job.status == "queued")
                    .values(status="running")
                ).rowcount
                db.commit()
                if not claimed:
                    continue
                jid, pid, kind = job.id, job.project_id, job.kind
            try:
                WORKFLOWS[kind].invoke({"project_id": pid, "job_id": jid, "kind": kind})
                with Session() as db:
                    job = db.get(Job, jid)
                    job.status = "completed"
                    job.progress = 100
                    db.commit()
            except Exception as exc:
                log.exception("Research job failed job_id=%s kind=%s", jid, kind)
                with Session() as db:
                    job = db.get(Job, jid)
                    if job:
                        job.status = "failed"
                        job.error = (
                            str(exc)[:500]
                            if isinstance(exc, ValueError)
                            else "The research service could not complete this step. Check provider settings and retry."
                        )
                        db.commit()
            with Session() as db:
                cleanup_history(db)
        except Exception:
            log.exception("Worker polling failed")


@asynccontextmanager
async def lifespan(app):
    if engine.dialect.name == "postgresql":
        with engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    if engine.dialect.name == "postgresql":
        # API authorization stays in FastAPI; block direct access through Supabase's Data API.
        with engine.begin() as connection:
            for table in Base.metadata.sorted_tables:
                connection.execute(text(f'ALTER TABLE "{table.name}" ENABLE ROW LEVEL SECURITY'))
    with Session() as db:
        db.execute(delete(AuthSession).where(AuthSession.expires < time.time()))
        for j in db.scalars(select(Job).where(Job.status == "running")):
            j.status = "failed"
            j.error = "The server restarted during this run. Retry the step."
        db.commit()
        cleanup_history(db)
    stop.clear()
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    yield
    stop.set()
    thread.join(timeout=2)


app = FastAPI(title="ResearchOS API", version="0.1.0", lifespan=lifespan)
origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)
requests = defaultdict(deque)


@app.middleware("http")
async def guard(request: Request, call_next):
    if request.method in ("POST", "PATCH", "DELETE", "PUT"):
        origin = request.headers.get("origin")
        if origin and origin not in origins:
            return PlainTextResponse("Origin not allowed", 403)
        if request.headers.get("sec-fetch-site") == "cross-site":
            return PlainTextResponse("Cross-site request rejected", 403)
        if int(request.headers.get("content-length", "0")) > 26 * 1024 * 1024:
            return PlainTextResponse("Upload exceeds 25 MB", 413)
    if request.url.path.startswith("/api"):
        key = (
            request.client.host if request.client else "local",
            "auth" if "/auth/" in request.url.path else "api",
        )
        current = time.time()
        queue = requests[key]
        while queue and queue[0] < current - 60:
            queue.popleft()
        if len(queue) >= (20 if key[1] == "auth" else 240):
            return PlainTextResponse("Too many requests. Try again in a minute.", 429)
        queue.append(current)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "DENY"
    return response


def db_session():
    with Session() as db:
        yield db


def current_user(request: Request, db=Depends(db_session)):
    user = db.get(User, "default_user")
    if not user:
        user = User(
            id="default_user",
            name="Researcher",
            email="researcher@local",
            password="none",
        )
        db.add(user)
        try:
            db.commit()
        except Exception:
            db.rollback()
            user = db.get(User, "default_user")
    return user


def project_for(db, pid, user=None):
    p = db.get(Project, pid)
    if not p:
        p = Project(
            id=pid,
            user_id="default_user",
            title="Research Workspace",
            question="Thesis & Project Ideator",
            status="ready",
        )
        db.add(p)
        db.commit()
    return p


def active_project_for(db, pid, user=None):
    return project_for(db, pid, user)


def idle(db, pid):
    if db.scalar(
        select(Job).where(Job.project_id == pid, Job.status.in_(["queued", "running"]))
    ):
        raise HTTPException(409, "A research step is running. Wait until it finishes.")


def public(obj, exclude=()):
    return {
        c.name: getattr(obj, c.name)
        for c in obj.__table__.columns
        if c.name not in exclude
    }


def project_json(db, p):
    data = public(p, ("user_id",))
    workspace = db.get(Workspace, p.id)
    papers = list(db.scalars(select(Paper).where(Paper.project_id == p.id)))
    data.update(
        readonly=not workspace or workspace.closed or workspace.expires <= time.time(),
        paper_count=len(papers),
        indexed_count=sum(x.status == "indexed" for x in papers),
        finding_count=sum(len(x["claims"]) for x in p.analysis.get("papers", [])),
    )
    return data


class Credentials(BaseModel):
    name: str = Field(default="Researcher", min_length=1, max_length=100)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=256)


class NewProject(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    question: str = Field(min_length=10, max_length=3000)


class Selection(BaseModel):
    selected: bool


class Question(BaseModel):
    content: str = Field(min_length=3, max_length=3000)


class PlanEdit(BaseModel):
    queries: list[str] = Field(min_length=1, max_length=3)


class Review(BaseModel):
    text: str = Field(min_length=1, max_length=3000)
    source_ids: list[str] = Field(min_length=1, max_length=30)
    status: str


class IdeateRequest(BaseModel):
    sample: str | None = None
    focus: str | None = None


class RefineRequest(BaseModel):
    proposal_id: str
    message: str = Field(min_length=1, max_length=3000)


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    return (
        salt
        + ":"
        + hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    )


def login_cookie(db, user, response):
    lifetime = 30 * 86400
    token = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            id=hashlib.sha256(token.encode()).hexdigest(),
            user_id=user.id,
            expires=time.time() + lifetime,
        )
    )
    db.commit()
    set_session_cookie(response, token, lifetime)
    return public(user, ("password",))


def set_session_cookie(response, token, lifetime=30 * 86400):
    response.set_cookie(
        "researchos_session",
        token,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
        max_age=lifetime,
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/auth/guest")
def guest(request: Request, response: Response, db=Depends(db_session)):
    token = request.cookies.get("researchos_session", "")
    session = (
        db.get(AuthSession, hashlib.sha256(token.encode()).hexdigest())
        if token
        else None
    )
    if session and session.expires > time.time():
        existing = db.get(User, session.user_id)
        if existing:
            return public(existing, ("password",))
    user = User(
        name="Curious mind",
        email=secrets.token_hex(16) + "@guest.local",
        password=password_hash(secrets.token_urlsafe(32)),
    )
    db.add(user)
    db.commit()
    return login_cookie(db, user, response)


@app.post("/api/auth/register")
def register(body: Credentials, response: Response, db=Depends(db_session)):
    email = body.email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(422, "Enter a valid email address.")
    u = User(
        name=body.name.strip() or "Researcher",
        email=email,
        password=password_hash(body.password),
    )
    db.add(u)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "An account already exists with this email.")
    return login_cookie(db, u, response)


@app.post("/api/auth/claim")
def claim_account(
    body: Credentials, user=Depends(current_user), db=Depends(db_session)
):
    if not user.email.endswith("@guest.local"):
        raise HTTPException(409, "This workspace already has an account.")
    email = body.email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or email.endswith(
        "@guest.local"
    ):
        raise HTTPException(422, "Enter a valid email address.")
    user.email = email
    user.name = body.name.strip() or "Researcher"
    user.password = password_hash(body.password)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This email already has an account. Sign in instead.")
    return public(user, ("password",))


@app.post("/api/auth/login")
def login(body: Credentials, request: Request, response: Response, db=Depends(db_session)):
    u = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if not u or not hmac.compare_digest(
        u.password, password_hash(body.password, u.password.split(":")[0])
    ):
        raise HTTPException(401, "Email or password is incorrect.")
    token = request.cookies.get("researchos_session", "")
    session = db.get(AuthSession, hashlib.sha256(token.encode()).hexdigest()) if token else None
    guest_user = db.get(User, session.user_id) if session and session.expires > time.time() else None
    if guest_user and guest_user.id != u.id and guest_user.email.endswith("@guest.local"):
        db.execute(update(Project).where(Project.user_id == guest_user.id).values(user_id=u.id))
        db.execute(delete(AuthSession).where(AuthSession.user_id == guest_user.id))
        db.delete(guest_user)
        db.commit()
    return login_cookie(db, u, response)


@app.post("/api/auth/logout")
def logout(request: Request, response: Response, db=Depends(db_session)):
    token = request.cookies.get("researchos_session", "")
    db.execute(
        delete(AuthSession).where(
            AuthSession.id == hashlib.sha256(token.encode()).hexdigest()
        )
    )
    db.commit()
    response.delete_cookie("researchos_session")
    return {"ok": True}


@app.get("/api/auth/me")
def me(request: Request, response: Response, user=Depends(current_user), db=Depends(db_session)):
    token = request.cookies["researchos_session"]
    session = db.get(AuthSession, hashlib.sha256(token.encode()).hexdigest())
    session.expires = time.time() + 30 * 86400
    db.commit()
    set_session_cookie(response, token)
    return public(user, ("password",))


@app.get("/api/settings")
def settings(user=Depends(current_user)):
    return {
        "ai_configured": configured(),
        "free_only": free_only(),
        "model": os.getenv("LLM_MODEL", "gpt-4.1-mini"),
        "embeddings_configured": embeddings_enabled() and bool(os.getenv("EMBEDDING_API_KEY") or configured()),
        "database": "PostgreSQL" if "postgres" in str(engine.url) else "SQLite",
        "search_source": "arXiv + OpenAlex",
        "max_pdf_mb": 25,
    }


@app.get("/api/projects")
def projects(user=Depends(current_user), db=Depends(db_session)):
    return [
        project_json(db, p)
        for p in db.scalars(
            select(Project)
            .where(Project.user_id == user.id)
            .order_by(Project.created.desc())
        )
    ]


@app.get("/api/projects/library")
def project_library(user=Depends(current_user), db=Depends(db_session)):
    return [
        {
            "id": pid,
            "title": title,
            "created": created,
        }
        for pid, title, created in db.execute(
            select(Project.id, Project.title, Project.created)
            .where(Project.user_id == user.id)
            .order_by(Project.created.desc())
        ).all()
    ]


@app.get("/api/projects/current")
def get_current_project(user=Depends(current_user), db=Depends(db_session)):
    p = db.scalar(
        select(Project)
        .order_by(Project.created.desc())
        .limit(1)
    )
    if not p:
        p = Project(
            id=uid(),
            user_id="default_user",
            title="Research Workspace",
            question="Thesis & Project Ideator",
            status="ready",
        )
        db.add(p)
        db.commit()
    return project_json(db, p)


@app.post("/api/projects/reset")
def reset_project(user=Depends(current_user), db=Depends(db_session)):
    p = Project(
        id=uid(),
        user_id="default_user",
        title="Research Workspace",
        question="Thesis & Project Ideator",
        status="ready",
    )
    db.add(p)
    db.commit()
    return project_json(db, p)


@app.post("/api/projects", status_code=201)
def create_project(
    body: NewProject, user=Depends(current_user), db=Depends(db_session)
):
    if len(body.title.strip()) < 3 or len(body.question.strip()) < 10:
        raise HTTPException(422, "Enter a title and a complete research question.")
    p = Project(
        user_id=user.id, title=body.title.strip(), question=body.question.strip()
    )
    db.add(p)
    db.flush()
    db.add(Workspace(project_id=p.id, expires=time.time() + WORKSPACE_TTL))
    db.commit()
    return project_json(db, p)


@app.get("/api/projects/{pid}")
def get_project(pid: str, user=Depends(current_user), db=Depends(db_session)):
    return project_json(db, project_for(db, pid, user))


@app.post("/api/projects/{pid}/archive")
def archive(pid: str, user=Depends(current_user), db=Depends(db_session)):
    p = project_for(db, pid, user)
    close_project(db, p)
    return project_json(db, p)


@app.delete("/api/projects/{pid}")
def delete_project(pid: str, user=Depends(current_user), db=Depends(db_session)):
    p = project_for(db, pid, user)
    idle(db, pid)
    papers = list(db.scalars(select(Paper).where(Paper.project_id == pid)))
    for paper in papers:
        db.execute(delete(Chunk).where(Chunk.paper_id == paper.id))
        if paper.file:
            delete_pdf(paper.file)
    for model in (Message, Job, Paper, Workspace):
        db.execute(delete(model).where(model.project_id == pid))
    db.delete(p)
    db.commit()
    return {"ok": True}


@app.patch("/api/projects/{pid}/plan")
def edit_plan(
    pid: str, body: PlanEdit, user=Depends(current_user), db=Depends(db_session)
):
    p = active_project_for(db, pid, user)
    idle(db, pid)
    if any(not q.strip() or len(q) > 300 for q in body.queries):
        raise HTTPException(422, "Queries must contain 1–300 characters.")
    p.plan = {**p.plan, "queries": [q.strip() for q in body.queries],
              "retry_queries": list(dict.fromkeys(" ".join(q.split()[:2]) for q in body.queries)), "mode": "edited", "concepts": [], "scope": p.question}
    db.commit()
    return p.plan


@app.post("/api/projects/{pid}/run/{kind}", status_code=202)
def run(pid: str, kind: str, user=Depends(current_user), db=Depends(db_session)):
    p = active_project_for(db, pid, user)
    idle(db, pid)
    if kind not in WORKFLOWS:
        raise HTTPException(404, "Unknown research step.")
    if kind == "analyze" and not configured():
        raise HTTPException(
            409,
            "Set LLM_API_KEY in .env and restart the backend to enable AI analysis.",
        )
    if kind in ("index", "analyze", "refine"):
        count = db.scalar(
            select(func.count())
            .select_from(Paper)
            .where(Paper.project_id == pid, Paper.selected == True)
        )
        if count > 20:
            raise HTTPException(422, "Select at most 20 papers per research run.")
        if count == 0:
            raise HTTPException(422, "Select at least one paper first.")
    job = Job(project_id=pid, kind=kind)
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A research step is already running.")
    return public(job)


@app.get("/api/projects/{pid}/jobs")
def jobs(pid: str, user=Depends(current_user), db=Depends(db_session)):
    project_for(db, pid, user)
    return [
        public(j)
        for j in db.scalars(
            select(Job)
            .where(Job.project_id == pid)
            .order_by(Job.created.desc())
            .limit(20)
        )
    ]


@app.get("/api/projects/{pid}/papers")
def papers(pid: str, user=Depends(current_user), db=Depends(db_session)):
    project_for(db, pid, user)
    return [
        {**public(p, ("file",)), "has_pdf": bool(p.file)}
        for p in db.scalars(
            select(Paper).where(Paper.project_id == pid).order_by(Paper.score.desc())
        )
    ]


@app.patch("/api/projects/{pid}/papers/{paper_id}")
def select_paper(
    pid: str,
    paper_id: str,
    body: Selection,
    user=Depends(current_user),
    db=Depends(db_session),
):
    project = active_project_for(db, pid, user)
    idle(db, pid)
    p = db.get(Paper, paper_id)
    if not p or p.project_id != pid:
        raise HTTPException(404, "Paper not found.")
    p.selected = body.selected
    # Derived artifacts must never outlive changes to the selected corpus.
    project.analysis = {}
    project.report = ""
    project.status = "discovered"
    db.commit()
    return {"ok": True}


@app.post("/api/projects/{pid}/upload", status_code=201)
async def upload(
    pid: str,
    file: UploadFile,
    focus: Optional[str] = Form(None),
    user=Depends(current_user),
    db=Depends(db_session),
):
    project = active_project_for(db, pid, user)
    idle(db, pid)
    raw = await file.read(25 * 1024 * 1024 + 1)
    if len(raw) > 25 * 1024 * 1024:
        raise HTTPException(413, "PDF must be smaller than 25 MB.")
    try:
        chunks = await __import__("asyncio").to_thread(chunk_pdf, raw)
    except Exception as exc:
        raise HTTPException(
            422, str(exc) if isinstance(exc, ValueError) else "Unable to read this PDF."
        )
    filename = Path(file.filename or "Uploaded paper.pdf").stem
    # Deselect previous papers so this upload is primary
    db.execute(update(Paper).where(Paper.project_id == pid).values(selected=False))
    p = Paper(
        project_id=pid,
        title=filename[:300],
        abstract=chunks[0]["text"][:1500],
        selected=True,
        source="Upload",
        status="indexed",
    )
    db.add(p)
    db.flush()
    for chunk in chunks:
        db.add(Chunk(paper_id=p.id, **chunk))
    chunk_dicts = [{"page": c["page"], "section": c["section"], "text": c["text"]} for c in chunks]
    context = prepare_paper_context(chunk_dicts)
    try:
        user_focus = (focus or "").strip() or project.question
        ideator_result = await __import__("asyncio").to_thread(
            generate_thesis_proposals, context, filename, user_focus
        )
        project.analysis = {**project.analysis, "ideator": ideator_result}
        flag_modified(project, "analysis")
        project.status = "ideated"
    except Exception as exc:
        log.warning("Could not auto-generate ideation on upload: %s", exc)
        project.analysis = {}
        project.status = "indexed"
    project.report = ""
    db.commit()
    return {**public(p, ("file",)), "has_pdf": False}


@app.post("/api/projects/{pid}/ideate")
async def ideate(
    pid: str,
    body: IdeateRequest = IdeateRequest(),
    user=Depends(current_user),
    db=Depends(db_session),
):
    project = active_project_for(db, pid, user)
    idle(db, pid)

    if body.sample and body.sample in SAMPLE_PROPOSALS:
        sample_data = SAMPLE_PROPOSALS[body.sample].copy()
        existing_paper = db.scalar(select(Paper).where(Paper.project_id == pid).limit(1))
        if not existing_paper:
            p = Paper(
                project_id=pid,
                title=sample_data["digest"]["title"],
                abstract=sample_data["digest"]["method_summary"],
                selected=True,
                source="Sample",
                status="indexed",
            )
            db.add(p)
            db.flush()
        project.analysis = {**project.analysis, "ideator": sample_data}
        flag_modified(project, "analysis")
        project.status = "ideated"
        db.commit()
        return sample_data

    chunks = list(
        db.scalars(
            select(Chunk)
            .join(Paper)
            .where(Paper.project_id == pid, Paper.selected == True)
            .order_by(Chunk.page)
        )
    )
    if not chunks:
        raise HTTPException(400, "Upload a research paper first or pick a sample paper.")

    chunk_dicts = [{"page": c.page, "section": c.section, "text": c.text} for c in chunks]
    context = prepare_paper_context(chunk_dicts)
    paper = db.scalar(
        select(Paper).where(Paper.project_id == pid, Paper.selected == True).limit(1)
    )
    paper_title = paper.title if paper else project.title

    ideator_result = await __import__("asyncio").to_thread(
        generate_thesis_proposals, context, paper_title, body.focus or project.question
    )
    project.analysis = {**project.analysis, "ideator": ideator_result}
    flag_modified(project, "analysis")
    project.status = "ideated"
    db.commit()
    return ideator_result


@app.post("/api/projects/{pid}/refine-proposal")
async def refine_proposal(
    pid: str,
    body: RefineRequest,
    user=Depends(current_user),
    db=Depends(db_session),
):
    project = active_project_for(db, pid, user)
    ideator_data = project.analysis.get("ideator")
    if not ideator_data or "proposals" not in ideator_data:
        raise HTTPException(
            400, "No proposals exist to refine. Generate proposals first."
        )

    target_prop = None
    prop_index = -1
    for i, p in enumerate(ideator_data["proposals"]):
        if p.get("id") == body.proposal_id:
            target_prop = p
            prop_index = i
            break
    if not target_prop:
        target_prop = ideator_data["proposals"][0]
        prop_index = 0

    history = [
        {"role": m.role, "content": m.content}
        for m in db.scalars(
            select(Message)
            .where(Message.project_id == pid)
            .order_by(Message.created)
            .limit(10)
        )
    ]

    result = await __import__("asyncio").to_thread(
        refine_proposal_chat,
        target_prop,
        ideator_data.get("digest", {}),
        history,
        body.message,
    )

    reply_text = result.get("reply", "Here is my advice on this project.")
    updated_prop = result.get("updated_proposal")

    if updated_prop and isinstance(updated_prop, dict):
        for k, v in updated_prop.items():
            if v:
                target_prop[k] = v
        ideator_data["proposals"][prop_index] = target_prop
        project.analysis = {**project.analysis, "ideator": ideator_data}
        flag_modified(project, "analysis")

    db.add(Message(project_id=pid, role="user", content=body.message))
    bot_msg = Message(
        project_id=pid, role="assistant", content=reply_text, evidence=[]
    )
    db.add(bot_msg)
    db.commit()

    return {
        "reply": reply_text,
        "proposal": target_prop,
        "ideator": ideator_data,
    }


@app.get("/api/projects/{pid}/proposals/{proposal_id}/export")
def export_proposal(
    pid: str,
    proposal_id: str,
    user=Depends(current_user),
    db=Depends(db_session),
):
    project = project_for(db, pid, user)
    ideator_data = project.analysis.get("ideator")
    if not ideator_data:
        raise HTTPException(404, "No ideator data found.")
    target_prop = next(
        (p for p in ideator_data.get("proposals", []) if p.get("id") == proposal_id),
        None,
    )
    if not target_prop and ideator_data.get("proposals"):
        target_prop = ideator_data["proposals"][0]
    if not target_prop:
        raise HTTPException(404, "Proposal not found.")

    doc = generate_export_markdown(target_prop, ideator_data.get("digest", {}))
    clean_title = re.sub(r"[^a-zA-Z0-9_-]", "_", target_prop.get("title", "proposal"))[:50]
    filename = f"{clean_title}.md"
    return Response(
        content=doc,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/projects/{pid}/papers/{paper_id}/pdf")
def pdf(pid: str, paper_id: str, user=Depends(current_user), db=Depends(db_session)):
    active_project_for(db, pid, user)
    p = db.get(Paper, paper_id)
    if not p or p.project_id != pid or not p.file:
        raise HTTPException(404, "PDF is not available.")
    return Response(
        read_pdf(p.file), media_type="application/pdf", headers={"Content-Disposition": "inline"}
    )


@app.get("/api/projects/{pid}/evidence")
def evidence(pid: str, q: str = "", user=Depends(current_user), db=Depends(db_session)):
    active_project_for(db, pid, user)
    if q:
        return retrieve(db, pid, q, 30)
    from backend.research import evidence_dict

    return [
        evidence_dict(c, p)
        for c, p in db.execute(
            select(Chunk, Paper)
            .join(Paper)
            .where(Paper.project_id == pid, Paper.selected == True)
            .limit(300)
        )
    ]


@app.get("/api/projects/{pid}/messages")
def messages(pid: str, user=Depends(current_user), db=Depends(db_session)):
    project_for(db, pid, user)
    return [
        public(m)
        for m in db.scalars(
            select(Message).where(Message.project_id == pid).order_by(Message.created)
        )
    ]


@app.post("/api/projects/{pid}/chat")
def chat(pid: str, body: Question, user=Depends(current_user), db=Depends(db_session)):
    active_project_for(db, pid, user)
    refs = retrieve(db, pid, body.content)
    if not refs:
        answer = "I could not find supporting evidence in your selected, indexed papers. Try a more specific question or add relevant papers."
    elif not configured():
        answer = "AI synthesis is not configured. These are the most relevant source passages for your question; open them to inspect the original evidence. Add LLM_API_KEY to enable synthesized answers."
    else:
        try:
            result = llm(
                'Answer only from the supplied evidence. Return {"claims":[{"text":"answer sentence","sources":[{"id":"chunk ID","quote":"verbatim supporting quote of at least 20 characters"}]}]}. If insufficient, return empty claims. Never invent missing metrics.',
                json.dumps({"question": body.content, "evidence": refs}),
            )
            claims = validate_claims(result.get("claims", []), refs)
            used = {s["id"] for c in claims for s in c["sources"]}
            refs = [e for e in refs if e["id"] in used]
            answer = (
                "\n\n".join(
                    c["text"]
                    + " "
                    + "".join(
                        f'[{next(i+1 for i,e in enumerate(refs) if e["id"]==s["id"])}]'
                        for s in c["sources"]
                    )
                    for c in claims
                )
                or "The selected evidence does not support an answer to this question."
            )
        except ValueError as exc:
            raise HTTPException(502, str(exc)) from None
        except Exception:
            raise HTTPException(
                502,
                "The AI provider could not answer. Check your settings and try again.",
            )
    # A response already in flight may finish after the page closes; retain only its text.
    db.expire_all()
    workspace = db.get(Workspace, pid)
    if not workspace or workspace.closed:
        refs = []
    db.add(Message(project_id=pid, role="user", content=body.content))
    msg = Message(project_id=pid, role="assistant", content=answer, evidence=refs)
    db.add(msg)
    db.commit()
    return public(msg)


@app.patch("/api/projects/{pid}/review")
def review(pid: str, body: Review, user=Depends(current_user), db=Depends(db_session)):
    from copy import deepcopy

    p = active_project_for(db, pid, user)
    idle(db, pid)
    if body.status not in (
        "supported",
        "partially_supported",
        "unsupported",
        "conflicting",
        "needs_review",
    ):
        raise HTTPException(422, "Invalid review status.")
    analysis = deepcopy(p.analysis)
    changed = False
    claims = [
        c for paper in analysis.get("papers", []) for c in paper["claims"]
    ] + analysis.get("gaps", [])
    for claim in claims:
        if claim["text"] == body.text and {s["id"] for s in claim["sources"]} == set(
            body.source_ids
        ):
            claim["status"] = body.status
            changed = True
    if not changed:
        raise HTTPException(404, "Finding not found. Refresh the analysis.")
    p.analysis = analysis
    p.report = ""
    p.status = "analyzed"
    db.commit()
    return {"ok": True}


@app.get("/api/projects/{pid}/export")
def export(pid: str, user=Depends(current_user), db=Depends(db_session)):
    p = project_for(db, pid, user)
    if not p.report:
        raise HTTPException(409, "Generate a report first.")
    return PlainTextResponse(
        p.report,
        headers={"Content-Disposition": 'attachment; filename="researchos-review.md"'},
    )



# ==============================================================================
# Simple, Direct Research Paper RAG Endpoints (PDF -> Extract -> RAG -> Questions)
# ==============================================================================

from backend.rag_engine import SAMPLE_PAPERS, search_chunks, build_rag_answer

class RagSampleRequest(BaseModel):
    pid: str
    sample: str = "attention"

class RagAskRequest(BaseModel):
    pid: str
    question: str

class RagResetRequest(BaseModel):
    pid: str

@app.get("/api/rag/status")
def rag_status(pid: str, user=Depends(current_user), db=Depends(db_session)):
    project = project_for(db, pid, user)
    paper = db.scalar(
        select(Paper).where(Paper.project_id == pid, Paper.selected == True).order_by(Paper.id.desc()).limit(1)
    )
    if not paper:
        return {"has_paper": False, "paper": None, "chunks_count": 0, "pages_count": 0, "suggested_questions": []}
    
    chunks = list(db.scalars(select(Chunk).where(Chunk.paper_id == paper.id)))
    pages = set(c.page for c in chunks)
    
    # Derive suggested questions from sample or paper metadata
    suggested = [
        "What is the primary contribution of this paper?",
        "What methodology and architecture does it propose?",
        "What benchmark datasets and results were reported?",
        "What limitations or shortcomings are discussed?"
    ]
    for s_key, s_data in SAMPLE_PAPERS.items():
        if s_data["title"].lower() in paper.title.lower() or paper.title.lower() in s_data["title"].lower():
            suggested = s_data.get("suggested_questions", suggested)
            break

    return {
        "has_paper": True,
        "paper": {
            "id": paper.id,
            "title": paper.title,
            "authors": paper.authors,
            "year": paper.year,
            "abstract": paper.abstract,
        },
        "chunks_count": len(chunks),
        "pages_count": len(pages) if pages else 1,
        "suggested_questions": suggested,
    }


@app.post("/api/rag/sample")
def rag_load_sample(body: RagSampleRequest, user=Depends(current_user), db=Depends(db_session)):
    pid = body.pid
    sample_key = body.sample if body.sample in SAMPLE_PAPERS else "attention"
    s_data = SAMPLE_PAPERS[sample_key]

    project_for(db, pid, user)
    idle(db, pid)

    # Clean existing papers/chunks for this project
    papers = list(db.scalars(select(Paper).where(Paper.project_id == pid)))
    for p in papers:
        db.execute(delete(Chunk).where(Chunk.paper_id == p.id))
        db.delete(p)
    # Clear prior messages
    db.execute(delete(Message).where(Message.project_id == pid))
    db.flush()

    new_paper = Paper(
        project_id=pid,
        title=s_data["title"],
        authors=s_data["authors"],
        year=s_data.get("year", 2024),
        abstract=s_data["abstract"],
        selected=True,
        source="Sample",
        status="indexed",
    )
    db.add(new_paper)
    db.flush()

    for item in s_data["chunks"]:
        db.add(Chunk(
            paper_id=new_paper.id,
            page=item["page"],
            section=item["section"],
            text=item["text"]
        ))
    db.commit()

    return {
        "status": "ok",
        "title": new_paper.title,
        "chunks_count": len(s_data["chunks"]),
        "pages_count": len(set(c["page"] for c in s_data["chunks"])),
        "suggested_questions": s_data.get("suggested_questions", []),
    }


@app.post("/api/rag/upload")
async def rag_upload_pdf(
    pid: str = Form(...),
    file: UploadFile = None,
    user=Depends(current_user),
    db=Depends(db_session),
):
    project_for(db, pid, user)
    idle(db, pid)

    if not file:
        raise HTTPException(400, "Please provide a PDF file.")
    raw = await file.read(25 * 1024 * 1024 + 1)
    if len(raw) > 25 * 1024 * 1024:
        raise HTTPException(413, "PDF must be smaller than 25 MB.")
    
    try:
        chunks = await __import__("asyncio").to_thread(chunk_pdf, raw)
    except Exception as exc:
        raise HTTPException(422, str(exc) if isinstance(exc, ValueError) else "Unable to parse this PDF.")

    filename = Path(file.filename or "Uploaded Research Paper.pdf").stem

    # Clean previous paper for this project
    papers = list(db.scalars(select(Paper).where(Paper.project_id == pid)))
    for p in papers:
        db.execute(delete(Chunk).where(Chunk.paper_id == p.id))
        db.delete(p)
    db.execute(delete(Message).where(Message.project_id == pid))
    db.flush()

    # Detect title and abstract from first chunks
    first_chunk_text = chunks[0]["text"] if chunks else ""
    title_candidate = filename
    if len(first_chunk_text.splitlines()) > 0:
        first_line = first_chunk_text.splitlines()[0].strip()
        if 5 < len(first_line) < 160:
            title_candidate = first_line

    new_paper = Paper(
        project_id=pid,
        title=title_candidate[:300],
        abstract=first_chunk_text[:1500],
        selected=True,
        source="Upload",
        status="indexed",
    )
    db.add(new_paper)
    db.flush()

    for item in chunks:
        db.add(Chunk(
            paper_id=new_paper.id,
            page=item["page"],
            section=item["section"],
            text=item["text"]
        ))
    db.commit()

    pages = set(c["page"] for c in chunks)
    return {
        "status": "ok",
        "title": new_paper.title,
        "chunks_count": len(chunks),
        "pages_count": len(pages),
        "suggested_questions": [
            "What is the primary contribution of this paper?",
            "What methodology and architecture does it propose?",
            "What benchmark datasets and results were reported?",
            "What limitations or shortcomings are discussed?"
        ]
    }


@app.post("/api/rag/ask")
async def rag_ask(
    body: RagAskRequest,
    user=Depends(current_user),
    db=Depends(db_session),
):
    pid = body.pid
    question = body.question.strip()
    if not question:
        raise HTTPException(400, "Question cannot be empty.")

    project_for(db, pid, user)
    paper = db.scalar(
        select(Paper).where(Paper.project_id == pid, Paper.selected == True).order_by(Paper.id.desc()).limit(1)
    )
    if not paper:
        raise HTTPException(400, "No research paper uploaded yet. Please upload a PDF first.")

    chunks = list(db.scalars(select(Chunk).where(Chunk.paper_id == paper.id)))
    if not chunks:
        raise HTTPException(400, "No readable chunks found in this paper.")

    # Retrieve relevant chunks
    matches = search_chunks(chunks, question, top_k=5)

    # Fetch recent conversation history
    history = [
        {"role": m.role, "content": m.content}
        for m in db.scalars(
            select(Message).where(Message.project_id == pid).order_by(Message.created).limit(8)
        )
    ]

    # Generate grounded RAG answer
    answer = await __import__("asyncio").to_thread(
        build_rag_answer, paper.title, question, matches, history
    )

    # Save to history
    db.add(Message(project_id=pid, role="user", content=question))
    assistant_msg = Message(
        project_id=pid,
        role="assistant",
        content=answer,
        evidence=[
            {
                "id": m["chunk_id"],
                "page": m["page"],
                "section": m["section"],
                "snippet": m["snippet"],
                "score": m["score"],
            }
            for m in matches
        ]
    )
    db.add(assistant_msg)
    db.commit()

    return {
        "answer": answer,
        "citations": [
            {
                "chunk_id": m["chunk_id"],
                "page": m["page"],
                "section": m["section"],
                "snippet": m["snippet"],
                "score": m["score"],
            }
            for m in matches
        ]
    }


@app.post("/api/rag/reset")
def rag_reset(body: RagResetRequest, user=Depends(current_user), db=Depends(db_session)):
    pid = body.pid
    project_for(db, pid, user)
    papers = list(db.scalars(select(Paper).where(Paper.project_id == pid)))
    for p in papers:
        db.execute(delete(Chunk).where(Chunk.paper_id == p.id))
        db.delete(p)
    db.execute(delete(Message).where(Message.project_id == pid))
    db.commit()
    return {"status": "ok"}


dist_dir = Path("dist").resolve()
if dist_dir.exists():
    app.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="assets")

    @app.get("/{path:path}")
    def frontend(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Endpoint not found")
        asset = (dist_dir / path).resolve()
        if asset.is_relative_to(dist_dir) and asset.is_file():
            return FileResponse(
                asset, media_type="image/webp" if asset.suffix.lower() == ".webp" else None
            )
        return FileResponse(dist_dir / "index.html")
