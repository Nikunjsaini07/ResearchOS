import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Sparkles,
  Upload,
  ArrowRight,
  Loader2,
  FileText,
  BookOpen,
  MessageSquare,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  Send,
  Zap,
  Brain,
  Layers,
  Search,
  ExternalLink,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, post } from "./api";
import type { RagPaperStatus, RagMessage, RagCitation } from "./types";

interface Props {
  projectId: string;
  onError: (msg: string) => void;
}

export function RagWorkspace({ projectId, onError }: Props) {
  const [status, setStatus] = useState<RagPaperStatus | null>(null);
  const [messages, setMessages] = useState<RagMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [loadingSample, setLoadingSample] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);
  const [inputQuestion, setInputQuestion] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [expandedCitations, setExpandedCitations] = useState<Record<number, boolean>>({});

  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  const loadStatusAndHistory = useCallback(async () => {
    try {
      const s = await api<RagPaperStatus>(`/rag/status?pid=${projectId}`);
      setStatus(s);

      // Load existing messages if any
      const history = await api<Array<{ role: string; content: string; evidence?: any[] }>>(
        `/projects/${projectId}/messages`
      );
      if (history && history.length > 0) {
        setMessages(
          history.map((m) => ({
            role: m.role === "assistant" ? "assistant" : "user",
            content: m.content,
            citations: m.evidence || [],
          }))
        );
      } else {
        setMessages([]);
      }
    } catch (err: any) {
      onError(err.message || "Failed to load workspace status.");
    } finally {
      setLoading(false);
    }
  }, [projectId, onError]);

  useEffect(() => {
    loadStatusAndHistory();
  }, [loadStatusAndHistory]);

  const handleUploadFile = async (file: File) => {
    if (!file) return;
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      onError("Please select a valid PDF file.");
      return;
    }
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("pid", projectId);
      formData.append("file", file);

      const res = await api<{ status: string; title: string }>(`/rag/upload`, {
        method: "POST",
        body: formData,
      });

      await loadStatusAndHistory();
      setMessages([
        {
          role: "assistant",
          content: `I have parsed and indexed **${res.title}**. You can now ask questions about its methodology, results, or limitations!`,
        },
      ]);
    } catch (err: any) {
      onError(err.message || "Failed to parse and index PDF.");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      await handleUploadFile(file);
    }
  };

  const handleLoadSample = async (sampleKey: "attention" | "lora") => {
    setLoadingSample(sampleKey);
    try {
      await api(`/rag/sample`, post({ pid: projectId, sample: sampleKey }));
      await loadStatusAndHistory();
      setMessages([
        {
          role: "assistant",
          content: `Loaded **${
            sampleKey === "attention" ? "Attention Is All You Need" : "LoRA"
          }**! Ask any question below or choose one of the suggested prompts.`,
        },
      ]);
    } catch (err: any) {
      onError(err.message || "Failed to load sample paper.");
    } finally {
      setLoadingSample(null);
    }
  };

  const handleAsk = async (customText?: string) => {
    const question = (customText || inputQuestion).trim();
    if (!question || asking) return;

    setInputQuestion("");
    const newHistory: RagMessage[] = [...messages, { role: "user", content: question }];
    setMessages(newHistory);
    setAsking(true);

    setTimeout(() => {
      chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 50);

    try {
      const res = await api<{ answer: string; citations: RagCitation[] }>(
        `/rag/ask`,
        post({ pid: projectId, question })
      );

      setMessages([
        ...newHistory,
        {
          role: "assistant",
          content: res.answer,
          citations: res.citations || [],
        },
      ]);

      // Automatically expand citations for the latest message
      setExpandedCitations((prev) => ({ ...prev, [newHistory.length]: true }));

      setTimeout(() => {
        chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    } catch (err: any) {
      onError(err.message || "Failed to generate answer.");
    } finally {
      setAsking(false);
    }
  };

  const handleReset = async () => {
    try {
      await api(`/rag/reset`, post({ pid: projectId }));
      setStatus({
        has_paper: false,
        paper: null,
        chunks_count: 0,
        pages_count: 0,
        suggested_questions: [],
      });
      setMessages([]);
    } catch (err: any) {
      onError(err.message || "Failed to reset workspace.");
    }
  };

  const toggleCitations = (index: number) => {
    setExpandedCitations((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  if (loading) {
    return (
      <div className="app-loading-state">
        <Loader2 size={36} className="spin accent-spin" />
        <p>Loading Research Assistant…</p>
      </div>
    );
  }

  // =========================================================================
  // Screen 1: Welcome & PDF Upload / Sample Picker
  // =========================================================================
  if (!status?.has_paper) {
    return (
      <div className="rag-welcome-container">
        <div className="rag-hero-card">
          <div className="rag-badge">
            <Sparkles size={14} />
            <span>Research Paper RAG Assistant</span>
          </div>

          <h2>Chat With Any Research Paper</h2>
          <p>
            Upload a PDF research paper. ResearchOS parses its sections, indexes semantic chunks, and
            answers your questions with grounded citations citing exact pages and sections.
          </p>

          {/* HTML5 Drag & Drop Area */}
          <div
            className={`rag-dropzone ${uploading ? "uploading" : ""} ${isDragging ? "dragging" : ""}`}
            onClick={() => !uploading && fileInputRef.current?.click()}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
              hidden
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleUploadFile(f);
              }}
            />

            {uploading ? (
              <div className="rag-dropzone-loading">
                <Loader2 size={36} className="spin accent-spin" />
                <strong>Extracting text & building RAG index…</strong>
                <span>Parsing PDF pages, detecting section boundaries, and computing chunk representations</span>
              </div>
            ) : (
              <div className="rag-dropzone-content">
                <div className="rag-dropzone-icon">
                  <Upload size={28} />
                </div>
                <strong>Drag & drop a research PDF here, or click to browse</strong>
                <span>Supports machine learning, computer science, and engineering papers (up to 25 MB)</span>
              </div>
            )}
          </div>

          <div className="rag-divider">
            <span>OR TEST INSTANTLY WITH A CLASSIC PAPER</span>
          </div>

          {/* 2 One-Click Sample Cards */}
          <div className="rag-sample-grid">
            <button
              className="rag-sample-card"
              onClick={() => handleLoadSample("attention")}
              disabled={Boolean(loadingSample) || uploading}
              type="button"
            >
              <div className="rag-sample-icon attention-icon">
                <Brain size={22} />
              </div>
              <div className="rag-sample-text">
                <strong>Attention Is All You Need</strong>
                <span>Foundational Transformer architecture paper (Vaswani et al.)</span>
              </div>
              <div className="rag-sample-action">
                {loadingSample === "attention" ? (
                  <Loader2 size={18} className="spin accent-spin" />
                ) : (
                  <ArrowRight size={18} />
                )}
              </div>
            </button>

            <button
              className="rag-sample-card"
              onClick={() => handleLoadSample("lora")}
              disabled={Boolean(loadingSample) || uploading}
              type="button"
            >
              <div className="rag-sample-icon lora-icon">
                <Zap size={22} />
              </div>
              <div className="rag-sample-text">
                <strong>LoRA: Low-Rank Adaptation of LLMs</strong>
                <span>Parameter-efficient fine-tuning on large language models (Hu et al.)</span>
              </div>
              <div className="rag-sample-action">
                {loadingSample === "lora" ? (
                  <Loader2 size={18} className="spin accent-spin" />
                ) : (
                  <ArrowRight size={18} />
                )}
              </div>
            </button>
          </div>
        </div>
      </div>
    );
  }

  // =========================================================================
  // Screen 2: Active RAG Workspace (Dual Pane)
  // =========================================================================
  const paper = status.paper;

  return (
    <div className="rag-workspace">
      {/* Top Paper Header Bar */}
      <div className="rag-paper-bar">
        <div className="rag-paper-meta">
          <div className="rag-paper-eyebrow">
            <BookOpen size={14} />
            <span>ACTIVE RESEARCH PAPER</span>
            {paper?.year && <span className="rag-year-tag">{paper.year}</span>}
          </div>
          <h3>{paper?.title || "Research Paper"}</h3>
          {paper?.authors && <p className="rag-paper-authors">{paper.authors}</p>}
        </div>

        <div className="rag-paper-stats-bar">
          <div className="rag-stat-pill">
            <Layers size={13} />
            <span>{status.chunks_count} Chunks Indexed</span>
          </div>
          <div className="rag-stat-pill">
            <FileText size={13} />
            <span>{status.pages_count} Pages</span>
          </div>
          <button
            className="rag-action-button"
            onClick={() => fileInputRef.current?.click()}
            title="Upload a different PDF"
          >
            <Upload size={13} />
            <span>Upload Another</span>
          </button>
          <button className="rag-action-button danger" onClick={handleReset} title="Clear paper & chat">
            <RotateCcw size={13} />
            <span>Reset</span>
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            hidden
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleUploadFile(f);
            }}
          />
        </div>
      </div>

      {/* Main Dual-Pane Workspace */}
      <div className="rag-layout">
        {/* Left Pane: Document Overview & Suggested Questions */}
        <aside className="rag-sidebar">
          {paper?.abstract && (
            <div className="sidebar-section">
              <h4>Abstract & Summary</h4>
              <p className="abstract-text">{paper.abstract}</p>
            </div>
          )}

          {status.suggested_questions && status.suggested_questions.length > 0 && (
            <div className="sidebar-section">
              <h4>Suggested Questions</h4>
              <div className="suggested-questions-list">
                {status.suggested_questions.map((q, idx) => (
                  <button
                    key={idx}
                    className="suggested-question-pill"
                    onClick={() => handleAsk(q)}
                    disabled={asking}
                    type="button"
                  >
                    <MessageSquare size={13} />
                    <span>{q}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="sidebar-section">
            <h4>RAG Pipeline Overview</h4>
            <div className="rag-pipeline-card">
              <div className="pipeline-step">
                <CheckCircle2 size={14} className="step-done" />
                <span>PDF parsed into {status.chunks_count} structured section chunks</span>
              </div>
              <div className="pipeline-step">
                <CheckCircle2 size={14} className="step-done" />
                <span>Hybrid BM25 + Keyword search with section-weighting</span>
              </div>
              <div className="pipeline-step">
                <CheckCircle2 size={14} className="step-done" />
                <span>Grounded generation with verbatim page and section references</span>
              </div>
            </div>
          </div>
        </aside>

        {/* Right Pane: Interactive RAG Chat */}
        <main className="rag-chat-pane">
          <div className="chat-messages-scroll">
            {messages.length === 0 ? (
              <div className="rag-chat-empty">
                <Sparkles size={32} className="empty-sparkle" />
                <h4>Ask anything about this paper</h4>
                <p>
                  Questions are answered strictly using retrieved excerpts from the document, with exact
                  page and section citations.
                </p>
                <div className="empty-prompts-row">
                  {status.suggested_questions.slice(0, 2).map((q, idx) => (
                    <button key={idx} className="empty-prompt-pill" onClick={() => handleAsk(q)}>
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((m, idx) => (
                <div key={idx} className={`rag-chat-bubble-row ${m.role}`}>
                  <div className="bubble-header-label">
                    {m.role === "user" ? "You" : "Research Assistant"}
                  </div>
                  <div className={`rag-bubble ${m.role}`}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                  </div>

                  {/* Grounded Source Citations Accordion */}
                  {m.role === "assistant" && m.citations && m.citations.length > 0 && (
                    <div className="rag-citations-container">
                      <button
                        className="citations-toggle-btn"
                        onClick={() => toggleCitations(idx)}
                        type="button"
                      >
                        <Search size={13} />
                        <span>{m.citations.length} Grounded Sources Cited</span>
                        {expandedCitations[idx] ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                      </button>

                      {expandedCitations[idx] && (
                        <div className="citations-cards-list">
                          {m.citations.map((c, cIdx) => (
                            <div key={cIdx} className="citation-card">
                              <div className="citation-top">
                                <span className="citation-location">
                                  Page {c.page} · {c.section}
                                </span>
                                {c.score > 0 && (
                                  <span className="citation-score">
                                    Relevance: {(c.score * 100).toFixed(0)}%
                                  </span>
                                )}
                              </div>
                              <p className="citation-snippet">"{c.snippet}"</p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))
            )}

            {asking && (
              <div className="rag-chat-bubble-row assistant">
                <div className="bubble-header-label">Research Assistant</div>
                <div className="rag-bubble assistant loading-bubble">
                  <Loader2 size={16} className="spin" />
                  <span>Searching paper chunks & synthesizing grounded answer…</span>
                </div>
              </div>
            )}
            <div ref={chatBottomRef} />
          </div>

          {/* Chat Input Bar */}
          <form
            className="rag-chat-input-row"
            onSubmit={(e) => {
              e.preventDefault();
              handleAsk();
            }}
          >
            <input
              type="text"
              placeholder="Ask a question about this paper (e.g. 'What is the core methodology?')..."
              value={inputQuestion}
              onChange={(e) => setInputQuestion(e.target.value)}
              disabled={asking}
            />
            <button
              type="submit"
              disabled={!inputQuestion.trim() || asking}
              className="rag-send-button"
              aria-label="Send question"
            >
              <Send size={16} />
            </button>
          </form>
        </main>
      </div>
    </div>
  );
}

