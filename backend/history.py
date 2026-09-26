"""Retain text history and remove temporary research material."""
import logging
import time

from sqlalchemy import delete, select, or_

from backend.db import Project, Workspace, Paper, Chunk, Job, Message
from backend.storage import delete_pdf

log = logging.getLogger("researchos.history")
WORKSPACE_TTL = 60 * 60


def result_text(project):
    if project.report:
        heading = f"# {project.title}\n\n## Research question\n{project.question}\n\n"
        return project.report.removeprefix(heading)
    analysis = project.analysis or {}
    lines = []
    for title, claims in (
        ("Answer", analysis.get("overview", [])),
        ("Findings", analysis.get("findings") or [c for p in analysis.get("papers", []) for c in p.get("claims", [])]),
        ("Research directions", analysis.get("gaps", [])),
    ):
        if claims:
            lines.append("## " + title)
            for claim in claims:
                lines.append(claim.get("text", ""))
                lines.extend(claim[key] for key in ("rationale", "next_step") if claim.get(key))
    if analysis.get("note"):
        lines.append(analysis["note"])
    return "\n\n".join(lines) or "This conversation ended before a result was generated."


def archive_project(db, project):
    """Only prune idle work. A closed workspace is retried after its job finishes."""
    if db.scalar(select(Job.id).where(Job.project_id == project.id, Job.status.in_(["queued", "running"]))):
        return False
    project.report = result_text(project)
    papers = list(db.scalars(select(Paper).where(Paper.project_id == project.id)))
    # Keep legacy file references until deletion succeeds so cleanup can retry.
    for paper in papers:
        if paper.file:
            delete_pdf(paper.file)
    paper_ids = select(Paper.id).where(Paper.project_id == project.id)
    db.execute(delete(Chunk).where(Chunk.paper_id.in_(paper_ids)))
    db.execute(delete(Paper).where(Paper.project_id == project.id))
    db.execute(delete(Job).where(Job.project_id == project.id))
    for message in db.scalars(select(Message).where(Message.project_id == project.id)):
        if message.evidence:
            references = [f"{i + 1}. {item.get('title', 'Source')} {item.get('url', '')}" for i, item in enumerate(message.evidence)]
            message.content += "\n\nSources:\n" + "\n".join(references)
        message.evidence = []
    db.execute(delete(Workspace).where(Workspace.project_id == project.id))
    project.analysis = {}
    project.plan = {}
    project.status = "archived"
    db.commit()
    return True


def close_project(db, project):
    workspace = db.get(Workspace, project.id)
    if workspace:
        workspace.closed = True
        db.commit()
    try:
        return archive_project(db, project)
    except (OSError, ValueError):
        db.rollback()
        log.exception("Legacy PDF cleanup will retry project_id=%s", project.id)
        return False


def cleanup_history(db):
    candidates = list(db.scalars(
        select(Project).outerjoin(Workspace, Workspace.project_id == Project.id).where(
            Project.status != "archived",
            or_(Workspace.project_id.is_(None), Workspace.closed.is_(True), Workspace.expires <= time.time()),
        )
    ))
    for project in candidates:
        try:
            close_project(db, project)
        except Exception:
            db.rollback()
            log.exception("Temporary research cleanup will retry project_id=%s", project.id)
