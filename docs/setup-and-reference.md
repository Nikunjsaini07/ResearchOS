# ResearchOS

A working research workspace built with React, TypeScript, FastAPI, SQLAlchemy, and LangGraph. Discover academic papers, select a corpus, index PDF passages, inspect evidence, ask follow-up questions, and export a sourced review.

## Quick start (Windows)

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.lock.txt
npm ci
npm run build
.\.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 and ask a research question. A private guest workspace is created automatically; no sign-in is required. The backend serves the built frontend from the same origin.

For frontend development, run `npm run dev` in another terminal. Vite proxies `/api` to port 8000. Use the same hostname consistently; localhost and 127.0.0.1 have separate cookies.

## Required credentials

No credentials are needed for guest workspaces, projects, arXiv discovery, uploads, keyword evidence retrieval, PDF reading, or local persistence.

To enable AI-authored summaries and synthesized follow-up answers, set these values in `.env` and restart the backend:

```dotenv
LLM_API_KEY=your-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4.1-mini
EMBEDDING_MODEL=text-embedding-3-small
```

An OpenAI-compatible provider must support chat completions with JSON-object output. Embeddings use an OpenAI-compatible embeddings endpoint. A separate embedding key/base URL can be supplied. Failed embeddings fall back to keyword retrieval. No provider keys are stored in browser storage or returned by the API.

## Workflow

The UI has two main screens: an illustrated question composer and a live research workspace.

1. Type a question on the home page; optionally attach a PDF.
2. Click **Let's explore**. A private guest workspace is created automatically; no login wall.
3. Watch the horizontal trail: plan, find papers, read and collect, connect ideas, answer.
4. Without an attached PDF, the pipeline discovers papers and selects up to six relevant results. With an upload, it uses that supplied corpus.
5. Read the answer and open numbered citations to inspect the original page-level passages.
6. Inspect Sources, compare available findings, and ask follow-up questions within the same page. Download the report from the header icon. The Research gaps tab currently has no automatically generated gap claims.
7. Continue from the same research page; the current browser session keeps the workspace available.

The automatic run generates search terms with Python rules, then normally makes one chat-completion request to draft a direct answer and supporting points from sampled passages. Optional embeddings make separate batched requests. The initial answer maps returned source IDs to stored passages, but that mapping does not verify the scientific interpretation. The final Markdown report formats the saved analysis without another LLM request. If AI synthesis fails or is not configured, the app reports that limitation and keeps the source evidence available instead of fabricating a conclusion.

## Architecture

- `src/App.tsx`: application UI, illustrated composer, live horizontal progress trail, cited answers, and evidence dialogs.
- `src/styles.css`: responsive design system, locally bundled Inter and Manrope fonts, print styles.
- `backend/main.py`: authenticated API, session cookies, durable job dispatch, worker, upload/download and reports.
- `backend/research.py`: LangGraph steps, arXiv search, PDF ingestion, retrieval, provider adapters, evidence validation.
- `backend/db.py`: SQLAlchemy schema. SQLite for zero-service local development; PostgreSQL with native pgvector storage/distance queries supported through DATABASE_URL. Redis optionally caches academic searches for one hour; cache failure never blocks research.

Research steps are durable database jobs. A single worker executes them outside HTTP requests. Completed events are polled by the UI; interrupted jobs are marked failed on restart and can be retried. Run **one API process** with this MVP worker; multiple workers require a separate queue/lease architecture. The initial run proceeds automatically. Afterwards, edit queries to discover more papers, adjust the source selection, and choose **Analyze selected papers** to rebuild without overwriting your selection.

## Docker

```powershell
Copy-Item .env.example .env
# Fill provider settings if desired, then:
docker compose up --build
```

The app runs at http://localhost:8000. Database and PDFs use named volumes. PostgreSQL and Redis are internal services. The sample database password is for local development; replace it before hosting. Set COOKIE_SECURE=true behind HTTPS and explicitly configure ALLOWED_ORIGINS for the deployment origin. Do not expose this development configuration directly to the internet.

The lockfile records the verified dependency versions; requirements.txt records the intended version ranges.

## Free-only OpenRouter setup

Put your key in the local `.env` (ignored by Git), then configure:

```dotenv
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openrouter/free
LLM_FREE_ONLY=true
EMBEDDINGS_ENABLED=false
```

Restart the API after changes. Free-only mode rejects paid model IDs and disables all embedding API calls. Retrieval uses local keyword matching. When `LLM_MODEL=openrouter/free`, the app reads OpenRouter's current free model catalog and tries compatible JSON-output models in sequence. If the catalog is unavailable, it retries the free router. You can set an explicit `:free` model to use only that model. Free-model availability, latency, and quotas vary; failures are shown in the answer and never trigger a paid fallback.

Automatic research searches the question, selects up to six relevant arXiv papers, and produces one direct AI summary with links to the passages it used. It reads PDF text when available and falls back to the paper abstract when a PDF cannot be downloaded. An abstract-only source is labeled as such, and an AI failure is shown as an error rather than as a stack of source excerpts.

The **Compare** tab shows available findings and marks missing comparisons; how much it can compare depends on the sourced answer. After reviewing a finding, choose **Generate report** to refresh the downloadable Markdown. Sources supports additional PDF uploads and selection of up to 20 papers. Research deletion requires confirmation.

## Practical limits

- arXiv is the initial discovery source. Other PDFs can be uploaded manually. Restricted/paywalled content is not bypassed.
- PDFs must contain extractable text; OCR is not included. Uploads are limited to 25 MB / 300 pages.
- Runs support up to 20 selected papers. The initial answer samples at most two passages per paper and sends up to 700 characters from each to the LLM. Tables and equations can be damaged by PDF extraction. Read the original PDF when checking claims.
- The initial answer maps source IDs to real stored passages; follow-up chat additionally requires quoted text to occur in a retrieved passage. Neither check proves a claim is scientifically correct. Findings begin marked **needs review**. Use **Review finding** to record supported, partially supported, unsupported, or conflicting judgments. Unsupported findings are excluded from regenerated reports.
- The Research gaps tab exists, but the current automatic analysis does not generate gap claims.
- The report is a structured synthesis of sourced findings, not an autonomous systematic review.
- The local SQLite mode computes vector similarity in-process. PostgreSQL uses pgvector exact distance queries; approximate-nearest-neighbor indexing and corpus pagination are future scale work.
- Email verification, password reset, collaborative teams, scientific benchmark results, and large-scale retrieval tuning are not included.
- Provider calls send selected document passages to your configured provider. Use a provider appropriate for your document permissions.

## API reference

FastAPI's interactive API documentation is available at `/docs`. Main routes live under `/api` and use HTTP-only session cookies. See `.env.example` for all environment variables.

Implementation references: [FastAPI file uploads](https://fastapi.tiangolo.com/tutorial/request-files/), [arXiv API](https://info.arxiv.org/help/api/user-manual.html).
