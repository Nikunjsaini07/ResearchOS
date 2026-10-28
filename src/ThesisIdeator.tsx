import React, { useState, useRef } from "react";
import {
  Sparkles,
  Upload,
  ArrowRight,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  Cpu,
  Database,
  Download,
  Copy,
  Check,
  Send,
  Zap,
  Target,
  BookOpen,
  ChevronDown,
  ChevronUp,
  Brain,
  Sliders,
  Plus,
  Compass,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, post } from "./api";
import type { Project, ThesisProposal, IdeatorData, PaperGap } from "./types";

interface Props {
  project: Project;
  onRefresh: () => Promise<void>;
  onReset?: () => Promise<void>;
  onError: (msg: string) => void;
}

export function ThesisIdeator({ project, onRefresh, onReset, onError }: Props) {
  const ideator: IdeatorData | undefined = project.analysis?.ideator;
  const [selectedProposalId, setSelectedProposalId] = useState<string | null>(
    () => ideator?.proposals?.[0]?.id || null
  );
  const [uploading, setUploading] = useState(false);
  const [loadingSample, setLoadingSample] = useState<string | null>(null);
  const [customFocus, setCustomFocus] = useState("");
  const [isGapsOpen, setIsGapsOpen] = useState(true);
  const [isDragging, setIsDragging] = useState(false);

  // Chat refinement state
  const [chatMessage, setChatMessage] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatHistory, setChatHistory] = useState<Array<{ role: string; content: string }>>([]);
  const [copied, setCopied] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const activeProposal: ThesisProposal | undefined =
    ideator?.proposals?.find((p) => p.id === selectedProposalId) ||
    ideator?.proposals?.[0];

  const quickPrompts = [
    "Adapt this for a single 8GB laptop GPU",
    "Draft a 1-page proposal summary for my advisor",
    "What hard questions will my committee ask?",
    "Give me the exact PyTorch repository structure for Phase 1",
  ];

  const processFileUpload = async (file: File) => {
    if (!file) return;
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      onError("Please select a valid PDF research paper.");
      return;
    }
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      if (customFocus.trim()) {
        formData.append("focus", customFocus.trim());
      }
      await api(`/projects/${project.id}/upload`, {
        method: "POST",
        body: formData,
      });
      await onRefresh();
      setSelectedProposalId("prop-1");
    } catch (err: any) {
      onError(err.message || "Failed to process the research paper.");
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
      await processFileUpload(file);
    }
  };

  const handleLoadSample = async (sampleKey: "lora" | "attention") => {
    setLoadingSample(sampleKey);
    try {
      await api(`/projects/${project.id}/ideate`, post({ sample: sampleKey, focus: customFocus }));
      await onRefresh();
      setSelectedProposalId("prop-1");
    } catch (err: any) {
      onError(err.message || "Could not load sample paper.");
    } finally {
      setLoadingSample(null);
    }
  };

  const handleSendMessage = async (msgText?: string) => {
    const textToSend = msgText || chatMessage.trim();
    if (!textToSend || !activeProposal || chatLoading) return;

    const newHistory = [...chatHistory, { role: "user", content: textToSend }];
    setChatHistory(newHistory);
    setChatMessage("");
    setChatLoading(true);

    try {
      const res = await api<{ reply: string; proposal: ThesisProposal; ideator: IdeatorData }>(
        `/projects/${project.id}/refine-proposal`,
        post({
          proposal_id: activeProposal.id,
          message: textToSend,
        })
      );

      setChatHistory([
        ...newHistory,
        { role: "assistant", content: res.reply },
      ]);
      await onRefresh();
      setTimeout(() => {
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    } catch (err: any) {
      onError(err.message || "Failed to get advice from Thesis Advisor.");
    } finally {
      setChatLoading(false);
    }
  };

  const copyMarkdown = () => {
    if (!activeProposal || !ideator) return;
    const text = `# ${activeProposal.title}\n\n**Category:** ${activeProposal.category}\n**Hypothesis:** ${activeProposal.hypothesis}\n\n## Baseline to Beat\n${activeProposal.baseline_to_beat}\n\n## Datasets & Tools\n${activeProposal.datasets_and_tools.join(", ")}`;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // State 1: No paper analyzed yet -> Show Hero & Dropzone & Samples
  if (!ideator) {
    return (
      <div className="ideator-welcome-container">
        <div className="ideator-hero">
          <div className="ideator-badge">
            <Sparkles size={15} />
            <span>AI Research Paper Critic & Thesis Generator</span>
          </div>
          <h2>Turn Any Research Paper Into an Actionable Thesis</h2>
          <p>
            Upload a research PDF or pick an iconic paper. ResearchOS spots unaddressed limitations,
            pinpoints open gaps, and synthesizes 3 complete project blueprints ready for coursework, a master's thesis, or a publication.
          </p>

          {/* Optional Focus / Constraints Input */}
          <div className="focus-input-wrapper">
            <Sliders size={16} className="focus-icon" />
            <input
              type="text"
              className="focus-input"
              placeholder="Optional: Tailor for specific constraints (e.g. '8GB GPU', 'Medical domain', 'Edge device')…"
              value={customFocus}
              onChange={(e) => setCustomFocus(e.target.value)}
            />
          </div>

          {/* Drag & Drop Zone with Native HTML5 Handlers */}
          <div
            className={`ideator-dropzone ${uploading ? "uploading" : ""} ${isDragging ? "dragging" : ""}`}
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
                if (f) processFileUpload(f);
              }}
            />
            {uploading ? (
              <div className="dropzone-loading">
                <Loader2 size={36} className="spin accent-spin" />
                <strong>Reading paper & synthesizing proposals…</strong>
                <span>Extracting core methodology, limitations, and research gaps</span>
              </div>
            ) : (
              <div className="dropzone-content">
                <div className="dropzone-icon">
                  <Upload size={28} />
                </div>
                <strong>Drag and drop a PDF here, or click to choose</strong>
                <span>Supports Machine Learning, Computer Science, and Engineering papers</span>
              </div>
            )}
          </div>

          <div className="ideator-divider">
            <span>OR TEST INSTANTLY WITH A CLASSIC PAPER</span>
          </div>

          {/* 2 One-Click Sample Cards */}
          <div className="sample-cards-grid">
            <button
              className="sample-paper-card"
              onClick={() => handleLoadSample("lora")}
              disabled={Boolean(loadingSample) || uploading}
              type="button"
            >
              <div className="sample-card-icon lora-color">
                <Zap size={20} />
              </div>
              <div className="sample-card-text">
                <strong>LoRA: Low-Rank Adaptation of LLMs</strong>
                <span>Parameter-efficient fine-tuning for massive models</span>
              </div>
              <div className="sample-card-action">
                {loadingSample === "lora" ? (
                  <Loader2 size={18} className="spin accent-spin" />
                ) : (
                  <ArrowRight size={18} />
                )}
              </div>
            </button>

            <button
              className="sample-paper-card"
              onClick={() => handleLoadSample("attention")}
              disabled={Boolean(loadingSample) || uploading}
              type="button"
            >
              <div className="sample-card-icon attention-color">
                <Brain size={20} />
              </div>
              <div className="sample-card-text">
                <strong>Attention Is All You Need</strong>
                <span>The foundational Transformer architecture</span>
              </div>
              <div className="sample-card-action">
                {loadingSample === "attention" ? (
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

  // State 2: Paper Analyzed -> Full Ideation Workspace & Studio
  return (
    <div className="ideator-dashboard">
      {/* Paper Digest Header */}
      <div className="paper-digest-bar">
        <div className="digest-info">
          <div className="digest-eyebrow">
            <BookOpen size={14} />
            <span>ANALYZED PAPER</span>
            {ideator.digest.year && <span className="digest-year">{ideator.digest.year}</span>}
          </div>
          <h3>{ideator.digest.title}</h3>
          <p className="digest-authors">{ideator.digest.authors}</p>
          <p className="digest-summary">{ideator.digest.core_problem}</p>
        </div>

        <div className="digest-actions">
          {onReset && (
            <button className="new-analysis-pill" onClick={onReset} title="Start new analysis">
              <Plus size={15} />
              <span>New Analysis</span>
            </button>
          )}
          <button
            className="re-ideate-btn"
            onClick={() => fileInputRef.current?.click()}
            title="Upload another paper"
          >
            <Upload size={14} />
            <span>Upload Another</span>
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            hidden
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) processFileUpload(f);
            }}
          />
        </div>
      </div>

      {/* Extracted Research Gaps Section */}
      {ideator.gaps && ideator.gaps.length > 0 && (
        <section className="gaps-panel">
          <div
            className="gaps-header"
            onClick={() => setIsGapsOpen(!isGapsOpen)}
            role="button"
            tabIndex={0}
          >
            <div className="gaps-header-title">
              <AlertTriangle size={18} className="gaps-icon" />
              <strong>Identified Limitations & Research Gaps in Paper</strong>
              <span className="gaps-count">{ideator.gaps.length} gaps</span>
            </div>
            <button className="icon-btn-ghost" aria-label="Toggle gaps">
              {isGapsOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
          </div>

          {isGapsOpen && (
            <div className="gaps-grid">
              {ideator.gaps.map((gap: PaperGap, index: number) => (
                <div className="gap-card" key={index}>
                  <div className="gap-area-tag">{gap.area}</div>
                  <p className="gap-desc">{gap.gap}</p>
                  {gap.evidence && (
                    <div className="gap-evidence">
                      <strong>Cited Context:</strong> {gap.evidence}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* 3 Proposals Selector Matrix */}
      <section className="proposals-matrix">
        <div className="matrix-title">
          <div>
            <h2>3 Actionable Thesis & Project Proposals</h2>
            <p>Select a blueprint to inspect the roadmap, benchmark baseline, and refine with the AI Advisor.</p>
          </div>
        </div>

        <div className="proposals-grid">
          {ideator.proposals.map((proposal) => {
            const isSelected = activeProposal?.id === proposal.id;
            return (
              <div
                key={proposal.id}
                className={`proposal-summary-card ${isSelected ? "selected" : ""}`}
                onClick={() => setSelectedProposalId(proposal.id)}
                role="button"
                tabIndex={0}
              >
                <div className="card-top-row">
                  <span className={`category-badge ${proposal.category.toLowerCase().replace(/[^a-z]/g, "-")}`}>
                    {proposal.category}
                  </span>
                  <span className="difficulty-badge">{proposal.difficulty}</span>
                </div>

                <h4 className="proposal-title">{proposal.title}</h4>
                <p className="proposal-tagline">{proposal.tagline}</p>

                <div className="card-specs">
                  <div className="spec-item">
                    <Cpu size={14} />
                    <span>{proposal.compute}</span>
                  </div>
                  <div className="spec-item">
                    <Target size={14} />
                    <span>Baseline: {proposal.baseline_to_beat.slice(0, 42)}…</span>
                  </div>
                </div>

                <div className="card-footer-cta">
                  <span className="select-indicator">
                    {isSelected ? "Active in Studio" : "Open in Studio"}
                  </span>
                  <ArrowRight size={14} />
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Proposal Studio & Refinement Workspace */}
      {activeProposal && (
        <section className="proposal-studio">
          <div className="studio-header">
            <div>
              <span className="studio-eyebrow">
                <Compass size={14} />
                <span>PROJECT STUDIO</span>
              </span>
              <h3>{activeProposal.title}</h3>
            </div>

            <div className="studio-actions">
              <button className="studio-action-btn" onClick={copyMarkdown} title="Copy Proposal Markdown">
                {copied ? <Check size={16} /> : <Copy size={16} />}
                <span>{copied ? "Copied" : "Copy"}</span>
              </button>
              <a
                href={`/api/projects/${project.id}/proposals/${activeProposal.id}/export`}
                className="studio-action-btn primary"
                download
              >
                <Download size={16} />
                <span>Export .md</span>
              </a>
            </div>
          </div>

          <div className="studio-layout">
            {/* Left: Detailed Proposal Specs & Roadmap */}
            <div className="proposal-details-panel">
              <div className="detail-section">
                <h5>Core Hypothesis</h5>
                <div className="hypothesis-box">
                  <Zap size={16} className="hypothesis-icon" />
                  <p>{activeProposal.hypothesis}</p>
                </div>
              </div>

              <div className="detail-section">
                <h5>Problem Statement in Prior Paper</h5>
                <p className="text-secondary">{activeProposal.problem_statement}</p>
              </div>

              <div className="detail-section">
                <h5>Required Datasets & Open-Source Tools</h5>
                <div className="tools-list">
                  {activeProposal.datasets_and_tools.map((tool, idx) => (
                    <span key={idx} className="tool-tag">
                      <Database size={12} />
                      {tool}
                    </span>
                  ))}
                </div>
              </div>

              <div className="detail-section">
                <h5>3-Phase Execution Roadmap</h5>
                <div className="roadmap-timeline">
                  {activeProposal.roadmap.map((step, idx) => (
                    <div key={idx} className="timeline-node">
                      <div className="node-marker">{idx + 1}</div>
                      <div className="node-body">
                        <strong>{step.phase}</strong>
                        <p className="node-task">{step.task}</p>
                        <div className="node-milestone">
                          <CheckCircle2 size={13} />
                          <span>Milestone: {step.milestone}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="detail-section">
                <h5>Target Baseline to Beat</h5>
                <div className="baseline-banner">
                  <Target size={16} />
                  <span>{activeProposal.baseline_to_beat}</span>
                </div>
              </div>

              {activeProposal.potential_risks && (
                <div className="detail-section">
                  <h5>Technical Risk & Mitigation</h5>
                  <p className="risk-text">⚠️ {activeProposal.potential_risks}</p>
                </div>
              )}
            </div>

            {/* Right: Interactive AI Advisor Chat */}
            <div className="refinement-chat-panel">
              <div className="chat-panel-header">
                <div>
                  <strong>AI Thesis Advisor</strong>
                  <span>Ask questions, customize constraints, or draft defense answers</span>
                </div>
              </div>

              <div className="quick-prompts-bar">
                {quickPrompts.map((prompt, idx) => (
                  <button
                    key={idx}
                    className="prompt-chip"
                    onClick={() => handleSendMessage(prompt)}
                    disabled={chatLoading}
                    type="button"
                  >
                    {prompt}
                  </button>
                ))}
              </div>

              <div className="chat-messages-container">
                {chatHistory.length === 0 ? (
                  <div className="chat-empty-state">
                    <Sparkles size={28} className="empty-sparkle" />
                    <strong>Refine your project with the Thesis Advisor</strong>
                    <p>
                      Need to lower compute requirements, change the dataset, or draft a proposal
                      for your professor? Send a message below or pick a quick prompt.
                    </p>
                  </div>
                ) : (
                  chatHistory.map((m, idx) => (
                    <div key={idx} className={`chat-bubble ${m.role}`}>
                      <div className="bubble-author">
                        {m.role === "user" ? "You" : "Thesis Advisor"}
                      </div>
                      <div className="bubble-content">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {m.content}
                        </ReactMarkdown>
                      </div>
                    </div>
                  ))
                )}
                {chatLoading && (
                  <div className="chat-bubble assistant loading">
                    <Loader2 size={16} className="spin" />
                    <span>Advisor is analyzing your request…</span>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              <form
                className="chat-input-row"
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage();
                }}
              >
                <input
                  type="text"
                  placeholder="Ask a question or adjust constraints (e.g. 'Use medical dataset instead')…"
                  value={chatMessage}
                  onChange={(e) => setChatMessage(e.target.value)}
                  disabled={chatLoading}
                />
                <button
                  type="submit"
                  disabled={!chatMessage.trim() || chatLoading}
                  className="chat-send-btn"
                  aria-label="Send message"
                >
                  <Send size={16} />
                </button>
              </form>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
