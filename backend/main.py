"""HTTP API and background job worker. Start with create_project, run, and worker."""

import hashlib
import hmac
import logging
import os
import re
import secrets
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from collections import defaultdict, deque
from fastapi import FastAPI, HTTPException, Request, Response, Depends, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select, delete, func, update, text
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
    DATA,
)
from backend.research import (
    WORKFLOWS,
    configured,
    retrieve,
    llm,
    validate_claims,
    chunk_pdf,
)
import json

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("researchos")
stop = threading.Event()


def worker():
    while not stop.wait(0.7):
        try:
            with Session() as db:
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
        except Exception:
            log.exception("Worker polling failed")


@asynccontextmanager
async def lifespan(app):
    if engine.dialect.name == "postgresql":
        with engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    with Session() as db:
        for j in db.scalars(select(Job).where(Job.status == "running")):
            j.status = "failed"
            j.error = "The server restarted during this run. Retry the step."
        db.commit()
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
    token = request.cookies.get("researchos_session", "")
    session = (
        db.get(AuthSession, hashlib.sha256(token.encode()).hexdigest())
        if token
        else None
    )
    if not session or session.expires < time.time():
        raise HTTPException(401, "Please sign in to continue.")
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(401, "Please sign in again.")
    return user


def project_for(db, pid, user):
    p = db.get(Project, pid)
    if not p or p.user_id != user.id:
        raise HTTPException(404, "Research project not found.")
    return p


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
    papers = list(db.scalars(select(Paper).where(Paper.project_id == p.id)))
    data.update(
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


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    return (
        salt
        + ":"
        + hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    )


def login_cookie(db, user, response):
    token = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            id=hashlib.sha256(token.encode()).hexdigest(),
            user_id=user.id,
            expires=time.time() + 7 * 86400,
        )
    )
    db.commit()
    response.set_cookie(
        "researchos_session",
        token,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
        max_age=7 * 86400,
    )
    return public(user, ("password",))


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
        return public(db.get(User, session.user_id), ("password",))
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
def login(body: Credentials, response: Response, db=Depends(db_session)):
    u = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if not u or not hmac.compare_digest(
        u.password, password_hash(body.password, u.password.split(":")[0])
    ):
        raise HTTPException(401, "Email or password is incorrect.")
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
def me(user=Depends(current_user)):
    return public(user, ("password",))


@app.get("/api/settings")
def settings(user=Depends(current_user)):
    return {
        "ai_configured": configured(),
        "model": os.getenv("LLM_MODEL", "gpt-4.1-mini"),
        "embeddings_configured": bool(os.getenv("EMBEDDING_API_KEY") or configured()),
        "database": "PostgreSQL" if "postgres" in str(engine.url) else "SQLite",
        "search_source": "arXiv",
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
    db.commit()
    return project_json(db, p)


@app.get("/api/projects/{pid}")
def get_project(pid: str, user=Depends(current_user), db=Depends(db_session)):
    return project_json(db, project_for(db, pid, user))


@app.delete("/api/projects/{pid}")
def delete_project(pid: str, user=Depends(current_user), db=Depends(db_session)):
    p = project_for(db, pid, user)
    idle(db, pid)
    papers = list(db.scalars(select(Paper).where(Paper.project_id == pid)))
    for paper in papers:
        db.execute(delete(Chunk).where(Chunk.paper_id == paper.id))
        if paper.file:
            Path(paper.file).unlink(missing_ok=True)
    for model in (Message, Job, Paper):
        db.execute(delete(model).where(model.project_id == pid))
    db.delete(p)
    db.commit()
    return {"ok": True}


@app.patch("/api/projects/{pid}/plan")
def edit_plan(
    pid: str, body: PlanEdit, user=Depends(current_user), db=Depends(db_session)
):
    p = project_for(db, pid, user)
    idle(db, pid)
    if any(not q.strip() or len(q) > 300 for q in body.queries):
        raise HTTPException(422, "Queries must contain 1–300 characters.")
    p.plan = {**p.plan, "queries": [q.strip() for q in body.queries]}
    db.commit()
    return p.plan


@app.post("/api/projects/{pid}/run/{kind}", status_code=202)
def run(pid: str, kind: str, user=Depends(current_user), db=Depends(db_session)):
    p = project_for(db, pid, user)
    idle(db, pid)
    if kind not in WORKFLOWS:
        raise HTTPException(404, "Unknown research step.")
    if kind == "analyze" and not configured():
        raise HTTPException(
            409,
            "Set LLM_API_KEY in .env and restart the backend to enable AI analysis.",
        )
    if kind in ("index", "analyze"):
        count = db.scalar(
            select(func.count())
            .select_from(Paper)
            .where(Paper.project_id == pid, Paper.selected == True)
        )
        if count > 20:
            raise HTTPException(422, "Select at most 20 papers per research run.")
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
    project = project_for(db, pid, user)
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
    pid: str, file: UploadFile, user=Depends(current_user), db=Depends(db_session)
):
    project = project_for(db, pid, user)
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
    path = DATA / f"{p.id}.pdf"
    path.write_bytes(raw)
    p.file = str(path)
    for chunk in chunks:
        db.add(Chunk(paper_id=p.id, **chunk))
    project.analysis = {}
    project.report = ""
    project.status = "indexed"
    db.commit()
    return {**public(p, ("file",)), "has_pdf": True}


@app.get("/api/projects/{pid}/papers/{paper_id}/pdf")
def pdf(pid: str, paper_id: str, user=Depends(current_user), db=Depends(db_session)):
    project_for(db, pid, user)
    p = db.get(Paper, paper_id)
    if not p or p.project_id != pid or not p.file:
        raise HTTPException(404, "PDF is not available.")
    return FileResponse(
        p.file, media_type="application/pdf", headers={"Content-Disposition": "inline"}
    )


@app.get("/api/projects/{pid}/evidence")
def evidence(pid: str, q: str = "", user=Depends(current_user), db=Depends(db_session)):
    project_for(db, pid, user)
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
    project_for(db, pid, user)
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
        except Exception:
            raise HTTPException(
                502,
                "The AI provider could not answer. Check your settings and try again.",
            )
    db.add(Message(project_id=pid, role="user", content=body.content))
    msg = Message(project_id=pid, role="assistant", content=answer, evidence=refs)
    db.add(msg)
    db.commit()
    return public(msg)


@app.patch("/api/projects/{pid}/review")
def review(pid: str, body: Review, user=Depends(current_user), db=Depends(db_session)):
    from copy import deepcopy

    p = project_for(db, pid, user)
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


if Path("dist").exists():
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")

    @app.get("/{path:path}")
    def frontend(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Endpoint not found")
        if path in ("favicon.svg", "research-world.png"):
            return FileResponse("dist/" + path)
        return FileResponse("dist/index.html")
