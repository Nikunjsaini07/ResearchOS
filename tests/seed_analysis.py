"""Create explicitly synthetic analysis for browser presentation tests only."""

import sys
from sqlalchemy import select
from backend.db import Session, Project, Paper, Chunk, now
from backend.research import evidence_dict

pid = sys.argv[1]
with Session() as db:
    p = db.get(Project, pid)
    assert (
        p.title == "Browser analysis fixture"
    ), "Only a test fixture project may be seeded."
    paper = db.scalar(select(Paper).where(Paper.project_id == pid))
    chunks = list(db.scalars(select(Chunk).where(Chunk.paper_id == paper.id)))
    evidence = [evidence_dict(c, paper) for c in chunks]
    claims = [
        {
            "text": c.text.split("\n", 1)[-1],
            "dimension": {
                "Methods": "Method",
                "Results": "Results",
                "Limitations": "Limitations",
            }[c.section],
            "sources": [{"id": c.id, "quote": c.text}],
            "status": "needs_review",
        }
        for c in chunks
    ]
    limitation = next(c for c in chunks if c.section == "Limitations")
    p.analysis = {
        "papers": [{"paper_id": paper.id, "title": paper.title, "claims": claims}],
        "gaps": [
            {
                "text": "Potential gap within this test corpus: multilingual evaluation is not reported.",
                "dimension": "Potential gap",
                "sources": [{"id": limitation.id, "quote": limitation.text}],
                "status": "needs_review",
            }
        ],
        "evidence": evidence,
        "created": now(),
        "note": "Synthetic test fixture, not scientific findings.",
    }
    p.status = "analyzed"
    db.commit()
