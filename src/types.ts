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
};
export type Project = {
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
    overview?: Claim[];
    findings?: Claim[];
    papers?: { paper_id: string; title: string; claims: Claim[] }[];
    gaps?: Claim[];
    evidence?: Evidence[];
  };
  plan: { queries?: string[] };
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
