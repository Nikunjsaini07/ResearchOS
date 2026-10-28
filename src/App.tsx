import React, { useState, useEffect } from "react";
import { Leaf, Sparkles, Loader2, AlertCircle, X, Plus } from "lucide-react";
import { RagWorkspace } from "./RagWorkspace";

function Brand() {
  return (
    <span className="brand">
      <span className="brand-icon">
        <Leaf size={20} />
      </span>
      research<span>os</span>
      <i />
    </span>
  );
}

export default function App() {
  const [projectId, setProjectId] = useState<string>("");
  const [error, setError] = useState("");

  const getOrCreateProjectId = () => {
    let id = localStorage.getItem("researchos_rag_pid");
    if (!id) {
      id = "proj_" + Math.random().toString(36).substring(2, 10);
      localStorage.setItem("researchos_rag_pid", id);
    }
    return id;
  };

  useEffect(() => {
    setProjectId(getOrCreateProjectId());
  }, []);

  const handleResetSession = () => {
    const newId = "proj_" + Math.random().toString(36).substring(2, 10);
    localStorage.setItem("researchos_rag_pid", newId);
    setProjectId(newId);
  };

  return (
    <div className="app rag-app-view">
      <div className="world" aria-hidden="true" />
      <header className="site-header">
        <div className="site-header-left">
          <button
            className="brand-button"
            onClick={handleResetSession}
            aria-label="ResearchOS home"
          >
            <Brand />
          </button>
          <span className="header-tag-pill">
            <Sparkles size={13} />
            <span>Research Paper RAG</span>
          </span>
        </div>

        <nav className="site-header-right">
          <button
            className="nav-button new-analysis-btn"
            onClick={handleResetSession}
            title="Start new research session"
          >
            <Plus size={14} />
            <span>New Session</span>
          </button>
          <span className="status-indicator-pill">
            <span className="status-dot-pulse" />
            <span>AI Ready</span>
          </span>
        </nav>
      </header>

      {error && (
        <div className="error" role="alert">
          <AlertCircle size={18} />
          <span>{error}</span>
          <button aria-label="Dismiss error" onClick={() => setError("")}>
            <X size={17} />
          </button>
        </div>
      )}

      <main className="rag-main-shell">
        {projectId ? (
          <RagWorkspace
            projectId={projectId}
            onError={(msg) => setError(msg)}
          />
        ) : (
          <div className="app-loading-state">
            <Loader2 size={36} className="spin accent-spin" />
            <p>Initializing Research Assistant…</p>
          </div>
        )}
      </main>
    </div>
  );
}
