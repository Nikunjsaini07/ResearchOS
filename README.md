# ResearchOS · Research Paper RAG Assistant

**ResearchOS turns any academic research paper into an interactive, grounded Q&A workspace.** Upload a PDF or explore landmark papers in 1-click. ResearchOS parses the document into structured page & section chunks, performs hybrid RAG retrieval, and generates answers with verifiable citations.

---

## Key Highlights

- **Simple, Direct Flow:** No sign-ins, no 5-step hurdles. Drop a PDF or click an iconic paper (*Attention Is All You Need*, *LoRA*) to begin immediately.
- **Section-Aware Extraction:** Breaks papers down by actual academic sections (*Abstract*, *Methods*, *Experiments*, *Results*, *Limitations*) tagged with exact page numbers.
- **Grounded Answers:** Answers are synthesized directly from retrieved passages, complete with expandable source drawers showing verbatim excerpts and relevance scores.
- **Dual-Pane Workspace:** Document summary, extraction statistics, and 1-click suggested questions on the left; conversational streaming chat on the right.
- **Ultra-Responsive:** Adapts seamlessly across mobile, tablet, and widescreen desktop layouts.

---

## Architecture & Tech Stack

| Layer | Technologies | Purpose |
|---|---|---|
| **Frontend** | React 18, TypeScript, Vite | Fluid UI, dual-pane layout, markdown rendering, responsive CSS |
| **Backend API** | FastAPI, Uvicorn, Python 3.12 | REST API, PDF processing, session management |
| **Database** | SQLAlchemy 2.0, SQLite | Persistence for papers, chunks, and conversation history |
| **PDF Extraction** | pypdf | Text extraction, page boundary mapping, section header detection |
| **RAG Retrieval** | Hybrid BM25 & Lexical overlap | Section-prioritized search over indexed document chunks |
| **LLM Synthesis** | OpenRouter API | Grounded question answering with inline page/section citations |

For an in-depth breakdown of algorithms, mathematical scoring formulas, database schemas, and endpoints, see [DOCUMENTATION.md](DOCUMENTATION.md).

---

## Quick Start (Local Run)

### 1. Configure Environment
```bash
cp .env.example .env
```
Ensure your `.env` contains:
```ini
DATABASE_URL=sqlite:///./data/researchos.db
LLM_API_KEY=your_openrouter_key_here
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openrouter/free
```

### 2. Backend Setup
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r backend/requirements.lock.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Frontend Setup
```powershell
npm install
npm run dev
```

Open **[http://127.0.0.1:5173](http://127.0.0.1:5173)** in your browser.

---

## API Summary

- `GET /api/rag/status?pid={projectId}`: Check workspace status, page counts, and suggested questions.
- `POST /api/rag/upload`: Upload and index a PDF file (multipart form data).
- `POST /api/rag/sample`: Ingest a 1-click sample paper (`attention` or `lora`).
- `POST /api/rag/ask`: Query the paper and receive a grounded answer with citations.
- `POST /api/rag/reset`: Reset the workspace and start fresh.

---

## Documentation

- Full system architecture, database schema, and scoring logic: **[DOCUMENTATION.md](DOCUMENTATION.md)**
