# ResearchOS

**ResearchOS turns a research question into a small, inspectable literature review.** It finds relevant academic papers or uses PDFs you upload, reads their text, and writes a sourced answer. You can open the passages behind a claim, ask follow-up questions, and download the review as Markdown.

[Try the live app](https://researchos-b9ap.onrender.com/) · [Read the detailed workflow and RAG guide](docs/researchos-rag-explained.md)

## What it does

Start with a question such as *“How do neural networks classify images?”* and optionally attach a PDF. ResearchOS then:

1. **Plans searches.** Python rules turn meaningful words in the question into up to three search queries. This stage does **not** use an LLM.
2. **Finds papers.** It searches arXiv, removes duplicates, ranks title and abstract relevance, and automatically selects up to six papers. If you attached a PDF, the run uses the uploaded corpus instead.
3. **Reads sources.** It extracts text from the selected PDFs, divides it into page-linked passages, and optionally creates embedding vectors for later retrieval. If an arXiv PDF is unavailable, its abstract may be used and is labeled as such.
4. **Writes an answer and suggests next questions.** It sends relevant passages with your *full original question* to the configured LLM for a direct answer and supporting points. A separate call inspects limitations and conclusions to suggest up to three source-backed research directions, each with a practical next step.
5. **Builds a review.** It assembles the answer, findings, search method, limitations, and references into a downloadable Markdown report. This formatting step does not make another LLM call.

The progress trail on the page corresponds to these five steps. Projects, papers, passages, job progress, and reports are stored so you can return to a workspace. Guest access is created automatically; you can also create an account.

## Where RAG fits

**Retrieval-Augmented Generation (RAG)** means finding relevant material outside the model, adding that material to the prompt, and then generating an answer. Here, the material is extracted passages from the selected papers. The papers are **not used to train or fine-tune** the LLM.

ResearchOS currently has two retrieval paths:

- **Initial report:** it selects an abstract and up to one other passage per paper using question-word overlap and section cues. Those excerpts are given to the LLM to produce the first answer. Embeddings may be stored, but vector similarity is **not** used to choose these initial excerpts.
- **Follow-up chat:** it searches the indexed passages for the new question. When embeddings are available, the ranking combines keyword overlap (55%) and semantic similarity (45%); otherwise it uses keywords. The retrieved passages become context for the follow-up LLM answer.

Source links make the output inspectable, but they do not automatically prove that an interpretation is correct. Claims begin marked as needing review. [The RAG guide](docs/researchos-rag-explained.md) explains indexing, retrieval, prompts, citations, and these limits in more depth.

## Technology

| Part | Used for |
| --- | --- |
| **React + TypeScript + Vite** | Responsive question composer, research workspace, source views, and progress display. |
| **Python + FastAPI + Uvicorn** | Same-origin API, session handling, uploads, queued research jobs, and follow-up chat. |
| **LangGraph** | Runs the fixed `plan → discover → index → analyze → report` workflow. |
| **HTTPX + arXiv API** | Academic search and PDF downloads; DataCite is a fallback for arXiv records. |
| **pypdf** | Extracts PDF text into page-linked passages. |
| **SQLAlchemy + PostgreSQL/SQLite** | Stores users, projects, papers, passages, vectors, jobs, reports, and messages. SQLite is the local default. |
| **pgvector** | Vector similarity search on PostgreSQL when embeddings are configured. |
| **Supabase Storage or local files** | Stores PDF bytes separately from database records. |
| **OpenAI-compatible APIs** | Configurable LLM for answers and optional embedding model for semantic retrieval. |
| **Docker** | Builds the frontend and runs the API; the deployed app uses Render. Redis can optionally cache searches. |

The browser calls `/api` on the same site. Provider credentials stay on the server, and the browser session uses an HTTP-only cookie.

## Run locally on Windows

From the repository root:

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.lock.txt
npm ci
```

Start the API in one terminal:

```powershell
.\.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Start the frontend in another:

```powershell
npm run dev
```

Open **http://127.0.0.1:5173**. Vite forwards `/api` requests to the Python server. To serve the built frontend through FastAPI, run `npm run build` before starting the API, then open **http://127.0.0.1:8000**.

The example `.env` uses SQLite and local PDF files. Paper search, uploads, and keyword retrieval can run without an AI key; a synthesized answer requires `LLM_API_KEY`. Embeddings additionally require an enabled embedding provider. Do not commit `.env` or put provider keys in frontend code. For server setup, see [configuration and Docker](docs/setup-and-reference.md) or [Supabase setup](docs/supabase-setup.md).

## Code map

| File | Role |
| --- | --- |
| `src/App.tsx` | Screens, submit handler, progress polling, answer and source views. |
| `src/api.ts` | Browser requests to the backend. |
| `backend/main.py` | API routes, auth, job worker, uploads, and chat. |
| `backend/research.py` | Query rules, paper discovery, PDF chunking, retrieval, LLM synthesis, and reports. |
| `backend/db.py` | Database schema, including passages and optional vectors. |
| `backend/storage.py` | Private Supabase or local PDF storage. |
| `backend/cache.py` | Optional Redis search cache. |

To follow one question through the code, start at `begin` in `src/App.tsx`, then `run` and `worker` in `backend/main.py`, then the `auto_*` stages in `backend/research.py`.

## Current limits

- This is a **focused review**, not an exhaustive systematic search. Automatic discovery starts with arXiv and selects at most six papers; users can adjust the selection, up to 20 per run.
- The first answer sees sampled excerpts, not entire PDFs. It can miss a relevant result elsewhere in a paper.
- Scanned PDFs need OCR before text can be extracted. Uploads are limited to 25 MB and 300 pages.
- A linked passage supports inspection, not automatic scientific verification. Check important claims in the original paper.
- Research directions are suggestions grounded in quoted passages from this small corpus. They are not proof that a topic is unstudied; inspect the cited papers and search more widely before treating one as a gap.
- External search and AI providers may be unavailable or rate-limit requests. An interrupted server-side job can be retried.
