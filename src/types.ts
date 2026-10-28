// Data returned by the Python API. These types describe objects; they do not fetch data.
export type Evidence = {
  id: string;
  paper_id: string;
  title: string;
  page: number;
  section: string;
  text: string;
  url: string;
  has_pdf: boolean;
};
export type Claim = {
  text: string;
  dimension: string;
  sources: { id: string; quote: string }[];
  status: string;
  rationale?: string;
  next_step?: string;
  kind?: "source_gap" | "source_limitation";
  gap?: string;
  comparison?: string;
  measure?: string;
};
export type Project = {
  readonly: boolean;
  id: string;
  title: string;
  question: string;
  status: string;
  created: string;
  report: string;
  paper_count: number;
  analysis: {
    mode?: string;
    note?: string;
    gap_status?: string;
    gap_note?: string;
    overview?: Claim[];
    findings?: Claim[];
    papers?: { paper_id: string; title: string; claims: Claim[] }[];
    gaps?: Claim[];
    evidence?: Evidence[];
    ideator?: IdeatorData;
  };
  plan: { queries?: string[]; scope?: string; warning?: string; ranking_warning?: string; coverage_note?: string; mode?: string };
};

export type RoadmapMilestone = {
  phase: string;
  task: string;
  milestone: string;
};

export type ThesisProposal = {
  id: string;
  title: string;
  category: "Direct Extension" | "Cross-Domain Application" | "Compute & Efficiency" | string;
  tagline: string;
  difficulty: "Accessible" | "Intermediate" | "Advanced" | string;
  compute: string;
  problem_statement: string;
  hypothesis: string;
  datasets_and_tools: string[];
  roadmap: RoadmapMilestone[];
  baseline_to_beat: string;
  potential_risks?: string;
};

export type PaperDigest = {
  title: string;
  authors: string;
  year?: number | string;
  core_problem: string;
  method_summary: string;
  key_findings: string[];
};

export type PaperGap = {
  area: string;
  gap: string;
  evidence: string;
};

export type IdeatorData = {
  digest: PaperDigest;
  gaps: PaperGap[];
  proposals: ThesisProposal[];
};
export type Paper = {
  id: string;
  title: string;
  authors: string;
  year: number;
  source: string;
  status: string;
  error: string;
  url: string;
  has_pdf: boolean;
  selected: boolean;
};
export type Job = {
  id: string;
  kind: string;
  status: string;
  progress: number;
  error: string;
  events: { stage?: string; text: string; time: string }[];
};
export type Message = {
  id: string;
  role: string;
  content: string;
  evidence: Evidence[];
};
export type User = { name: string; email: string };
export type ProjectSummary = Pick<Project, "id" | "title" | "created">;

export interface RagCitation {
  chunk_id: string;
  page: number;
  section: string;
  snippet: string;
  score: number;
}

export interface RagMessage {
  id?: string;
  role: "user" | "assistant";
  content: string;
  citations?: RagCitation[];
  created?: string;
}

export interface RagPaperStatus {
  has_paper: boolean;
  paper: {
    id?: string;
    title: string;
    authors?: string;
    year?: number;
    abstract?: string;
  } | null;
  chunks_count: number;
  pages_count: number;
  suggested_questions: string[];
}
