# ResearchOS · Architecture & Technical Documentation

> **Research Paper RAG Assistant**  
> Simple, grounded question answering for academic papers: **PDF $\rightarrow$ Extraction $\rightarrow$ Hybrid RAG $\rightarrow$ Grounded Citations**.

---

## 1. Overview & System Purpose

**ResearchOS** is a specialized Retrieval-Augmented Generation (RAG) assistant designed for researchers, engineers, and students. Instead of uploading PDFs to a general-purpose chatbot that hallucinates citations, ResearchOS provides an inspectable, grounded environment where:
1. An academic PDF is ingested, segmented, and indexed locally into structured page-and-section chunks.
2. Questions are answered strictly using retrieved passages from the paper.
3. Every response contains **expandable verbatim citations** indicating the exact page number, section heading, and relevant source passage.
4. Zero authentication barriers or complex setup—users can drag-and-drop any PDF or test immediately with 1-click landmark papers (*Attention Is All You Need*, *LoRA*).

---

## 2. Technical Stack

### Frontend Architecture
- **Framework:** [React 18](https://react.dev/) with [TypeScript](https://www.typescriptlang.org/)
- **Bundler & Dev Server:** [Vite 6](https://vitejs.dev/) with Hot Module Replacement (HMR)
- **Styling:** Custom CSS with Glassmorphism, CSS Grid, Flexbox, and `clamp()` fluid typography. Zero heavy UI dependencies (no Tailwind, MUI, or Bootstrap) to maintain fast load times (<450ms).
- **Icons:** [Lucide React](https://lucide.dev/) (feather-style SVG icons)
- **Markdown & Code Rendering:** [ReactMarkdown](https://github.com/remarkjs/react-markdown) + [remark-gfm](https://github.com/remarkjs/remark-gfm) (GitHub Flavored Markdown for tables, lists, and formatted code blocks)

### Backend Architecture
- **Language & Runtime:** Python 3.12
- **Web Framework:** [FastAPI](https://fastapi.tiangolo.com/) with [Uvicorn](https://www.uvicorn.org/) ASGI server
- **Database ORM:** [SQLAlchemy 2.0](https://www.sqlalchemy.org/)
- **Database Engine:** SQLite (`sqlite:///./data/researchos.db`) for low-latency local persistence; fully compatible with PostgreSQL.
- **PDF Extraction Engine:** [pypdf](https://pypdf.readthedocs.io/) with custom section-boundary regex parsing.
- **LLM Synthesis Provider:** [OpenRouter API](https://openrouter.ai/) (supporting high-performance free models such as Gemma, LLaMA, and Nemotron with automatic fallbacks).
- **Networking:** [HTTPX](https://www.python-httpx.org/) for asynchronous and resilient outbound HTTP requests.

---

## 3. System Architecture & End-to-End Workflow

```
┌────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                  │
│                                                                        │
│  [ Upload PDF / Pick Sample ] ───► [ Dual-Pane Workspace ]             │
│                                       ├─ Left: Abstract & Suggestions  │
│                                       └─ Right: Chat & Cited Sources   │
└─────────────────────────────────┬──────────────────────────────────────┘
                                  │ HTTP / Multipart
                                  ▼
┌────────────────────────────────────────────────────────────────────────┐
│                              BACKEND                                   │
│                                                                        │
│   FastAPI API Router (backend/main.py)                                 │
│        │                                                               │
│        ├── 1. Ingestion & Extraction (backend/rag_engine.py)           │
│        │      • pypdf page extraction                                  │
│        │      • Regex academic section boundary detection              │
│        │      • Chunking with page & section metadata                  │
│        │                                                               │
│        ├── 2. Storage & Persistence (backend/db.py)                    │
│        │      • SQLite Database                                        │
│        │      • Tables: projects, papers, chunks, messages             │
│        │                                                               │
│        ├── 3. Hybrid Retrieval Engine (search_chunks)                   │
│        │      • Query normalization & stop-word filtration             │
│        │      • Term-frequency overlap + log-length dampening          │
│        │      • Section-priority boosts (Abstract, Methods: 1.3x)      │
│        │      • Exact-phrase matching bonus (1.5x)                     │
│        │                                                               │
│        └── 4. Grounded Synthesis (build_rag_answer)                    │
│               • Structured prompt with [SOURCE X | Page Y, Section Z]  │
│               • OpenRouter LLM generation                              │
│               • Verbatim snippet extraction & score calculation        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Detailed Component Breakdown

### A. Document Parsing & Section Chunking
When a PDF is received via `POST /api/rag/upload`:
1. **Validation:** Checks magic bytes (`%PDF-`) and file size limit ($\le 25\text{ MB}$, $\le 300\text{ pages}$).
2. **Page-by-Page Extraction:** Iterates over all pages using `pypdf.PdfReader`.
3. **Section Boundary Detection:** Uses regular expressions matching standard academic headings:
   ```regex
   ^(?:\d+(?:\.\d+)*[.\s]+)?(abstract|introduction|related work|background|method(?:ology|s)?|experiments?|results?|discussion|limitations?|conclusions?|references|future work)\s*$
   ```
4. **Length-Bounded Buffering:** Groups lines into chunks of $1400 - 1800$ characters without splitting mid-sentence, preserving exact `page` number and `section` name.
5. **Persistence:** Saves entries into the `papers` and `chunks` SQLite tables.

### B. Hybrid RAG Retrieval (`search_chunks`)
When a user submits a question via `POST /api/rag/ask`:
1. **Tokenization:** Converts the query into normalized tokens, eliminating common conversational filler (`"please"`, `"tell me"`, `"what is"`, etc.).
2. **Lexical Scoring:** Computes token overlap frequency between the query and each indexed chunk:
   $$\text{Score} = \frac{\sum_{t \in Q} \min(\text{count}_Q(t), \text{count}_C(t))}{1.0 + \ln(\max(10, \text{length}(C)))}$$
3. **Domain Boosters:**
   - **Section Priority:** Chunks under `Abstract`, `Method`, `Architecture`, `Results`, or `Conclusion` receive a **$1.3\times$** multiplier.
   - **Exact Phrase:** Queries appearing verbatim in the text receive a **$1.5\times$** multiplier.
4. **Selection:** Returns the top $K=5$ highest-scoring chunks with page and section tags.

### C. Grounded Answer Synthesis (`build_rag_answer`)
1. **Context Formatting:** The retrieved chunks are formatted into explicit source blocks:
   ```text
   --- [SOURCE 1 | Page 4, Section: 3.2 Attention: Scaled Dot-Product Attention] ---
   An attention function can be described as mapping a query and a set of key-value pairs...
   ```
2. **System Prompt Enforcement:** Instructs the LLM to act strictly as a grounded research scientist:
   - Answer directly using only the supplied context.
   - Cite page numbers and sections inline (e.g., `**[Page 4, Section 3.2]**`).
   - Clearly state when a topic is unmentioned rather than hallucinating external facts.
3. **Response Payload:** The backend returns both the markdown answer text and a structured array of citations containing `page`, `section`, `snippet`, and `score`.

---

## 5. API Reference

### 1. Document & Workspace Status
- **`GET /api/rag/status?pid={projectId}`**
  - **Description:** Returns the active paper status, chunk counts, page counts, and suggested questions for a workspace.
  - **Response:**
    ```json
    {
      "has_paper": true,
      "paper": {
        "id": "c1f9b3...",
        "title": "Attention Is All You Need",
        "authors": "Ashish Vaswani et al.",
        "year": 2017,
        "abstract": "The dominant sequence transduction models..."
      },
      "chunks_count": 9,
      "pages_count": 9,
      "suggested_questions": [
        "What is the mathematical formula for Scaled Dot-Product Attention?",
        "How does Multi-Head Attention differ from single-head attention?"
      ]
    }
    ```

### 2. PDF Upload & Parsing
- **`POST /api/rag/upload`**
  - **Content-Type:** `multipart/form-data`
  - **Parameters:**
    - `pid` (string): Project/Workspace ID.
    - `file` (binary): PDF research paper file.
  - **Response:**
    ```json
    {
      "status": "ok",
      "title": "LoRA: Low-Rank Adaptation of Large Language Models",
      "chunks_count": 8,
      "pages_count": 8,
      "suggested_questions": [...]
    }
    ```

### 3. One-Click Sample Paper Ingestion
- **`POST /api/rag/sample`**
  - **Payload:** `{"pid": "proj_123", "sample": "attention" | "lora"}`
  - **Description:** Instantly populates the database with real excerpts from landmark papers for immediate testing without uploading files.

### 4. Grounded Question Answering
- **`POST /api/rag/ask`**
  - **Payload:** `{"pid": "proj_123", "question": "What is the formula for Multi-Head Attention?"}`
  - **Response:**
    ```json
    {
      "answer": "Multi-Head Attention is formulated as MultiHead(Q, K, V) = Concat(head_1, ..., head_h) W^O...",
      "citations": [
        {
          "chunk_id": "chk-5",
          "page": 5,
          "section": "3.2.2 Multi-Head Attention",
          "snippet": "MultiHead(Q, K, V) = Concat(head_1, ..., head_h) W^O where head_i = Attention(Q W_i^Q, K W_i^K, V W_i^V)...",
          "score": 0.94
        }
      ]
    }
    ```

### 5. Reset Workspace
- **`POST /api/rag/reset`**
  - **Payload:** `{"pid": "proj_123"}`
  - **Description:** Purges active papers, chunks, and message history for the given workspace, returning to the clean upload view.

---

## 6. Database Schema (SQLite / SQLAlchemy)

The database models are defined in [`backend/db.py`](file:///f:/Raglearn/backend/db.py):

| Table | Column | Type | Description |
|---|---|---|---|
| **`projects`** | `id` | `VARCHAR(32)` (PK) | Unique workspace session identifier |
| | `title` | `VARCHAR(200)` | Session label |
| | `status` | `VARCHAR(30)` | Current workspace state |
| **`papers`** | `id` | `VARCHAR(32)` (PK) | Unique paper identifier |
| | `project_id`| `VARCHAR(32)` (FK) | References `projects.id` |
| | `title` | `TEXT` | Paper title |
| | `authors` | `TEXT` | Extracted author list |
| | `year` | `INTEGER` | Publication year |
| | `abstract`| `TEXT` | Abstract or summary snippet |
| | `selected`| `BOOLEAN` | Active paper flag for RAG retrieval |
| **`chunks`** | `id` | `VARCHAR(32)` (PK) | Unique chunk identifier |
| | `paper_id`| `VARCHAR(32)` (FK) | References `papers.id` |
| | `page` | `INTEGER` | 1-indexed PDF page number |
| | `section` | `VARCHAR(100)` | Section heading (e.g. "3.2 Attention") |
| | `text` | `TEXT` | Verbatim text content of chunk |
| **`messages`** | `id` | `VARCHAR(32)` (PK) | Unique message identifier |
| | `project_id`| `VARCHAR(32)` (FK) | References `projects.id` |
| | `role` | `VARCHAR(20)` | `"user"` or `"assistant"` |
| | `content` | `TEXT` | Markdown text content |
| | `evidence`| `JSON` | Stored citation objects (page, section, snippet) |

---

## 7. Local Development & Deployment Guide

### Prerequisites
- Python 3.11+
- Node.js 18+ & npm
- Valid OpenRouter API Key (optional for basic search, required for LLM synthesis)

### Step 1: Clone & Configure
```bash
# Clone the repository
git clone https://github.com/Nikunjsaini07/ResearchOS.git
cd ResearchOS

# Create environment configuration
cp .env.example .env
```
Ensure your `.env` contains:
```ini
DATABASE_URL=sqlite:///./data/researchos.db
LLM_API_KEY=your_openrouter_api_key_here
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openrouter/free
```

### Step 2: Backend Setup
```bash
# Set up virtual environment
python -m venv .venv

# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.lock.txt

# Start backend server
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Step 3: Frontend Setup
```bash
# In a separate terminal:
npm install
npm run dev
```

Open **`http://127.0.0.1:5173`** in your browser.

---

## 8. Key Design Decisions

1. **Section-Aware Chunking over Fixed Token Windows:** Traditional RAG splits text strictly every 500 tokens, which cuts equations and paragraphs in half. ResearchOS groups lines under detected section headings, preserving the logical flow of academic arguments.
2. **Inspectable Verbatim Citations:** The LLM does not merely claim a page number; the system attaches the exact retrieved passage and relevance score in an expandable drawer, allowing the reader to verify findings directly.
3. **Zero Friction Onboarding:** Built-in samples (*Attention Is All You Need*, *LoRA*) enable one-click testing without requiring immediate file uploads.
