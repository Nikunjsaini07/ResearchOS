import type { Claim, Evidence } from "./types";

type Props = {
  claims: Claim[];
  evidence: Evidence[];
  status?: string;
  note?: string;
  busy: boolean;
  canRetry: boolean;
  onRetry: () => void;
  onOpen: (id: string, claim: Claim) => void;
};

export function ResearchGaps({ claims, evidence, status, note, busy, canRetry, onRetry, onOpen }: Props) {
  const supported = claims.filter(c =>
    c.status !== "unsupported" && c.sources?.length &&
    ((c.kind === "source_gap" && c.gap && c.comparison && c.measure) || c.kind === "source_limitation"));
  const hasGap = supported.some(c => c.kind === "source_gap");
  const legacy = claims.some(c => !c.kind);

  return <section className="gaps-list" aria-labelledby="gaps-heading">
    <header className="gap-intro">
      <h2 id="gaps-heading">{hasGap ? "What remains unanswered" : "Research gaps"}</h2>
      <p>{hasGap
        ? "Each gap below connects an unresolved source limitation to a study you could run."
        : "A gap needs evidence of something unresolved. A paper’s successful result alone does not establish one."}</p>
    </header>
    {supported.map((claim, index) => <article className="gap-card" key={index}>
      <div>
        <span className="eyebrow">{claim.kind === "source_gap" ? `SOURCE-SUPPORTED GAP ${index + 1}` : "AUTHOR-STATED LIMITATION"}</span>
        <h3 className="gap-question">{claim.gap || claim.text}</h3>
        {claim.kind === "source_gap" && <>
          <p className="gap-research-question"><strong>Question:</strong> {claim.text}</p>
          <p><strong>Why it matters:</strong> {claim.rationale}</p>
        </>}
        <div className="gap-evidence">
          <span className="eyebrow">SUPPORTING SOURCE</span>
          {claim.sources.map(ref => {
            const source = evidence.find(e => e.id === ref.id);
            return <div key={ref.id}>
              <blockquote>{ref.quote}</blockquote>
              <button className="gap-source-link" onClick={() => onOpen(ref.id, claim)}>
                Read source: {source?.title || "Supporting passage"}
                {source?.page ? ` · p. ${source.page}` : " · abstract"}
              </button>
            </div>;
          })}
        </div>
        {claim.kind === "source_gap" ? <div className="gap-study">
          <h4>A study to test it</h4>
          <p>{claim.next_step}</p>
          <dl>
            <div><dt>Measure</dt><dd>{claim.measure}</dd></div>
          </dl>
        </div> : <p className="gap-limit-note">This is a limitation reported by the authors. It has not been developed into a validated research gap.</p>}
      </div>
    </article>)}
    {!supported.length && <div className="gap-empty" role="status">
      <h3>{status === "unavailable" && !legacy ? "Gap analysis could not finish" : "No supported research gap found"}</h3>
      <p>{legacy
        ? "Regenerate this analysis to check the proposed gaps against explicit source limitations."
        : note || "Add relevant full-text papers with limitations or future-work sections. The current evidence does not establish a specific gap."}</p>
    </div>}
    {canRetry && (legacy || status === "unavailable" || !supported.length) &&
      <button className="button" disabled={busy} onClick={onRetry}>{busy ? "Analyzing sources…" : "Regenerate answer and gaps"}</button>}
    {hasGap && <p className="gap-note">Supported within the selected papers. Check the wider literature before claiming novelty.</p>}
  </section>;
}
