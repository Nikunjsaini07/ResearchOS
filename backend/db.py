"""Database connection and tables shared by the API and research pipeline."""

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, String, Text, JSON, ForeignKey, Index, text
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

load_dotenv()
DATA = Path(os.getenv("DATA_DIR", "./data"))
DATA.mkdir(parents=True, exist_ok=True)
url = os.getenv("DATABASE_URL", "sqlite:///./data/researchos.db")
engine = create_engine(
    url,
    connect_args=(
        {"check_same_thread": False, "timeout": 30} if url.startswith("sqlite") else {}
    ),
    pool_pre_ping=True,
)
Session = sessionmaker(engine, expire_on_commit=False)


def uid():
    return uuid.uuid4().hex


def now():
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password: Mapped[str] = mapped_column(Text)


class AuthSession(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    expires: Mapped[float]


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    question: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    created: Mapped[str] = mapped_column(String(40), default=now)
    plan: Mapped[dict] = mapped_column(JSON, default=dict)
    analysis: Mapped[dict] = mapped_column(JSON, default=dict)
    report: Mapped[str] = mapped_column(Text, default="")


class Paper(Base):
    __tablename__ = "papers"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    title: Mapped[str] = mapped_column(Text)
    authors: Mapped[str] = mapped_column(Text, default="")
    year: Mapped[int] = mapped_column(default=0)
    abstract: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(Text, default="")
    pdf_url: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(40), default="Upload")
    selected: Mapped[bool] = mapped_column(default=False)
    score: Mapped[float] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(40), default="discovered")
    error: Mapped[str] = mapped_column(Text, default="")
    file: Mapped[str] = mapped_column(Text, default="")


class Chunk(Base):
    __tablename__ = "chunks"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id"), index=True)
    page: Mapped[int]
    section: Mapped[str] = mapped_column(String(100))
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list | None] = mapped_column(
        JSON().with_variant(Vector(), "postgresql"), nullable=True, default=lambda: None
    )


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="queued")
    progress: Mapped[int] = mapped_column(default=0)
    events: Mapped[list] = mapped_column(JSON, default=list)
    error: Mapped[str] = mapped_column(Text, default="")
    created: Mapped[str] = mapped_column(String(40), default=now)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    created: Mapped[str] = mapped_column(String(40), default=now)


Index(
    "one_active_job_per_project",
    Job.project_id,
    unique=True,
    sqlite_where=text("status IN ('queued', 'running')"),
    postgresql_where=text("status IN ('queued', 'running')"),
)
