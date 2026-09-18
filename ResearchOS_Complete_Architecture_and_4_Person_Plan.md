# ResearchOS — Complete Project Plan

> An agentic research-paper intelligence platform for students and researchers.
>
> **Team size:** 4  
> **Recommended duration:** 8–10 weeks  
> **Primary stack:** React + TypeScript, FastAPI + Python, PostgreSQL + pgvector, Redis, LangGraph, Docker

---

# 1. Project Vision

## Problem

Students and researchers spend a large amount of time:

- Finding relevant research papers
- Removing duplicate or irrelevant papers
- Reading long PDFs
- Understanding methodologies
- Comparing papers
- Tracking evidence and citations
- Identifying limitations
- Finding potential research gaps
- Writing literature reviews

ResearchOS turns this into an agentic workflow.

## Example

User:

> Compare RAG, fine-tuning, and prompt engineering for reducing LLM hallucinations.

ResearchOS:

```text
Research Question
       ↓
Query Understanding
       ↓
Research Planning
       ↓
Paper Discovery
       ↓
Paper Ranking
       ↓
PDF Collection
       ↓
PDF Processing
       ↓
Knowledge Base
       ↓
Paper Analysis
       ↓
Cross-Paper Comparison
       ↓
Potential Gap Detection
       ↓
Claim Verification
       ↓
Literature Review
       ↓
Citation-backed Report
```

---

# 2. Product Goals

## MVP

The first release must support:

- [ ] User authentication
- [ ] Create research project
- [ ] Enter research question
- [ ] Generate search queries
- [ ] Search academic sources
- [ ] Deduplicate papers
- [ ] Rank papers
- [ ] Import/download accessible PDFs
- [ ] Extract PDF text
- [ ] Section-aware chunking
- [ ] Embeddings
- [ ] Vector search
- [ ] Paper summarization
- [ ] Paper comparison
- [ ] Potential research-gap detection
- [ ] Citation-backed answers
- [ ] Literature-review generation
- [ ] Web dashboard

## Advanced Features

Build these only after MVP works:

- [ ] Citation graph
- [ ] Contradiction detection
- [ ] Claim verification
- [ ] Research timeline
- [ ] Knowledge graph
- [ ] Paper recommendation
- [ ] Research workspace
- [ ] Markdown/PDF export
- [ ] Token/cost tracking
- [ ] Evaluation dashboard
- [ ] Human-in-the-loop review
- [ ] Saved evidence
- [ ] Team collaboration

---

# 3. What Makes This More Than a PDF Chatbot?

The project should NOT be presented as:

> "Chatbot that talks to research papers."

Instead:

> "An agentic research workflow that discovers, analyzes, compares, verifies, and synthesizes academic evidence."

The important engineering components are:

1. Planning
2. Tool use
3. Retrieval
4. Evidence tracking
5. Multi-step reasoning
6. Verification
7. Human approval
8. Evaluation

---

# 4. System Architecture

```text
                              ┌──────────────────────┐
                              │        USER          │
                              └──────────┬───────────┘
                                         │
                                         ↓
                              ┌──────────────────────┐
                              │    React Frontend    │
                              └──────────┬───────────┘
                                         │
                                         ↓
                              ┌──────────────────────┐
                              │      FastAPI         │
                              │      REST API        │
                              └──────────┬───────────┘
                                         │
                         ┌───────────────┴───────────────┐
                         │                               │
                         ↓                               ↓
                ┌─────────────────┐             ┌─────────────────┐
                │ Research API    │             │     Chat API    │
                └────────┬────────┘             └────────┬────────┘
                         │                               │
                         └───────────────┬───────────────┘
                                         ↓
                              ┌──────────────────────┐
                              │  LangGraph Workflow  │
                              │  / Agent Orchestrator│
                              └──────────┬───────────┘
                                         │
                ┌────────────────────────┼────────────────────────┐
                │                        │                        │
                ↓                        ↓                        ↓
       ┌────────────────┐      ┌────────────────┐       ┌────────────────┐
       │ Search Tools   │      │ Retrieval Tools│       │ Action Tools   │
       └───────┬────────┘      └───────┬────────┘       └────────────────┘
               │                       │
               ↓                       ↓
       ┌────────────────┐      ┌────────────────────────────┐
       │ Academic APIs  │      │ PostgreSQL + pgvector      │
       │ arXiv/OpenAlex │      │ Papers / Chunks / Evidence │
       └────────────────┘      └────────────────────────────┘
                                         │
                                         ↓
                                  ┌─────────────┐
                                  │    Redis    │
                                  │ Cache/Jobs  │
                                  └─────────────┘
```

---

# 5. Recommended Tech Stack

## Frontend

```text
React
TypeScript
Vite
TailwindCSS
TanStack Query
Zustand
React Router
```

## Backend

```text
Python
FastAPI
Pydantic
SQLAlchemy
Alembic
```

## AI

```text
LangGraph
LangChain
LLM API
Embedding model/API
```

## Data

```text
PostgreSQL
pgvector
Redis
```

## Infrastructure

```text
Docker
Docker Compose
Nginx
GitHub Actions
```

## Optional

```text
S3-compatible object storage
Celery / RQ / Arq
OpenTelemetry
Sentry
```

---

# 6. Team Structure

Four people should each own a major subsystem.

```text
Person 1 → AI / Agents
Person 2 → Data / RAG
Person 3 → Frontend
Person 4 → Backend / Infrastructure
```

Everyone must contribute to integration, testing, documentation, and the final presentation.

---

# 7. Person 1 — AI / Agent Engineer

## Ownership

- LangGraph
- Agent state
- Planner
- Query generation
- Paper analysis
- Comparison
- Gap detection
- Verification
- Report generation
- Evaluation

## Tasks

### Phase 1

- [ ] Select LLM
- [ ] Define prompts
- [ ] Design agent state
- [ ] Create LangGraph skeleton
- [ ] Implement planner

### Phase 2

- [ ] Search Agent
- [ ] Paper Analysis Agent
- [ ] Comparison Agent
- [ ] Gap Detection Agent

### Phase 3

- [ ] Verification Agent
- [ ] Report Agent
- [ ] Citation handling
- [ ] Agent fallback logic

### Phase 4

- [ ] Evaluation framework
- [ ] Hallucination tests
- [ ] Retrieval-quality tests
- [ ] Token/cost tracking

---

# 8. Person 2 — Data / RAG Engineer

## Ownership

- Database
- Paper ingestion
- PDF processing
- Chunking
- Embeddings
- Retrieval
- Metadata
- Evidence
- Citation mapping

## Tasks

- [ ] PostgreSQL schema
- [ ] pgvector setup
- [ ] Paper ingestion service
- [ ] PDF parser
- [ ] Section extraction
- [ ] Chunking
- [ ] Embedding pipeline
- [ ] Vector indexing
- [ ] Hybrid search
- [ ] Reranking
- [ ] Deduplication
- [ ] Evidence storage

---

# 9. Person 3 — Frontend Engineer

## Ownership

- UI
- UX
- Dashboard
- Research workspace
- Paper explorer
- Chat
- Reports
- Evidence visualization

## Pages

```text
/login
/register
/dashboard
/research/new
/research/:id
/research/:id/papers
/research/:id/compare
/research/:id/evidence
/research/:id/report
/settings
```

## Tasks

- [ ] Design system
- [ ] Authentication UI
- [ ] Dashboard
- [ ] Create Research page
- [ ] Research progress UI
- [ ] Paper cards
- [ ] Paper viewer
- [ ] Chat UI
- [ ] Evidence panel
- [ ] Comparison table
- [ ] Research-gap visualization
- [ ] Report viewer
- [ ] Export UI
- [ ] Error/loading states

---

# 10. Person 4 — Backend / Infrastructure Engineer

## Ownership

- FastAPI
- Authentication
- APIs
- Background jobs
- Redis
- File storage
- Docker
- Deployment
- Logging

## Tasks

- [ ] FastAPI project
- [ ] Authentication
- [ ] User APIs
- [ ] Research APIs
- [ ] Paper APIs
- [ ] Chat APIs
- [ ] Background job system
- [ ] Redis
- [ ] File upload
- [ ] API validation
- [ ] Rate limiting
- [ ] Logging
- [ ] Docker
- [ ] CI/CD
- [ ] Deployment

---

# 11. Agent Architecture

Do not build one giant agent.

Use a graph of specialized nodes.

```text
                         START
                           │
                           ↓
                  ┌────────────────┐
                  │ Research       │
                  │ Planner        │
                  └───────┬────────┘
                          ↓
                  ┌────────────────┐
                  │ Query Generator│
                  └───────┬────────┘
                          ↓
                  ┌────────────────┐
                  │ Search Agent   │
                  └───────┬────────┘
                          ↓
                  ┌────────────────┐
                  │ Paper Ranker   │
                  └───────┬────────┘
                          ↓
                  ┌────────────────┐
                  │ Paper Analyzer │
                  └───────┬────────┘
                          ↓
              ┌───────────┴───────────┐
              ↓                       ↓
       ┌──────────────┐        ┌──────────────┐
       │ Comparison   │        │ Limitation   │
       │ Agent        │        │ Analyzer     │
       └──────┬───────┘        └──────┬───────┘
              └───────────┬───────────┘
                          ↓
                  ┌────────────────┐
                  │ Gap Detector   │
                  └───────┬────────┘
                          ↓
                  ┌────────────────┐
                  │ Claim          │
                  │ Verification   │
                  └───────┬────────┘
                          ↓
                  ┌────────────────┐
                  │ Report Agent   │
                  └───────┬────────┘
                          ↓
                         END
```

---

# 12. LangGraph State

Example:

```python
class ResearchState(TypedDict):

    research_question: str

    generated_queries: list[str]

    papers_found: list[dict]

    selected_papers: list[str]

    analyzed_papers: list[dict]

    evidence: list[dict]

    comparisons: list[dict]

    research_gaps: list[dict]

    verified_claims: list[dict]

    final_report: str

    errors: list[str]
```

The state is the shared memory of the workflow.

---

# 13. Research Planner

## Input

```text
Compare RAG and fine-tuning for reducing hallucinations in LLM applications.
```

## Output

```json
{
  "topic": "LLM hallucination reduction",
  "subtopics": [
    "retrieval augmented generation",
    "fine tuning",
    "prompt engineering"
  ],
  "queries": [
    "RAG hallucination reduction",
    "fine tuning hallucination reduction",
    "LLM hallucination mitigation",
    "RAG vs fine tuning LLM"
  ],
  "required_evidence": [
    "methodology",
    "dataset",
    "benchmark",
    "results",
    "limitations"
  ]
}
```

---

# 14. Search Pipeline

```text
User Question
      ↓
Generate Queries
      ↓
Search Sources
      ↓
Normalize Metadata
      ↓
Deduplicate
      ↓
Semantic Relevance
      ↓
Rank
      ↓
Select Papers
```

## Initial Sources

Start with:

```text
arXiv
OpenAlex
Crossref
Semantic Scholar
```

Do not start by scraping random websites.

---

# 15. Paper Metadata

Store:

```json
{
  "title": "...",
  "authors": [],
  "abstract": "...",
  "year": 2025,
  "doi": "...",
  "url": "...",
  "pdf_url": "...",
  "source": "arxiv"
}
```

---

# 16. Paper Ranking

Use a deterministic ranking layer.

Example:

```text
Final Score =
    0.45 × Semantic Similarity
  + 0.20 × Keyword Relevance
  + 0.15 × Recency
  + 0.20 × Source Quality
```

Keep weights configurable.

The LLM should not be the only ranking mechanism.

---

# 17. PDF Processing Pipeline

```text
PDF
 ↓
Download
 ↓
Validate
 ↓
Extract Text
 ↓
Detect Sections
 ↓
Clean Text
 ↓
Chunk
 ↓
Generate Embeddings
 ↓
Store
```

---

# 18. Section-Aware Chunking

Do not blindly split every document into fixed-size chunks.

Preserve:

```text
Abstract
Introduction
Related Work
Methodology
Experiments
Results
Discussion
Limitations
Conclusion
References
```

Each chunk should contain:

```json
{
  "paper_id": "paper_123",
  "section": "Results",
  "page": 8,
  "chunk_index": 31,
  "text": "...",
  "embedding": "..."
}
```

---

# 19. RAG Architecture

Use hybrid retrieval.

```text
                    Query
                      │
             ┌────────┴────────┐
             ↓                 ↓
       Vector Search      Keyword Search
             ↓                 ↓
             └────────┬────────┘
                      ↓
                  Reranker
                      ↓
               Top Evidence
                      ↓
                     LLM
```

---

# 20. Evidence Model

Every important generated claim should have evidence.

```json
{
  "claim": "Method X improved benchmark Y.",
  "evidence": [
    {
      "paper_id": "paper_123",
      "page": 8,
      "section": "Results",
      "chunk_id": "chunk_31"
    }
  ],
  "verification_status": "verified"
}
```

Possible statuses:

```text
verified
partially_verified
unsupported
conflicting
```

---

# 21. Citation Architecture

Never generate citations after writing the report.

Instead:

```text
Evidence
   ↓
Claim
   ↓
Claim Verification
   ↓
Report Generation
```

The report generator receives evidence IDs.

Example:

```text
RAG improved factuality on benchmark X [1].

[1] Paper Name, Authors, 2025, Results, p.8
```

---

# 22. Paper Analysis

For each selected paper extract:

```text
Title
Research Question
Problem
Method
Dataset
Model
Baseline
Metrics
Results
Limitations
Future Work
```

Example:

```json
{
  "paper_id": "123",
  "problem": "...",
  "method": "...",
  "dataset": "...",
  "metrics": ["accuracy", "F1"],
  "results": [],
  "limitations": []
}
```

---

# 23. Comparison Agent

Input:

```text
Paper A
Paper B
Paper C
```

Output:

```text
| Dimension | Paper A | Paper B | Paper C |
|-----------|---------|---------|---------|
| Method | ... | ... | ... |
| Dataset | ... | ... | ... |
| Model | ... | ... | ... |
| Metric | ... | ... | ... |
| Result | ... | ... | ... |
| Limitation | ... | ... | ... |
```

Every cell should be traceable to evidence.

---

# 24. Research Gap Detection

This is one of the most important features.

The system should look for:

```text
Underexplored datasets
Missing populations
Conflicting findings
Unexplored combinations
Known limitations
Old benchmarks
Missing evaluation
Unaddressed constraints
```

Example:

```text
Paper A:
Evaluates English datasets.

Paper B:
Evaluates multilingual datasets.

Paper C:
Evaluates long-context datasets.

Potential gap:
Limited evidence exists for systems combining
multilingual + long-context evaluation.

Evidence:
Paper A, page X
Paper B, page Y
Paper C, page Z
```

Use the phrase:

> "Potential research gap"

rather than claiming:

> "Nobody has researched this."

---

# 25. Claim Verification

Before producing the final report:

```text
Generated Claim
      ↓
Retrieve Supporting Evidence
      ↓
Check Evidence
      ↓
Does evidence support claim?
      │
   ┌──┴──┐
   │     │
  YES    NO
   │     │
   ↓     ↓
Verified Unsupported
```

For conflicting evidence:

```text
Claim
 ↓
Paper A supports it
Paper B contradicts it
 ↓
Mark as CONFLICTING
 ↓
Show both sources
```

---

# 26. Report Structure

```text
# Literature Review

## 1. Research Question

## 2. Search Methodology

## 3. Papers Selected

## 4. Background

## 5. Method Comparison

## 6. Findings

## 7. Contradictory Evidence

## 8. Limitations

## 9. Potential Research Gaps

## 10. Conclusion

## 11. References
```

---

# 27. Database Schema

## Users

```text
users
------
id
name
email
password_hash
created_at
```

## Research Projects

```text
research_projects
-----------------
id
user_id
title
research_question
status
created_at
updated_at
```

## Papers

```text
papers
------
id
external_id
title
abstract
year
doi
url
pdf_url
source
created_at
```

## Authors

```text
authors
-------
id
name
```

## Paper Authors

```text
paper_authors
-------------
paper_id
author_id
author_order
```

## Research Papers

```text
research_papers
---------------
research_id
paper_id
relevance_score
selected
```

## Paper Chunks

```text
paper_chunks
------------
id
paper_id
section
page_number
chunk_index
content
embedding
```

## Evidence

```text
evidence
--------
id
research_id
paper_id
chunk_id
claim
page_number
verification_status
```

## Research Gaps

```text
research_gaps
-------------
id
research_id
description
confidence
evidence
status
```

## Reports

```text
reports
-------
id
research_id
content
version
created_at
```

---

# 28. API Architecture

## Authentication

```http
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/logout
GET  /api/v1/auth/me
```

## Research

```http
POST /api/v1/research
GET  /api/v1/research
GET  /api/v1/research/{id}
DELETE /api/v1/research/{id}
POST /api/v1/research/{id}/run
```

## Papers

```http
GET  /api/v1/research/{id}/papers
GET  /api/v1/papers/{id}
POST /api/v1/research/{id}/papers/import
```

## Chat

```http
POST /api/v1/research/{id}/chat
GET  /api/v1/research/{id}/messages
```

## Analysis

```http
POST /api/v1/research/{id}/analyze
GET  /api/v1/research/{id}/analysis
GET  /api/v1/research/{id}/gaps
```

## Reports

```http
POST /api/v1/research/{id}/report
GET  /api/v1/research/{id}/report
GET  /api/v1/research/{id}/report/export
```

---

# 29. Background Jobs

Research can take several minutes.

Do not keep the HTTP request open.

Use:

```text
FastAPI
   ↓
Redis Queue
   ↓
Worker
   ↓
LangGraph
```

Example:

```text
POST /research/123/run

Response:

{
  "job_id": "job_123",
  "status": "queued"
}
```

Frontend then checks:

```text
GET /jobs/job_123
```

or uses WebSockets/SSE for live progress.

---

# 30. Progress Events

The UI should show:

```text
✓ Research question analyzed
✓ Search queries generated
✓ 87 papers discovered
✓ 42 duplicate papers removed
✓ 20 papers selected
✓ 20 papers processed
✓ Evidence extracted
● Comparing papers
○ Detecting research gaps
○ Generating report
```

This makes the agent feel like a real system rather than a single loading spinner.

---

# 31. Frontend Layout

## Dashboard

```text
--------------------------------------------
ResearchOS

Your Research Projects

[ + New Research ]

--------------------------------------------

LLM Hallucination Research
Status: Completed
Papers: 32
Gaps: 7

AI Code Generation
Status: Running
Papers: 18
Progress: 64%

--------------------------------------------
```

---

# 32. Research Workspace

```text
┌───────────────────────────────────────────┐
│ Research Question                         │
│                                           │
│ Compare RAG and fine-tuning...            │
└───────────────────────────────────────────┘

[ Overview ] [ Papers ] [ Evidence ]
[ Comparison ] [ Gaps ] [ Chat ] [ Report ]
```

---

# 33. Paper UI

Each paper:

```text
Paper Title

Authors
Year
Source

Relevance: 92%

Abstract

[Read Paper]

Analysis
├── Method
├── Dataset
├── Results
└── Limitations
```

---

# 34. Evidence UI

When the user clicks a claim:

```text
CLAIM

"Method X improved factuality."

Evidence

Paper: Example Paper
Page: 8
Section: Results

[Open Evidence]
```

This is a major trust feature.

---

# 35. Chat

User:

> Why did Paper A perform better than Paper B?

System:

```text
Paper A used Dataset X...
Paper B used Dataset Y...

The papers differ primarily in...
```

Then show:

```text
Sources:
[Paper A — p.8]
[Paper B — p.12]
```

---

# 36. Project Repository

Recommended monorepo:

```text
researchos/
│
├── frontend/
│   ├── src/
│   ├── components/
│   ├── pages/
│   ├── hooks/
│   └── services/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── repositories/
│   │   └── main.py
│   │
│   └── tests/
│
├── agents/
│   ├── planner/
│   ├── search/
│   ├── analysis/
│   ├── comparison/
│   ├── verification/
│   ├── gap_detection/
│   └── report/
│
├── ingestion/
│   ├── pdf/
│   ├── chunking/
│   └── embeddings/
│
├── evaluation/
│
├── docker/
│
├── docs/
│
├── docker-compose.yml
├── README.md
└── .env.example
```

---

# 37. Git Workflow

Use:

```text
main
develop
feature/*
bugfix/*
```

Never work directly on `main`.

Example:

```bash
git checkout develop
git pull

git checkout -b feature/paper-ingestion
```

Then:

```bash
git add .
git commit -m "feat: add paper ingestion pipeline"
git push origin feature/paper-ingestion
```

Create PR → review → merge.

---

# 38. Commit Convention

Use:

```text
feat:
fix:
refactor:
docs:
test:
chore:
```

Examples:

```text
feat: add paper search service
feat: implement research planner
fix: handle invalid PDF
test: add retrieval tests
docs: update architecture
```

---

# 39. Environment Variables

Never commit secrets.

```env
DATABASE_URL=
REDIS_URL=

LLM_API_KEY=
EMBEDDING_API_KEY=

SEMANTIC_SCHOLAR_API_KEY=
OPENALEX_API_KEY=

JWT_SECRET=
STORAGE_BUCKET=
```

Commit:

```text
.env.example
```

Never:

```text
.env
```

---

# 40. Development Order

This is extremely important.

Do NOT start with the UI.

Do NOT start by building all agents.

Start with one complete vertical slice.

## Vertical Slice #1

```text
Question
 ↓
Search
 ↓
Retrieve papers
 ↓
Analyze one paper
 ↓
Answer with citation
 ↓
Display in UI
```

Once this works end-to-end, expand.

---

# 41. Week 1 — Foundation

## Everyone

```text
[ ] Finalize requirements
[ ] Finalize architecture
[ ] Create GitHub repository
[ ] Setup branches
[ ] Setup project management board
[ ] Decide coding standards
[ ] Create .env.example
[ ] Setup Docker
```

## Person 1

```text
[ ] LangGraph prototype
[ ] LLM integration
[ ] Define ResearchState
[ ] Planner prototype
```

## Person 2

```text
[ ] PostgreSQL
[ ] pgvector
[ ] Database schema
[ ] Alembic
[ ] Paper model
```

## Person 3

```text
[ ] React project
[ ] Tailwind
[ ] Routing
[ ] Design system
[ ] Dashboard wireframe
```

## Person 4

```text
[ ] FastAPI
[ ] API structure
[ ] Authentication skeleton
[ ] Docker Compose
[ ] Redis
```

### Week 1 Deliverable

All four developers can run the entire project locally.

---

# 42. Week 2 — Paper Discovery

## Person 1

Build:

```text
Research Planner
Query Generator
```

## Person 2

Build:

```text
Paper ingestion
Metadata normalization
Deduplication
```

## Person 3

Build:

```text
Research creation UI
Search results UI
Paper cards
```

## Person 4

Build:

```text
Research APIs
Paper APIs
Background jobs
```

### Milestone

User enters:

```text
"LLM hallucinations"
```

System finds papers and displays them.

---

# 43. Week 3 — PDF + RAG

## Person 1

```text
[ ] Retrieval Agent
[ ] Paper Analysis prompt
```

## Person 2

```text
[ ] PDF parser
[ ] Section extraction
[ ] Chunking
[ ] Embeddings
[ ] pgvector retrieval
```

## Person 3

```text
[ ] Paper viewer
[ ] Paper detail page
[ ] Evidence UI
```

## Person 4

```text
[ ] PDF upload/download APIs
[ ] Job processing
[ ] Storage
```

### Milestone

User can ask:

> "What methodology did this paper use?"

and receive an evidence-backed answer.

---

# 44. Week 4 — Multi-Paper Analysis

Build:

```text
Paper Analyzer
Comparison Agent
```

Output:

```text
Method
Dataset
Metrics
Results
Limitations
```

Then comparison table.

### Milestone

User selects 3–5 papers and gets a structured comparison.

---

# 45. Week 5 — Research Gap Detection

Implement:

```text
Gap Detector
```

Look for:

```text
limitations
missing datasets
conflicting results
unexplored combinations
future work
```

### Milestone

Research workspace contains:

```text
Potential Research Gaps

1. ...
Evidence: Paper A, Paper B

2. ...
Evidence: Paper C

3. ...
Evidence: Paper A, Paper D
```

---

# 46. Week 6 — Verification + Report

Implement:

```text
Claim Verification
Report Generator
Citation System
```

### Milestone

Generate a complete literature review with traceable evidence.

---

# 47. Week 7 — UX + Reliability

Focus on:

```text
[ ] Error handling
[ ] Loading states
[ ] Retry logic
[ ] Empty states
[ ] Better citations
[ ] Agent progress
[ ] Authentication
[ ] Security
[ ] Rate limits
```

---

# 48. Week 8 — Evaluation

This is what separates a serious project from a demo.

Create a benchmark.

Example:

```text
20 research questions
100 papers
100 questions over papers
```

Measure:

### Retrieval

```text
Recall@K
Precision@K
MRR
```

### Generation

```text
Citation correctness
Citation completeness
Faithfulness
Answer relevance
```

### System

```text
Latency
Token usage
Cost
Failure rate
```

---

# 49. Evaluation Dataset

Create questions such as:

```text
Q1:
What dataset did Paper A use?

Q2:
What was the baseline?

Q3:
What limitation did the authors identify?

Q4:
Why did Paper A outperform Paper B?

Q5:
What evidence supports claim X?
```

Have team members manually create ground-truth answers.

Then compare ResearchOS output.

---

# 50. Hallucination Test

Create questions where the answer does NOT exist.

Example:

```text
"What accuracy did Paper A achieve on Dataset Z?"
```

if Dataset Z was never evaluated.

Correct response:

```text
"The paper does not report an evaluation on Dataset Z."
```

Incorrect:

```text
"Paper A achieved 92% accuracy."
```

This should be a major evaluation metric.

---

# 51. Security

Implement:

```text
JWT authentication
Password hashing
Input validation
File validation
File-size limits
Rate limiting
CORS configuration
SQL injection protection
Secret management
```

Never let an uploaded document execute code.

---

# 52. Agent Safety

The model should NOT have unrestricted access to the system.

Use explicit tools:

```text
search_papers()
get_paper()
retrieve_evidence()
analyze_paper()
compare_papers()
generate_report()
```

The LLM chooses tools.

The backend controls what tools can actually do.

---

# 53. Observability

Log:

```text
request_id
user_id
research_id
agent_name
tool_name
latency
tokens
model
error
```

Example:

```json
{
  "research_id": "123",
  "agent": "comparison_agent",
  "latency_ms": 3200,
  "tokens": 2400,
  "status": "success"
}
```

This helps debugging.

---

# 54. Caching

Use Redis for:

```text
Paper metadata
Search results
Repeated retrieval
Job status
Rate limiting
```

Do not repeatedly call an external API for the same paper.

---

# 55. Cost Optimization

Track:

```text
Input tokens
Output tokens
Embedding calls
Search API calls
PDF processing
```

Use cheaper models for:

```text
classification
metadata extraction
query rewriting
deduplication
```

Use stronger models for:

```text
complex comparison
gap analysis
final synthesis
```

---

# 56. Failure Handling

Every external operation can fail.

Examples:

```text
API unavailable
PDF unavailable
PDF corrupted
LLM timeout
Rate limit
Embedding failure
Database failure
```

Implement:

```text
Retry
 ↓
Exponential Backoff
 ↓
Fallback
 ↓
Record Error
 ↓
Continue if Possible
```

One broken paper should not destroy the entire research run.

---

# 57. Agent Workflow Failure

Example:

```text
Search
 ↓
No papers found
 ↓
Query expansion
 ↓
Search again
 ↓
Still nothing
 ↓
Ask user to broaden query
```

Do not make the agent loop forever.

Set:

```text
max_iterations = 3
```

---

# 58. Human-in-the-Loop

For important decisions:

```text
Agent:

"I found 42 papers.
I recommend selecting these 15."

             ↓

User

[Approve] [Modify]
```

Then:

```text
"Generate literature review?"

[Generate]
```

This is better than blindly allowing autonomous decisions.

---

# 59. Deployment

## Development

```text
Docker Compose

frontend
backend
postgres
redis
worker
```

## Production

Possible setup:

```text
Frontend
   ↓
Vercel / static hosting

Backend
   ↓
Cloud server/container platform

Database
   ↓
Managed PostgreSQL

Redis
   ↓
Managed Redis

Storage
   ↓
S3-compatible storage
```

---

# 60. CI/CD

GitHub Actions:

```text
Push
 ↓
Lint
 ↓
Type Check
 ↓
Unit Tests
 ↓
Build
 ↓
Docker Build
 ↓
Deploy
```

---

# 61. Testing Strategy

## Frontend

```text
Component tests
Integration tests
E2E tests
```

## Backend

```text
Unit tests
API tests
Database tests
```

## AI

```text
Prompt tests
Retrieval tests
Citation tests
Hallucination tests
Regression tests
```

---

# 62. Important AI Evaluation Principle

Do not say:

> "Our agent is accurate."

Without measurement.

Instead report:

```text
Retrieval Recall@5: XX%

Citation correctness: XX%

Citation completeness: XX%

Answer faithfulness: XX%

Average latency: XX sec

Average tokens/query: XX
```

The actual values must come from your experiments.

---

# 63. Final User Flow

```text
LOGIN
  ↓
DASHBOARD
  ↓
CREATE RESEARCH
  ↓
Enter research question
  ↓
Agent creates research plan
  ↓
User reviews plan
  ↓
Search papers
  ↓
User reviews selected papers
  ↓
Process papers
  ↓
Analyze
  ↓
Compare
  ↓
Detect potential gaps
  ↓
Verify evidence
  ↓
Generate report
  ↓
User reviews report
  ↓
Export
```

---

# 64. Example Complete Run

## User

```text
Research:

"How effective are LLMs for automated software testing?"
```

## Planner

```text
Subtopics:

1. Test generation
2. Test repair
3. Code coverage
4. LLM benchmarks
5. Limitations
```

## Search

```text
Found: 126 papers
```

## Deduplication

```text
126 → 91
```

## Ranking

```text
91 → 25
```

## PDF Processing

```text
25 papers
~5000 chunks
```

## Analysis

```text
25 structured analyses
```

## Comparison

```text
Methods
Datasets
Models
Metrics
Results
Limitations
```

## Gap Detection

```text
Potential Gap #1
Limited evaluation on...

Evidence:
Paper A
Paper F
Paper M
```

## Verification

```text
Claims: 34

Verified: 29
Partially verified: 3
Conflicting: 2
Unsupported: 0
```

## Final

```text
Literature Review
+
Comparison
+
Potential Research Gaps
+
References
+
Evidence
```

---

# 65. What NOT to Build Initially

Avoid these until the core system works:

```text
❌ Voice assistant
❌ Mobile application
❌ Fine-tuning your own LLM
❌ Custom foundation model
❌ 20-agent architecture
❌ Complex knowledge graph
❌ Browser automation
❌ Social features
❌ Recommendation system
❌ Fancy animations
```

The core research workflow is already large.

---

# 66. MVP Definition

The MVP is complete when this works:

```text
User enters research question
        ↓
System generates queries
        ↓
Searches academic sources
        ↓
Finds papers
        ↓
User selects papers
        ↓
System processes PDFs
        ↓
System indexes evidence
        ↓
User asks questions
        ↓
System retrieves evidence
        ↓
System answers with citations
        ↓
System compares papers
        ↓
System identifies potential gaps
        ↓
System generates report
```

If this works reliably, you already have a strong project.

---

# 67. Final Demo Script

For the college presentation, do NOT spend 10 minutes explaining the login page.

Use one impressive research question.

Example:

```text
"Compare RAG, fine-tuning and prompt engineering
for reducing hallucinations in LLMs."
```

Then demonstrate:

### 1. Planning

Show generated research plan.

### 2. Discovery

Show papers being found.

### 3. Evidence

Open a paper and show extracted evidence.

### 4. Comparison

Show the comparison matrix.

### 5. Gap Detection

Show potential research gaps with evidence.

### 6. Verification

Click a claim and show its source.

### 7. Final Report

Generate the literature review.

### 8. Evaluation

Show your benchmark results.

---

# 68. College Report Structure

Your final project report can contain:

```text
1. Abstract

2. Introduction

3. Problem Statement

4. Existing Systems

5. Proposed System

6. System Architecture

7. Technology Stack

8. Database Design

9. Agent Architecture

10. RAG Architecture

11. Implementation

12. Algorithms

13. Evaluation

14. Results

15. Limitations

16. Future Scope

17. Conclusion

18. References
```

---

# 69. Viva Questions You Should Prepare

Expect questions such as:

### Why use agents?

Explain the difference between:

```text
LLM
RAG
Workflow
Agent
Multi-agent system
```

### Why LangGraph?

Explain:

```text
State
Nodes
Edges
Conditional routing
Cycles
Human-in-the-loop
```

### Why pgvector?

Explain:

```text
Embeddings
Vector similarity
ANN search
Metadata filtering
```

### Why hybrid search?

Explain the difference between:

```text
Semantic similarity
Keyword matching
Reranking
```

### How do you prevent hallucination?

Explain:

```text
Evidence retrieval
Citation mapping
Verification
Unsupported-claim detection
```

### How do you evaluate the system?

Explain:

```text
Retrieval metrics
Faithfulness
Citation correctness
Latency
Cost
```

---

# 70. Definition of Done

A feature is not finished merely because the code runs.

Every feature must have:

```text
Implementation
+
Tests
+
Error handling
+
Logging
+
Documentation
+
UI integration
```

---

# 71. Team Operating Rules

## Daily

15-minute meeting:

```text
What did I complete?
What am I doing today?
What is blocking me?
```

## Weekly

One complete demo every week.

Never say:

> "We'll integrate everything at the end."

Integration should happen continuously.

---

# 72. Weekly Milestone Checklist

```text
Week 1  → Infrastructure
Week 2  → Paper Discovery
Week 3  → PDF + RAG
Week 4  → Paper Analysis
Week 5  → Comparison + Gaps
Week 6  → Verification + Reports
Week 7  → UX + Reliability
Week 8  → Evaluation + Deployment
```

---

# 73. First 48 Hours

This is where you should start.

## Day 1

### All four

```text
[ ] Create GitHub repository
[ ] Create Discord/WhatsApp project channel
[ ] Create project board
[ ] Finalize stack
[ ] Create architecture diagram
[ ] Define MVP
[ ] Assign ownership
```

### Person 1

```text
Create basic LangGraph:

START
 ↓
Planner
 ↓
END
```

### Person 2

```text
Create PostgreSQL + pgvector.

Create:
users
research_projects
papers
paper_chunks
```

### Person 3

```text
Create React application.

Build:
Login
Dashboard
New Research
```

### Person 4

```text
Create FastAPI.

Build:

GET /health

POST /auth/register
POST /auth/login

POST /research
GET /research
```

---

# 74. Day 2

Connect everything.

```text
React
  ↓
FastAPI
  ↓
PostgreSQL
```

Then:

```text
FastAPI
  ↓
LangGraph
  ↓
LLM
```

Then:

```text
LangGraph
  ↓
Paper Search API
  ↓
PostgreSQL
```

At the end of Day 2, the system should have a primitive end-to-end flow.

---

# 75. The Golden Rule

Build vertically, not horizontally.

Bad:

```text
Month 1:
Build entire frontend

Month 2:
Build backend

Month 3:
Build AI

Month 4:
Try to integrate
```

Good:

```text
Week 1:
Frontend → Backend → AI → Database

Week 2:
Frontend → Backend → Search → Database

Week 3:
Frontend → Backend → PDF → RAG

Week 4:
Frontend → Backend → Analysis → Report
```

Every week produces something demonstrable.

---

# 76. Final Architecture

```text
                           ┌──────────────┐
                           │     USER     │
                           └──────┬───────┘
                                  │
                                  ↓
                       ┌─────────────────────┐
                       │   React + TypeScript│
                       └──────────┬──────────┘
                                  │
                                  ↓
                         ┌────────────────┐
                         │    FastAPI     │
                         └───────┬────────┘
                                 │
                  ┌──────────────┼──────────────┐
                  │              │              │
                  ↓              ↓              ↓
             PostgreSQL       Redis         Workers
                  │                             │
                  │                             ↓
                  │                       ┌───────────┐
                  │                       │ LangGraph │
                  │                       └─────┬─────┘
                  │                             │
                  │              ┌──────────────┼──────────────┐
                  │              │              │              │
                  │              ↓              ↓              ↓
                  │          Planner          Search        Analysis
                  │              │              │              │
                  │              │              ↓              ↓
                  │              │       Academic APIs    LLM + RAG
                  │              │                             │
                  │              └──────────────┬──────────────┘
                  │                             ↓
                  │                       Comparison
                  │                             │
                  │                             ↓
                  │                       Gap Detection
                  │                             │
                  │                             ↓
                  │                       Verification
                  │                             │
                  │                             ↓
                  │                       Report Agent
                  │                             │
                  └─────────────────────────────┘
                                  │
                                  ↓
                           Evidence-backed
                               Report
```

---

# 77. Final Target

The final project should feel like:

> **"Perplexity + NotebookLM + an autonomous research workflow"**

but the real value should come from your engineering:

```text
Search
+
Retrieval
+
Agents
+
Evidence
+
Verification
+
Evaluation
+
Good UX
```

That is the project.

Do not chase the number of agents. Build a system where every component has a clear purpose and can be measured.
