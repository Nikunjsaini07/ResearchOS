# ResearchOS

Ask a research question, find papers, read their evidence, and build a sourced answer.
The browser uses **React + TypeScript**; the server uses **Python + FastAPI**.

## Start here

Read these files in order. You do not need to understand every file at once.

| File | What to learn |
| --- | --- |
| `src/main.tsx` | How React starts and loads the styles |
| `src/App.tsx` | The screens, state, button handlers, and research progress |
| `src/api.ts` | How the browser sends requests to Python |
| `src/types.ts` | The shapes of projects, papers, jobs, and evidence |
| `backend/main.py` | How API routes handle requests and queue research jobs |
| `backend/research.py` | How papers become searchable passages and sourced answers |
| `backend/db.py` | How accounts, projects, papers, and jobs are stored |

## Project map

```text
src/          Browser code: application, API helper, types, and styles
backend/      Python API, research pipeline, database, and optional cache
public/       Images and favicon actually used by the app
docs/         Detailed setup and reference material
```

`src/styles.css` controls the appearance. `backend/cache.py` is an optional Redis
helper; skip it on your first read. The root configuration files support builds
and Docker.

## Run locally (Windows)

If the project is already installed, start the API:

```powershell
.\.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In a second terminal, start the frontend:

```powershell
npm.cmd run dev
```

Open http://127.0.0.1:5173. For a fresh installation and provider settings, see
[Setup and reference](docs/setup-and-reference.md).

## Follow one question through the code

1. In `src/App.tsx`, find `begin`: it creates a project, uploads an optional PDF,
   and requests a research job using `api` from `src/api.ts`.
2. In `backend/main.py`, find `run`: it queues the job. The `worker` function
   picks it up and runs the matching workflow.
3. In `backend/research.py`, start at `auto_plan` and follow `auto_discover`,
   `auto_index`, `auto_analyze`, and `auto_report`.
4. Back in `src/App.tsx`, `load` fetches the results. A `useEffect` polls while
   research is running, and React displays the updated state.

Try a small change first: edit one of the suggested questions in `prompts` in
`src/App.tsx`. Then follow the submit handler before exploring the research pipeline.

## Why some folders are hidden

VS Code hides installed dependencies (`node_modules`, `.venv`), generated builds,
Python caches, test output, and local data through `.vscode/settings.json`.
They still exist and work normally. Change `files.exclude` there to show them.
Your `.env`, database, uploaded PDFs, and existing design edits are preserved.

Old design references are kept in `docs/reference/`, also hidden from the editor's
normal file tree. They are not needed to run or understand the current app.
