import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  ArrowUp,
  ArrowUpRight,
  ArrowLeft,
  Plus,
  Search,
  BookOpen,
  Sparkles,
  Compass,
  Leaf,
  Check,
  Loader2,
  X,
  Paperclip,
  History,
  Settings2,
  FileText,
  Download,
  ExternalLink,
  ChevronRight,
  Quote,
  RefreshCw,
  AlertCircle,
  LogOut,
  Feather,
  Network,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, post } from "./api";
import type {
  Evidence,
  Claim,
  Project,
  Paper,
  Job,
  Message,
  User,
} from "./types";

// Research stages shown in the progress trail.
const steps = [
  {
    id: "plan",
    label: "Make a plan",
    icon: Compass,
    verb: "Finding a direction",
  },
  {
    id: "discover",
    label: "Find papers",
    icon: Search,
    verb: "Following the leads",
  },
  {
    id: "index",
    label: "Read & collect",
    icon: BookOpen,
    verb: "A little light reading",
  },
  {
    id: "analyze",
    label: "Connect ideas",
    icon: Network,
    verb: "Joining the dots",
  },
  {
    id: "report",
    label: "Your answer",
    icon: Feather,
    verb: "Bringing it together",
  },
];
const prompts = [
  "How can we make AI hallucinate less?",
  "What is next for solar energy?",
  "How does sleep affect memory?",
];
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
function Modal({
  title,
  close,
  children,
  wide = false,
}: {
  title: string;
  close: () => void;
  children: React.ReactNode;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const prev = document.activeElement as HTMLElement;
    ref.current?.querySelector<HTMLElement>("button,input")?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
      if (e.key === "Tab") {
        const a = ref.current?.querySelectorAll<HTMLElement>(
          "button:not(:disabled),input,textarea,a[href]",
        );
        if (!a?.length) return;
        const first = a[0],
          last = a[a.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      prev?.focus();
    };
  }, []);
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => e.target === e.currentTarget && close()}
    >
      <div
        ref={ref}
        className={"modal " + (wide ? "wide" : "")}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header>
          <h2>{title}</h2>
          <button
            className="icon-button"
            aria-label="Close dialog"
            onClick={close}
          >
            <X size={20} />
          </button>
        </header>
        {children}
      </div>
    </div>
  );
}
export default function App() {
  // State holds the current question, research results, and open dialogs.
  const [user, setUser] = useState<User | null>(null),
    [question, setQuestion] = useState(""),
    [attachment, setAttachment] = useState<File | null>(null),
    [id, setId] = useState(
      location.hash.replace("#research/", "").startsWith("#")
        ? null
        : location.hash.replace("#research/", "") || null,
    );
  const [project, setProject] = useState<Project | null>(null),
    [papers, setPapers] = useState<Paper[]>([]),
    [job, setJob] = useState<Job | null>(null),
    [history, setHistory] = useState<Project[]>([]),
    [messages, setMessages] = useState<Message[]>([]);
  const [busy, setBusy] = useState(""),
    [error, setError] = useState(""),
    [modal, setModal] = useState(""),
    [source, setSource] = useState<Evidence | null>(null),
    [review, setReview] = useState<Claim | null>(null),
    [tab, setTab] = useState("Answer"),
    [followup, setFollowup] = useState(""),
    [config, setConfig] = useState<{
      ai_configured: boolean;
      model: string;
    } | null>(null),
    [activity, setActivity] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null),
    routeRef = useRef(id);
  routeRef.current = id;
  const running = job?.status === "queued" || job?.status === "running";
  const stage =
    job?.events
      .slice()
      .reverse()
      .find((e) => e.stage)?.stage || "plan";
  const stageIndex = steps.findIndex((s) => s.id === stage),
    finished = job?.status === "completed" && !!project?.report;
  const navigate = (next: string | null) => {
    location.hash = next ? "research/" + next : "";
    setId(next);
    setError("");
    setTab("Answer");
    setSource(null);
    setProject(null);
    setJob(null);
    setMessages([]);
  };
  // Fetch a complete workspace; ignore responses for a page we have left.
  const load = useCallback(async (pid: string) => {
    const [p, ps, js, ms] = await Promise.all([
      api<Project>("/projects/" + pid),
      api<Paper[]>("/projects/" + pid + "/papers"),
      api<Job[]>("/projects/" + pid + "/jobs"),
      api<Message[]>("/projects/" + pid + "/messages"),
    ]);
    if (routeRef.current !== pid) return;
    setProject(p);
    setPapers(ps);
    setJob(js[0] || null);
    setMessages(ms);
  }, []);
  useEffect(() => {
    api<User>("/auth/me")
      .then((u) => {
        setUser(u);
        api("/settings").then(setConfig);
      })
      .catch(() => {});
    const change = () => {
      const hash = location.hash;
      setId(hash.startsWith("#research/") ? hash.slice(10) : null);
    };
    window.addEventListener("hashchange", change);
    return () => window.removeEventListener("hashchange", change);
  }, []);
  useEffect(() => {
    if (id) load(id).catch((e) => setError(e.message));
  }, [id, load]);
  useEffect(() => {
    if (!id || !running) return;
    const timer = setInterval(
      () => load(id).catch((e) => setError(e.message)),
      1500,
    );
    return () => clearInterval(timer);
  }, [id, running, load]);
  // Give every asynchronous action the same loading and error handling.
  async function action(name: string, fn: () => Promise<void>) {
    setBusy(name);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  async function ensureUser() {
    if (!user) {
      const u = await api<User>("/auth/guest", post());
      setUser(u);
      setConfig(await api("/settings"));
    }
  }
  // Submit a question, optionally upload a PDF, then start the research pipeline.
  const begin = () =>
    action("start", async () => {
      await ensureUser();
      const p = await api<Project>(
        "/projects",
        post({
          title: question.trim().slice(0, 100),
          question: question.trim(),
        }),
      );
      navigate(p.id);
      routeRef.current = p.id;
      if (attachment) {
        const form = new FormData();
        form.append("file", attachment);
        await api("/projects/" + p.id + "/upload", {
          method: "POST",
          body: form,
        });
        setAttachment(null);
      }
      await api("/projects/" + p.id + "/run/research", post());
      await load(p.id);
      setQuestion("");
    });
  const retry = () =>
    action("retry", async () => {
      await api("/projects/" + id + "/run/research", post());
      await load(id!);
    });
  const showSource = (eid: string, claim?: Claim) => {
    const e = project?.analysis.evidence?.find((e) => e.id === eid);
    if (e) {
      setSource(e);
      setReview(claim || null);
    }
  };
  const citations = (claim: Claim) => (
    <span className="citations">
      {claim.sources.map((s, i) => (
        <button
          key={s.id + i}
          title="Read the supporting passage"
          onClick={() => showSource(s.id, claim)}
        >
          <Quote size={11} />
          {i + 1}
        </button>
      ))}
    </span>
  );
  return (
    <div className={"app " + (id ? "research-view" : "home-view")}>
      <div className="world" aria-hidden="true" />
      <header className="site-header">
        <button
          className="brand-button"
          onClick={() => navigate(null)}
          aria-label="ResearchOS home"
        >
          <Brand />
        </button>
        <nav>
          {id && (
            <button className="nav-button" onClick={() => navigate(null)}>
              <Plus size={16} />
              <span>New question</span>
            </button>
          )}
          <button
            className="nav-button"
            onClick={() =>
              action("history", async () => {
                await ensureUser();
                setHistory(await api("/projects"));
                setModal("history");
              })
            }
          >
            <History size={16} />
            <span>Your explorations</span>
          </button>
          <button
            className="icon-button header-settings"
            aria-label="Settings"
            onClick={() => setModal("settings")}
          >
            <Settings2 size={18} />
          </button>
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
      {!id ? (
        <main className="home">
          <div className="welcome-tag">
            <span className="little-star">✦</span>A little curiosity goes a long
            way
          </div>
          <h1>
            What are we
            <br />
            <span>curious about today?</span>
          </h1>
          <p className="home-description">
            Big questions deserve a little exploring. <br />
            Let’s find the papers, connect the ideas, and make sense of it all.
          </p>
          <form
            className="composer"
            onSubmit={(e) => {
              e.preventDefault();
              begin();
            }}
          >
            <textarea
              aria-label="Your research question"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  if (question.trim().length >= 10 && !busy) begin();
                }
              }}
              placeholder="Ask a question. Follow a possibility…"
              maxLength={3000}
              rows={3}
            />
            {attachment && (
              <div className="attachment">
                <FileText size={13} />
                {attachment.name}
                <button
                  type="button"
                  aria-label="Remove attachment"
                  onClick={() => setAttachment(null)}
                >
                  <X size={13} />
                </button>
              </div>
            )}
            <div className="composer-bottom">
              <div>
                <button
                  type="button"
                  className="attach-button"
                  onClick={() => fileRef.current?.click()}
                >
                  <Paperclip size={17} />
                  <span>Add a paper</span>
                </button>
                <span className="composer-divider" />
                <span className="research-mode">
                  <Sparkles size={14} />
                  Deep research
                </span>
              </div>
              <button
                className="explore-button"
                type="submit"
                disabled={!!busy || question.trim().length < 10}
              >
                {busy === "start" ? (
                  <Loader2 className="spin" size={18} />
                ) : (
                  <>
                    <span>Let’s explore</span>
                    <ArrowUp size={18} />
                  </>
                )}
              </button>
            </div>
          </form>
          <div className="suggestions">
            <span>A little inspiration</span>
            {prompts.map((p) => (
              <button key={p} onClick={() => setQuestion(p)}>
                {p}
                <ArrowUpRight size={13} />
              </button>
            ))}
          </div>
          <div className="home-footnote">
            <BookOpen size={14} />
            Real papers. Clear sources. Room for your own thinking.
          </div>
          <input
            ref={fileRef}
            type="file"
            accept="application/pdf"
            hidden
            onChange={(e) => {
              setAttachment(e.target.files?.[0] || null);
              e.target.value = "";
            }}
          />
        </main>
      ) : (
        <main className="research-shell">
          <button className="back-button" onClick={() => navigate(null)}>
            <ArrowLeft size={15} />
            Back to the clearing
          </button>
          <div className="research-title">
            <div>
              <span className="eyebrow">YOUR LITTLE EXPEDITION</span>
              <h1>{project?.question || "Getting your research ready…"}</h1>
            </div>
            <span className={"run-badge " + (finished ? "complete" : "")}>
              {running ? (
                <>
                  <span className="pulse-dot" />
                  Exploring
                </>
              ) : finished ? (
                <>
                  <Check size={13} />
                  Ready to read
                </>
              ) : job?.status === "failed" ? (
                "Needs a little help"
              ) : (
                "Your research"
              )}
            </span>
          </div>
          <section className="journey" aria-label="Research progress">
            <div className="journey-heading">
              <span>
                <Sparkles size={15} />
                {finished
                  ? "A few steps. A clearer picture."
                  : "Good answers take a little exploring."}
              </span>
              <button onClick={() => setActivity(!activity)}>
                {activity ? "Hide" : "Show"} activity
                <ChevronRight size={13} className={activity ? "rotated" : ""} />
              </button>
            </div>
            <div className="trail">
              {steps.map((s, i) => {
                const done = finished || i < stageIndex,
                  current = running && i === stageIndex;
                return (
                  <React.Fragment key={s.id}>
                    {i > 0 && (
                      <div
                        className={
                          "trail-line " + (done || current ? "lit" : "")
                        }
                      >
                        <i />
                      </div>
                    )}
                    <div
                      className={
                        "trail-stop " +
                        (done ? "done " : "") +
                        (current ? "current " : "")
                      }
                    >
                      <span className="stop-icon">
                        {done ? <Check size={23} /> : <s.icon size={23} />}{" "}
                        {current && <i />}
                      </span>
                      <strong>{s.label}</strong>
                      <small>
                        {done ? "All done" : current ? "On it…" : "Up next"}
                      </small>
                    </div>
                  </React.Fragment>
                );
              })}
            </div>
            {running && (
              <div className="progress-caption" aria-live="polite">
                <Loader2 size={13} className="spin" />
                <span>{job?.events.at(-1)?.text || "Packing our bags…"}</span>
                <strong>{job?.progress || 0}%</strong>
              </div>
            )}
            {activity && (
              <div className="activity-log">
                {job?.events.map((e, i) => (
                  <div key={i}>
                    <span>
                      {new Date(e.time).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                    <i />
                    {e.text}
                  </div>
                ))}
              </div>
            )}
          </section>
          {job?.status === "failed" && (
            <div className="recovery">
              <AlertCircle size={20} />
              <div>
                <h3>A small detour</h3>
                <p>{job.error}</p>
              </div>
              <button className="button" disabled={!!busy} onClick={retry}>
                <RefreshCw size={14} />
                Try again
              </button>
            </div>
          )}
          <div className="result-layout">
            <section className="answer-panel">
              <div className="answer-tabs">
                {["Answer", "Sources", "Research gaps"].map((t) => (
                  <button
                    key={t}
                    className={tab === t ? "active" : ""}
                    onClick={() => setTab(t)}
                  >
                    {t}
                    {t === "Sources" && papers.length > 0 && (
                      <span>{papers.filter((p) => p.selected).length}</span>
                    )}
                  </button>
                ))}
                {project?.report && (
                  <a
                    className="download-link"
                    href={"/api/projects/" + id + "/export"}
                    aria-label="Download research"
                  >
                    <Download size={17} />
                  </a>
                )}
              </div>
              {running && !project?.analysis.papers ? (
                <div className="working">
                  <div className="working-orbit">
                    <span />
                    <span />
                    <span />
                    <div>
                      <StageIcon stage={stage} />
                    </div>
                  </div>
                  <span className="eyebrow">
                    {String(stageIndex + 1).padStart(2, "0")} / 05
                  </span>
                  <h2>
                    {steps[stageIndex]?.verb || "Finding a direction"}
                    <span className="animated-dots">…</span>
                  </h2>
                  <p>
                    {stage === "discover"
                      ? "Looking beyond the obvious. Finding papers that speak to your question."
                      : stage === "index"
                        ? "Taking notes, saving passages, and keeping every source close."
                        : stage === "analyze"
                          ? "Spotting connections, comparing findings, and checking the evidence."
                          : "A thoughtful answer starts with a thoughtful plan."}
                  </p>
                  <div className="working-note">
                    <Leaf size={14} />
                    You can leave this page. Your research keeps going.
                  </div>
                </div>
              ) : tab === "Answer" ? (
                <div className="answer-content">
                  {project?.analysis.papers ? (
                    <>
                      <div className="answer-intro">
                        <span className="answer-spark">
                          <Sparkles size={20} />
                        </span>
                        <div>
                          <span className="eyebrow">HERE’S WHAT WE FOUND</span>
                          <h2>
                            {project.analysis.mode === "extractive"
                              ? "Straight from the source."
                              : "A little more clarity."}
                          </h2>
                        </div>
                      </div>
                      {project.analysis.mode === "extractive" && (
                        <div className="honest-note">
                          <Leaf size={16} />
                          <p>
                            These are original source passages.{" "}
                            <button onClick={() => setModal("settings")}>
                              Connect an AI provider
                            </button>{" "}
                            for a synthesized answer and deeper comparisons.
                          </p>
                        </div>
                      )}
                      {project.analysis.papers.map((p, i) => (
                        <section className="finding-group" key={p.paper_id}>
                          <div className="finding-title">
                            <span>{String(i + 1).padStart(2, "0")}</span>
                            <h3>{p.title}</h3>
                          </div>
                          {p.claims
                            .filter((c) => c.status !== "unsupported")
                            .map((c, j) => (
                              <div className="finding" key={j}>
                                {project.analysis.mode !== "extractive" && (
                                  <span className="finding-dimension">
                                    {c.dimension}
                                  </span>
                                )}
                                <p>
                                  {c.text}
                                  {citations(c)}
                                </p>
                              </div>
                            ))}
                        </section>
                      ))}
                      <div className="answer-end">
                        <Check size={15} />
                        Sources are linked. Interpretations are yours to review.
                      </div>
                    </>
                  ) : (
                    <div className="empty-state">
                      <Feather size={30} />
                      <h2>A good answer is on its way.</h2>
                      <p>
                        Your research will appear here once the evidence is
                        ready.
                      </p>
                      {!running && (
                        <button
                          className="button"
                          disabled={!!busy}
                          onClick={retry}
                        >
                          Start exploring
                          <ArrowUpRight size={15} />
                        </button>
                      )}
                    </div>
                  )}
                </div>
              ) : tab === "Sources" ? (
                <div className="sources-list">
                  {papers
                    .filter((p) => p.selected)
                    .map((p, i) => (
                      <article className="source-card" key={p.id}>
                        <span className="source-index">
                          {String(i + 1).padStart(2, "0")}
                        </span>
                        <div>
                          <div className="paper-meta">
                            {p.source} · {p.year || "Uploaded paper"}
                            <span>
                              {p.status === "indexed"
                                ? "Read & indexed"
                                : p.status}
                            </span>
                          </div>
                          <h3>{p.title}</h3>
                          <p>{p.authors || "Your uploaded document"}</p>
                          {p.error && <p className="paper-error">{p.error}</p>}
                          <div className="source-links">
                            {p.has_pdf && (
                              <a
                                target="_blank"
                                rel="noreferrer"
                                href={
                                  "/api/projects/" +
                                  id +
                                  "/papers/" +
                                  p.id +
                                  "/pdf"
                                }
                              >
                                Read PDF
                                <ExternalLink size={12} />
                              </a>
                            )}
                            {p.url && (
                              <a target="_blank" rel="noreferrer" href={p.url}>
                                Publication
                                <ArrowUpRight size={13} />
                              </a>
                            )}
                          </div>
                        </div>
                      </article>
                    ))}
                  {!papers.length && (
                    <div className="empty-state">
                      <BookOpen size={30} />
                      <h2>Collecting good company.</h2>
                      <p>The papers behind your answer will appear here.</p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="gaps-list">
                  {project?.analysis.gaps?.length ? (
                    project.analysis.gaps.map((c, i) => (
                      <article key={i}>
                        <span className="gap-leaf">
                          <Leaf size={22} />
                        </span>
                        <div>
                          <span className="eyebrow">
                            A POSSIBILITY TO EXPLORE
                          </span>
                          <p>
                            {c.text}
                            {citations(c)}
                          </p>
                        </div>
                      </article>
                    ))
                  ) : (
                    <div className="empty-state">
                      <Leaf size={30} />
                      <h2>There’s always more to explore.</h2>
                      <p>
                        {config?.ai_configured
                          ? "No sufficiently supported gaps have been identified yet."
                          : "Connect an AI provider to explore potential gaps in this collection."}
                      </p>
                    </div>
                  )}
                  <p className="gap-note">
                    Possible directions within these papers, not claims that no
                    one has studied them.
                  </p>
                </div>
              )}
              {messages.length > 0 && (
                <div className="conversation">
                  {messages.map((m) => (
                    <div className={"message " + m.role} key={m.id}>
                      <span>{m.role === "user" ? "You" : "ResearchOS"}</span>
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {m.content}
                      </ReactMarkdown>
                      {m.evidence?.length > 0 && (
                        <div className="message-sources">
                          {m.evidence.map((e, i) => (
                            <button
                              key={e.id}
                              onClick={() => {
                                setSource(e);
                                setReview(null);
                              }}
                            >
                              [{i + 1}] {e.title}
                              <ArrowUpRight size={12} />
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
              {project?.analysis.papers && (
                <form
                  className="followup"
                  onSubmit={(e) => {
                    e.preventDefault();
                    action("chat", async () => {
                      await api(
                        "/projects/" + id + "/chat",
                        post({ content: followup }),
                      );
                      setFollowup("");
                      setMessages(await api("/projects/" + id + "/messages"));
                    });
                  }}
                >
                  <input
                    aria-label="Follow-up question"
                    value={followup}
                    onChange={(e) => setFollowup(e.target.value)}
                    placeholder="A new thought? Ask a follow-up…"
                    minLength={3}
                    maxLength={3000}
                  />
                  <button
                    aria-label="Send follow-up"
                    disabled={!!busy || followup.trim().length < 3}
                  >
                    {busy === "chat" ? (
                      <Loader2 size={17} className="spin" />
                    ) : (
                      <ArrowUp size={18} />
                    )}
                  </button>
                </form>
              )}
            </section>
            <aside className="research-aside">
              <div className="field-note">
                <span className="field-note-icon">
                  <Leaf size={20} />
                </span>
                <span className="eyebrow">A NOTE FROM THE FIELD</span>
                <h3>
                  Stay curious.
                  <br />
                  Keep the source close.
                </h3>
                <p>
                  Every finding has a paper behind it. Tap a citation to read
                  the original passage and see the full picture.
                </p>
                <div className="field-note-rule" />
                <span>
                  {papers.filter((p) => p.status === "indexed").length} papers
                  read <i /> {project?.analysis.evidence?.length || 0} passages
                  connected
                </span>
              </div>
              {project?.plan.queries && (
                <div className="search-notes">
                  <span className="eyebrow">TRAILS WE’RE FOLLOWING</span>
                  {project.plan.queries.map((q) => (
                    <div key={q}>
                      <Search size={13} />
                      {q}
                    </div>
                  ))}
                </div>
              )}
            </aside>
          </div>
          <footer className="research-footer">
            <Leaf size={13} />A little further than where you started.
          </footer>
        </main>
      )}
      {modal === "history" && (
        <Modal title="Your explorations" close={() => setModal("")}>
          <p className="modal-description">
            Every question is a little place you’ve been.
          </p>
          <div className="history-list">
            {history.map((p) => (
              <button
                key={p.id}
                onClick={() => {
                  setModal("");
                  navigate(p.id);
                }}
              >
                <span>
                  <Compass size={18} />
                </span>
                <div>
                  <strong>{p.question}</strong>
                  <small>
                    {new Date(p.created).toLocaleDateString("en", {
                      month: "short",
                      day: "numeric",
                    })}{" "}
                    · {p.paper_count} papers
                  </small>
                </div>
                <ArrowUpRight size={17} />
              </button>
            ))}
            {!history.length && (
              <div className="empty-state">
                <Leaf size={30} />
                <h3>Your first adventure is waiting.</h3>
                <p>Ask a question to get started.</p>
              </div>
            )}
          </div>
        </Modal>
      )}
      {modal === "settings" && (
        <Modal title="Make yourself at home" close={() => setModal("")}>
          <div className="settings-intro">
            <span>
              <Leaf size={22} />
            </span>
            <div>
              <h3>{user?.name || "Hello, curious mind."}</h3>
              <p>
                {user?.email.endsWith("@guest.local")
                  ? "A guest workspace, just for this browser."
                  : user?.email || "Start exploring without an account."}
              </p>
            </div>
          </div>
          <div className="setting-block">
            <div className="setting-heading">
              <h3>Your research companion</h3>
              <span className={config?.ai_configured ? "connected" : ""}>
                {config?.ai_configured ? "Connected" : "Not connected"}
              </span>
            </div>
            <p>
              {config?.ai_configured
                ? "Your AI provider is ready to connect the dots."
                : "Paper discovery and reading work right away. Add an AI provider for synthesized answers, comparisons, and research gaps."}
            </p>
            {!config?.ai_configured && (
              <>
                <p className="setup-copy">
                  Add these server settings to <code>F:\Raglearn\.env</code>,
                  then restart the backend:
                </p>
                <pre>LLM_API_KEY=your-key{"\n"}LLM_MODEL=gpt-4.1-mini</pre>
                <small>
                  For another compatible provider, also set LLM_BASE_URL. Never
                  paste a key into a chat.
                </small>
              </>
            )}
            <button
              className="quiet-button"
              onClick={() =>
                action("settings", async () => {
                  await ensureUser();
                  setConfig(await api("/settings"));
                })
              }
            >
              <RefreshCw size={13} />
              Refresh connection
            </button>
          </div>
          <div className="account-actions">
            {(!user || user.email.endsWith("@guest.local")) && (
              <>
                <button
                  className="button"
                  onClick={() => setModal("save-account")}
                >
                  Keep your workspace
                  <ArrowUpRight size={14} />
                </button>
                <button
                  className="quiet-button"
                  onClick={() => setModal("login")}
                >
                  Sign in to an account
                </button>
              </>
            )}
            {user && !user.email.endsWith("@guest.local") && (
              <button
                className="quiet-button"
                onClick={() =>
                  action("logout", async () => {
                    await api("/auth/logout", post());
                    setUser(null);
                    setConfig(null);
                    setModal("");
                    navigate(null);
                  })
                }
              >
                <LogOut size={14} />
                Sign out
              </button>
            )}
          </div>
          {user?.email.endsWith("@guest.local") && (
            <p className="session-note">
              Guest access lasts 7 days and depends on this browser’s cookie.
              Save an account to keep access to your research.
            </p>
          )}
        </Modal>
      )}
      {(modal === "login" || modal === "save-account") && (
        <Modal
          title={
            modal === "login"
              ? "Welcome back."
              : "Keep your little corner of curiosity."
          }
          close={() => setModal("")}
        >
          <form
            className="account-form"
            onSubmit={(e) => {
              e.preventDefault();
              const data = Object.fromEntries(new FormData(e.currentTarget));
              action("account", async () => {
                if (modal === "save-account") await ensureUser();
                const u = await api<User>(
                  modal === "login" ? "/auth/login" : "/auth/claim",
                  post(data),
                );
                setUser(u);
                setConfig(await api("/settings"));
                setModal("");
                if (modal === "login") navigate(null);
              });
            }}
          >
            {modal === "save-account" && (
              <label>
                Your name
                <input
                  name="name"
                  required
                  maxLength={100}
                  placeholder="Alex Morgan"
                />
              </label>
            )}
            <label>
              Email address
              <input
                name="email"
                type="email"
                required
                placeholder="you@example.com"
              />
            </label>
            <label>
              Password
              <input
                name="password"
                type="password"
                minLength={8}
                required
                placeholder="At least 8 characters"
              />
            </label>
            {error && <p className="form-error">{error}</p>}
            <button className="button full" disabled={!!busy}>
              {busy ? (
                <Loader2 className="spin" size={17} />
              ) : modal === "login" ? (
                "Sign in"
              ) : (
                "Save my workspace"
              )}
              <ArrowUpRight size={16} />
            </button>
          </form>
        </Modal>
      )}
      {source && (
        <Modal
          title="A closer look at the evidence"
          close={() => {
            setSource(null);
            setReview(null);
          }}
          wide
        >
          <div className="evidence-modal">
            <span className="eyebrow">STRAIGHT FROM THE PAPER</span>
            <h2>{source.title}</h2>
            <div className="source-location">
              <span>Page {source.page}</span>
              <span>{source.section}</span>
            </div>
            {review && review.status !== "source_excerpt" && (
              <div className="review-box">
                <h3>The finding</h3>
                <p>{review.text}</p>
                <span>How well does the passage support it?</span>
                <div>
                  {[
                    "supported",
                    "partially_supported",
                    "unsupported",
                    "conflicting",
                  ].map((status) => (
                    <button
                      key={status}
                      className={review.status === status ? "active" : ""}
                      disabled={!!busy || running}
                      onClick={() =>
                        action("review", async () => {
                          await api("/projects/" + id + "/review", {
                            method: "PATCH",
                            body: JSON.stringify({
                              text: review.text,
                              source_ids: review.sources.map((s) => s.id),
                              status,
                            }),
                          });
                          setReview({ ...review, status });
                          await load(id!);
                        })
                      }
                    >
                      {status.replaceAll("_", " ")}
                    </button>
                  ))}
                </div>
              </div>
            )}
            <blockquote>{source.text}</blockquote>
            <p className="evidence-note">
              An original extracted passage. Open the PDF for tables, equations,
              and the full context.
            </p>
            <div className="source-links">
              {source.has_pdf && (
                <a
                  className="button"
                  target="_blank"
                  rel="noreferrer"
                  href={
                    "/api/projects/" +
                    id +
                    "/papers/" +
                    source.paper_id +
                    "/pdf#page=" +
                    source.page
                  }
                >
                  Open page {source.page}
                  <ExternalLink size={14} />
                </a>
              )}
              {source.url && (
                <a target="_blank" rel="noreferrer" href={source.url}>
                  Original publication
                  <ArrowUpRight size={14} />
                </a>
              )}
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
function StageIcon({ stage }: { stage: string }) {
  const Icon = steps.find((s) => s.id === stage)?.icon || Compass;
  return <Icon size={30} />;
}
