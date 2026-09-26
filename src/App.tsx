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
  FileText,
  Download,
  ExternalLink,
  ChevronRight,
  Quote,
  RefreshCw,
  AlertCircle,
  Feather,
  Network,
  History,
  LogIn,
  LogOut,
  UserRound,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, post, ApiError } from "./api";
import type {
  Evidence,
  Claim,
  Project,
  Paper,
  Job,
  Message,
  User,
  ProjectSummary,
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
const isGuest = (user: User | null) => !!user?.email.endsWith("@guest.local");
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
  const connectionMessage = "Connection lost. Your saved research will return when you reconnect.";
  // State holds the current question, research results, and open dialogs.
  const [user, setUser] = useState<User | null>(null),
    [question, setQuestion] = useState(() => {
      try { return localStorage.getItem("researchos:draftQuestion") || ""; }
      catch { return ""; }
    }),
    [attachment, setAttachment] = useState<File | null>(null),
    [id, setId] = useState(
      location.hash.replace("#research/", "").startsWith("#")
        ? null
        : location.hash.replace("#research/", "") || null,
    );
  const [project, setProject] = useState<Project | null>(null),
    [papers, setPapers] = useState<Paper[]>([]),
    [job, setJob] = useState<Job | null>(null),
    [messages, setMessages] = useState<Message[]>([]);
  const [busy, setBusy] = useState(""),
    [error, setError] = useState(""),
    [authReady, setAuthReady] = useState(false),
    [modal, setModal] = useState(""),
    [source, setSource] = useState<Evidence | null>(null),
    [review, setReview] = useState<Claim | null>(null),
    [tab, setTab] = useState("Answer"),
    [followup, setFollowup] = useState(""),
    [config, setConfig] = useState<{
      ai_configured: boolean;
      model: string;
      free_only: boolean;
    } | null>(null),
    [activity, setActivity] = useState(false);
  const [library, setLibrary] = useState<ProjectSummary[]>([]);
  const [libraryBusy, setLibraryBusy] = useState(false);
  const [libraryError, setLibraryError] = useState("");
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [authError, setAuthError] = useState("");
  const [authBusy, setAuthBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null),
    routeRef = useRef(id);
  const activeProjectRef = useRef<string | null>(null);
  const historyRequests = useRef(new Set<string>());
  const closeActive = async () => {
    const pid = activeProjectRef.current;
    activeProjectRef.current = null;
    if (pid) {
      await api("/projects/" + pid + "/archive", { ...post(), keepalive: true });
      historyRequests.current.add(pid);
    }
  };
  useEffect(() => {
    try {
      if (question) localStorage.setItem("researchos:draftQuestion", question);
      else localStorage.removeItem("researchos:draftQuestion");
    } catch {}
  }, [question]);
  routeRef.current = id;
  const running = job?.status === "queued" || job?.status === "running";
  const stage =
    job?.events
      .slice()
      .reverse()
      .find((e) => e.stage)?.stage || job?.kind || "plan";
  const stageIndex = steps.findIndex((s) => s.id === stage),
    finished = !running && !!project?.report;
  const navigate = (next: string | null) => {
    if (activeProjectRef.current && activeProjectRef.current !== next) void closeActive().catch(() => {});
    routeRef.current = next;
    location.hash = next ? "research/" + next : "";
    setId(next);
    setError("");
    setTab("Answer");
    setSource(null);
    setProject(null);
    setPapers([]);
    setJob(null);
    setMessages([]);
  };
  // Fetch a complete workspace; ignore responses for a page we have left.
  const load = useCallback(async (pid: string) => {
    let p: Project, ps: Paper[], js: Job[], ms: Message[];
    try {
      if (activeProjectRef.current !== pid && !historyRequests.current.has(pid)) {
        await api("/projects/" + pid + "/archive", post());
        historyRequests.current.add(pid);
      }
      [p, ps, js, ms] = await Promise.all([
        api<Project>("/projects/" + pid),
        api<Paper[]>("/projects/" + pid + "/papers"),
        api<Job[]>("/projects/" + pid + "/jobs"),
        api<Message[]>("/projects/" + pid + "/messages"),
      ]);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401 && routeRef.current === pid) {
        setUser(null);
        setAuthMode("login");
        setAuthError("Your session expired. Sign in to reopen research saved to your account.");
        setModal("auth");
        return;
      }
      if (e instanceof ApiError && e.status === 404 && routeRef.current === pid) {
        location.hash = "";
        routeRef.current = null;
        setId(null);
        setProject(null);
        setJob(null);
        setError("This research is unavailable in the current account. Open your research library or start a new question.");
        return;
      }
      throw e;
    }
    if (routeRef.current !== pid) return;
    setProject(p);
    setPapers(ps);
    setJob(js[0] || null);
    setMessages(ms);
    setError((current) => current === connectionMessage ? "" : current);
  }, []);
  useEffect(() => {
    let active = true;
    let retry: number | undefined;
    const restore = async () => {
      try {
        let u: User;
        try {
          u = await api<User>("/auth/me");
        } catch (e) {
          if (!(e instanceof ApiError) || e.status !== 401) throw e;
          if (location.hash.startsWith("#research/")) {
            if (!active) return;
            setAuthReady(true);
            setError("Your session expired. Sign in to reopen research saved to your account.");
            return;
          }
          u = await api<User>("/auth/guest", post());
        }
        if (!active) return;
        setUser(u);
        setAuthReady(true);
        setError((current) => current === connectionMessage ? "" : current);
        api("/settings").then(setConfig).catch(() => {});
      } catch (e) {
        if (!active) return;
        if (!(e instanceof ApiError) || e.status === 429 || e.status >= 500) {
          setError(connectionMessage);
          retry = window.setTimeout(restore, 5000);
        } else {
          setError((e as Error).message);
        }
      }
    };
    restore();
    const reconnect = () => {
      window.clearTimeout(retry);
      restore();
    };
    window.addEventListener("online", reconnect);
    const change = () => {
      const hash = location.hash;
      const next = hash.startsWith("#research/") ? hash.slice(10) : null;
      if (activeProjectRef.current && activeProjectRef.current !== next) void closeActive().catch(() => {});
      routeRef.current = next;
      setId(next);
    };
    const leave = () => { void closeActive().catch(() => {}); };
    window.addEventListener("hashchange", change);
    window.addEventListener("pagehide", leave);
    return () => {
      active = false;
      window.clearTimeout(retry);
      window.removeEventListener("online", reconnect);
      window.removeEventListener("hashchange", change);
      window.removeEventListener("pagehide", leave);
    };
  }, []);
  useEffect(() => {
    if (id && authReady && user) load(id).catch((e) => setError(e instanceof ApiError && e.status < 500 ? e.message : connectionMessage));
  }, [id, authReady, user?.email, load]);
  useEffect(() => {
    if (!id || !running || !user) return;
    const timer = setInterval(
      () => load(id).catch((e) => setError(e instanceof ApiError && e.status < 500 ? e.message : connectionMessage)),
      1500,
    );
    return () => clearInterval(timer);
  }, [id, running, user?.email, load]);
  useEffect(() => {
    if (!id || !authReady || !user) return;
    const reconnect = () => load(id).catch((e) => setError((e as Error).message));
    window.addEventListener("online", reconnect);
    return () => window.removeEventListener("online", reconnect);
  }, [id, authReady, user?.email, load]);
  const openLibrary = async () => {
    if (!user) {
      setAuthMode("login");
      setModal("auth");
      return;
    }
    setModal("library");
    setLibraryBusy(true);
    setLibraryError("");
    setError("");
    try {
      setLibrary(await api<ProjectSummary[]>("/projects/library"));
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setUser(null);
        setAuthMode("login");
        setAuthError("Your session expired. Sign in to open your research library.");
        setModal("auth");
      } else {
        setLibraryError((e as Error).message);
      }
    } finally {
      setLibraryBusy(false);
    }
  };
  const submitAuth = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const credentials = {
      name: String(data.get("name") || "Researcher"),
      email: String(data.get("email") || "").trim(),
      password: String(data.get("password") || ""),
    };
    setAuthBusy(true);
    setAuthError("");
    try {
      const endpoint = authMode === "login" ? "login" : isGuest(user) ? "claim" : "register";
      const next = await api<User>("/auth/" + endpoint, post(credentials));
      setUser(next);
      setError("");
      setModal("");
      api("/settings").then(setConfig).catch(() => {});
    } catch (e) {
      setAuthError((e as Error).message);
    } finally {
      setAuthBusy(false);
    }
  };
  const signOut = () => action("logout", async () => {
    await closeActive();
    await api("/auth/logout", post());
    setUser(null);
    setLibrary([]);
    setQuestion("");
    setAttachment(null);
    setModal("");
    navigate(null);
  });
  // Give every asynchronous action the same loading and error handling.
  async function action(name: string, fn: () => Promise<void>) {
    setBusy(name);
    setError("");
    try {
      await fn();
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setUser(null);
        setAuthMode("login");
        setAuthError("Your session expired. Sign in to continue.");
        setModal("auth");
      } else {
        setError((e as Error).message);
      }
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
      activeProjectRef.current = p.id;
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
      await api("/projects/" + id + "/run/" + (job?.kind || "research"), post());
      await load(id!);
    });
  const runStep = (kind: string) => action(kind, async () => {
    await api("/projects/" + id + "/run/" + kind, post());
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
            <button className="nav-button" onClick={() => navigate(null)} aria-label="New question">
              <Plus size={16} />
              <span>New question</span>
            </button>
          )}
          <button className="nav-button" onClick={openLibrary} aria-label="Open saved research">
            <History size={16} />
            <span>Conversation history</span>
          </button>
          {user && !isGuest(user) ? (
            <button className="nav-button account-trigger" onClick={() => setModal("account")} aria-label="Your account">
              <UserRound size={16} />
              <span>{user.name}</span>
            </button>
          ) : (
            <button className="nav-button account-trigger" onClick={() => { setAuthMode("login"); setAuthError(""); setModal("auth"); }} aria-label="Sign in">
              <LogIn size={16} />
              <span>Sign in</span>
            </button>
          )}
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
      ) : !project ? (
        <main className="research-shell"><div className="library-empty" role="status">
          {authReady && !user ? "Sign in to read your saved conversation." : <><Loader2 className="spin" size={22} /> Loading conversation…</>}
        </div></main>
      ) : project.readonly ? (
        <main className="research-shell saved-conversation">
          <div className="research-title">
            <div><span className="eyebrow">CONVERSATION HISTORY · {new Date(project.created).toLocaleDateString()}</span><h1>{project.question}</h1></div>
            <span className="run-badge">Read only</span>
          </div>
          <section className="answer-panel">
            <div className="saved-heading"><h2>Saved result</h2>{project.report && <a href={"/api/projects/" + id + "/export"} aria-label="Download saved result"><Download size={18} /></a>}</div>
            <div className="saved-result">
              {running ? <p role="status"><Loader2 size={16} className="spin" /> Research is finishing. Its result will appear here.</p> : <ReactMarkdown remarkPlugins={[remarkGfm]}>{project.report || "This conversation ended before a result was generated."}</ReactMarkdown>}
            </div>
            {!!messages.length && <div className="conversation">{messages.map((message) => <div className={"message " + message.role} key={message.id}><span>{message.role === "user" ? "You" : "ResearchOS"}</span><ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown></div>)}</div>}
            <p className="saved-note">This is a record of the conversation and result. Start a new question to research further.</p>
          </section>
          <button className="quiet-button delete-project" disabled={running || !!busy} onClick={() => setModal("delete-project")}>Delete this conversation</button>
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
                const done = finished || (running && i < stageIndex) || (!running && !!project?.analysis.papers && i < 4),
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
                {["Answer", "Compare", "Sources", "Research gaps"].map((t) => (
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
              {!running && project?.analysis.papers && !project.report && (
                <div className="workspace-tools">
                  <p>Your findings changed. Update the report to download the latest review.</p>
                  <button className="button" disabled={!!busy} onClick={() => runStep("report")}>Generate report</button>
                </div>
              )}
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
                      {!project.analysis.findings && papers.some((p) => p.selected && p.status === "indexed") && (
                        <div className="legacy-answer">
                          <p>This answer uses the older paper-by-paper format.</p>
                          <button className="button" disabled={!!busy || running} onClick={() => runStep("refine")}>Update answer</button>
                        </div>
                      )}
                      {project.analysis.mode !== "synthesized" && !!project.analysis.findings && config?.ai_configured && (
                        <div className="legacy-answer">
                          <p>The AI answer did not complete. Try the research again.</p>
                          <button className="button" disabled={!!busy || running} onClick={() => runStep("research")}>Research again</button>
                        </div>
                      )}
                      <div className="answer-intro">
                        <span className="answer-spark">
                          <Sparkles size={20} />
                        </span>
                        <div>
                          <span className="eyebrow">HERE’S WHAT WE FOUND</span>
                          <h2>
                            {project.analysis.mode !== "synthesized"
                              ? "Summary unavailable"
                              : "An answer to your question"}
                          </h2>
                        </div>
                      </div>
                      {project.analysis.mode !== "synthesized" && (
                        <div className="honest-note">
                          <Leaf size={16} />
                          <p>
                            {project.analysis.note || "These are original source passages. Open Sources to inspect the full paper set."}
                          </p>
                        </div>
                      )}
                      <section className="answer-section">
                        <h3>Direct answer</h3>
                        {project.analysis.overview?.some((c) => c.status !== "unsupported") ? (
                          project.analysis.overview.filter((c) => c.status !== "unsupported").map((c, i) => (
                            <p className="answer-summary" key={i}>{c.text}{citations(c)}</p>
                          ))
                        ) : (
                          <p className="answer-summary answer-unavailable">{project.analysis.mode !== "synthesized"
                            ? "The AI could not complete a summary for this run. See the reason above, then choose Research again."
                            : "The available passages do not support a cited summary yet. Review the findings below."}</p>
                        )}
                      </section>
                      {!!project.analysis.findings?.length && <section className="answer-section">
                        <h3>{project.analysis.mode === "extractive" ? "Relevant source passages" : "Key findings"}</h3>
                        {(project.analysis.findings ?? project.analysis.papers.flatMap((p) => p.claims))
                          .filter((c) => c.status !== "unsupported")
                          .map((c, i) => {
                            const sourceTitle = project.analysis.evidence?.find((e) => e.id === c.sources[0]?.id)?.title;
                            return <div className="finding" key={i}>
                              <span className="finding-dimension">{c.dimension}{sourceTitle ? " · " + sourceTitle : ""}</span>
                              <p>{c.text}{citations(c)}</p>
                            </div>;
                          })}
                      </section>}
                      {project.analysis.mode === "synthesized" && <div className="answer-end">
                        <Check size={15} />
                        Review the linked sources before relying on this summary.
                      </div>}
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
              ) : tab === "Compare" ? (
                <div className="comparison-panel">
                  <p className="comparison-note">Compare reported evidence. Different datasets and evaluation methods may make results incomparable.</p>
                  {project?.analysis.papers?.length ? (
                    <div className="comparison-scroll" tabIndex={0} role="region" aria-label="Paper comparison">
                      <table className="comparison-table">
                        <thead><tr><th scope="col">Evidence</th>{project.analysis.papers.map(p => <th scope="col" key={p.paper_id}>{p.title}</th>)}</tr></thead>
                        <tbody>{["Method", "Dataset", "Results", "Limitations"].map(dimension => (
                          <tr key={dimension}><th scope="row">{dimension}</th>{project.analysis.papers!.map(p => {
                            const claims = p.claims.filter(c => c.status !== "unsupported" && c.dimension.toLowerCase().replace(/s$/, "") === dimension.toLowerCase().replace(/s$/, ""));
                            return <td key={p.paper_id}>{claims.length ? claims.map((c, i) => <p key={i}>{c.text}{citations(c)}</p>) : <span className="not-reported">Not reported in extracted findings</span>}</td>;
                          })}</tr>
                        ))}</tbody>
                      </table>
                    </div>
                  ) : <div className="empty-state"><BookOpen size={30}/><h2>Evidence comes first.</h2><p>Analyze your selected papers to compare their findings here.</p></div>}
                </div>
              ) : tab === "Sources" ? (
                <div className="sources-list">
                  <div className="workspace-tools">
                    <p>Select up to 20 papers, then rebuild your answer. Changing the selection clears the previous findings.</p>
                    <button className="button" disabled={!!busy || running || !papers.some(p => p.selected)} onClick={() => runStep("refine")}>Analyze selected papers</button>
                    <label className="quiet-button upload-label">Add PDF
                      <input aria-label="Add PDF to research" type="file" accept="application/pdf" disabled={!!busy || running} onChange={e => {
                        const file = e.target.files?.[0]; e.target.value = "";
                        if (file) action("upload", async () => {
                          const form = new FormData(); form.append("file", file);
                          await api("/projects/" + id + "/upload", {method: "POST", body: form});
                          await load(id!);
                        });
                      }}/>
                    </label>
                  </div>
                  {papers
                    .map((p, i) => (
                      <article className="source-card" key={p.id}>
                        <input type="checkbox" aria-label={"Include " + p.title} checked={p.selected} disabled={!!busy || running || (!p.selected && papers.filter(p => p.selected).length >= 20)} onChange={e => {
                          const selected = e.target.checked;
                          setPapers(current => current.map(paper => paper.id === p.id ? {...paper, selected} : paper));
                          action("selection", async () => {
                            try {
                              await api("/projects/" + id + "/papers/" + p.id, {method: "PATCH", body: JSON.stringify({selected})});
                            } catch (error) {
                              setPapers(current => current.map(paper => paper.id === p.id ? {...paper, selected: !selected} : paper));
                              throw error;
                            }
                            await load(id!);
                          });
                        }}/>
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
                          <span className="eyebrow">RESEARCH DIRECTION {i + 1}</span>
                          <h3 className="gap-question">{c.text}</h3>
                          {c.rationale && <p>{c.rationale}{citations(c)}</p>}
                          {c.next_step && <p><strong>How to investigate:</strong> {c.next_step}</p>}
                        </div>
                      </article>
                    ))
                  ) : (
                    <div className="empty-state">
                      <Leaf size={30} />
                      <h2>There’s always more to explore.</h2>
                      <p>
                        {config?.ai_configured
                          ? "The selected passages did not support a specific research direction. Try adding more relevant papers or a full-text PDF."
                          : "No synthesized research gaps are available for this run."}
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
                  <form key={project.plan.queries.join("|")} onSubmit={e => {
                    e.preventDefault();
                    const data = new FormData(e.currentTarget);
                    const queries = String(data.get("queries")).split("\n").map(q => q.trim()).filter(Boolean);
                    action("discover", async () => {
                      await api("/projects/" + id + "/plan", {method: "PATCH", body: JSON.stringify({queries})});
                      await api("/projects/" + id + "/run/discover", post());
                      await load(id!); setTab("Sources");
                    });
                  }}>
                    <label htmlFor="search-queries">Search queries (one per line, up to 3)</label>
                    <textarea id="search-queries" name="queries" rows={5} required defaultValue={project.plan.queries.join("\n")} disabled={running || !!busy}/>
                    <button className="quiet-button" disabled={running || !!busy}>Find more papers</button>
                  </form>
                </div>
              )}
              <button className="quiet-button delete-project" disabled={running || !!busy} onClick={() => setModal("delete-project")}>Delete this research</button>
            </aside>
          </div>
        </main>
      )}
      {modal === "library" && (
        <Modal title="Conversation history" close={() => setModal("")} wide>
          <p className="modal-description">
            {isGuest(user)
              ? "Your past questions and results, saved as text. Create an account to read them on another device."
              : "Read your past questions, results, and conversations. Saved sessions are read-only."}
          </p>
          {libraryBusy ? (
            <div className="library-empty"><Loader2 className="spin" size={20} /> Loading your research…</div>
          ) : libraryError ? (
            <div className="library-empty" role="alert">
              <AlertCircle size={23} />
              <h3>Conversation history unavailable</h3>
              <p>{libraryError}</p>
              <button className="button" onClick={openLibrary}>Try again</button>
            </div>
          ) : library.length ? (
            <div className="history-list">
              {library.map((item) => (
                <button key={item.id} disabled={!!busy} onClick={() => action("history", async () => { await closeActive(); await api("/projects/" + item.id + "/archive", post()); historyRequests.current.add(item.id); setModal(""); navigate(item.id); await load(item.id); })}>
                  <span><BookOpen size={17} /></span>
                  <div>
                    <strong>{item.title}</strong>
                    <small>{new Date(item.created).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}</small>
                  </div>
                  <ChevronRight size={16} />
                </button>
              ))}
            </div>
          ) : (
            <div className="library-empty">
              <BookOpen size={24} />
              <h3>No research saved yet</h3>
              <p>Ask a question to start your first research workspace.</p>
              <button className="button" onClick={() => { setModal(""); navigate(null); }}>Start a question</button>
            </div>
          )}
          {isGuest(user) && !libraryBusy && (
            <button className="quiet-button library-account-link" onClick={() => { setAuthMode("register"); setAuthError(""); setModal("auth"); }}>
              Create an account to keep this research
              <ArrowUpRight size={15} />
            </button>
          )}
        </Modal>
      )}
      {modal === "auth" && (
        <Modal title={authMode === "login" ? "Sign in" : "Create your account"} close={() => setModal("")}>
          <p className="modal-description">
            {authMode === "login"
              ? "Read your conversation history on any device. Guest conversations in this browser will join your account."
              : "Keep your questions, conversations, and result text in one place."}
          </p>
          <form className="account-form" onSubmit={submitAuth}>
            {authMode === "register" && (
              <label>Your name<input name="name" autoComplete="name" required maxLength={100} placeholder="Your name" /></label>
            )}
            <label>Email<input name="email" type="email" autoComplete="email" required maxLength={254} placeholder="you@example.com" /></label>
            <label>Password<input name="password" type="password" autoComplete={authMode === "login" ? "current-password" : "new-password"} required minLength={8} maxLength={256} placeholder="At least 8 characters" /></label>
            {authError && <p className="form-error" role="alert">{authError}</p>}
            <button className="button account-submit" disabled={authBusy}>
              {authBusy ? <Loader2 size={16} className="spin" /> : authMode === "login" ? "Sign in" : "Create account"}
            </button>
          </form>
          <div className="account-switch">
            {authMode === "login" ? "New to ResearchOS?" : "Already have an account?"}
            <button onClick={() => { setAuthMode(authMode === "login" ? "register" : "login"); setAuthError(""); }}>
              {authMode === "login" ? "Create an account" : "Sign in"}
            </button>
          </div>
        </Modal>
      )}
      {modal === "account" && user && !isGuest(user) && (
        <Modal title="Your account" close={() => setModal("")}>
          <div className="settings-intro">
            <span><UserRound size={19} /></span>
            <div><h3>{user.name}</h3><p>{user.email}</p></div>
          </div>
          <p className="session-note">Your conversation history is saved as text. This browser stays signed in for up to 30 days.</p>
          <div className="account-actions">
            <button className="quiet-button" onClick={openLibrary}><History size={15} /> Conversation history</button>
            <button className="quiet-button" disabled={!!busy} onClick={signOut}><LogOut size={15} /> Sign out</button>
          </div>
        </Modal>
      )}
      {modal === "delete-project" && (
        <Modal title="Delete this research?" close={() => setModal("")}>
          <p className="modal-description">This permanently removes the question, saved result, and conversation.</p>
          <div className="workspace-tools">
            <button className="quiet-button" onClick={() => setModal("")}>Keep research</button>
            <button className="button" disabled={!!busy} onClick={() => action("delete", async () => {
              await api("/projects/" + id, {method: "DELETE"});
              setModal(""); navigate(null);
            })}>Delete permanently</button>
          </div>
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
              {source.page > 0
                ? "An extracted paper passage. PDFs are discarded after reading; refer to the original publication for full context."
                : "The paper abstract. Open the original source for its full context."}
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
