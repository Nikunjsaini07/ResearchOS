"""Run browser checks against a disposable database, never the user's workspace."""
import os
assert os.environ.get("RESEARCHOS_E2E_DIR"), "Start through Playwright for isolated storage."
import uvicorn
from backend.main import app
server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8766))

# Only this disposable test runner installs the shutdown route.
@app.post("/__test_shutdown")
def shutdown():
    server.should_exit = True
    return {"ok": True}

server.run()
