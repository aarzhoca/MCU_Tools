import { useEffect, useRef, useState } from 'react';
import styles from './ImportModal.module.css';

export type WorkspaceSource = { part_number: string; [key: string]: unknown };
type Check = { field: string; operator: string; required_value: unknown; actual_value: unknown; status: string; reason: string };
type Candidate = { part_number: string; eligibility: string; similarity_pct?: number; reason?: string; requirement_checks: Check[];
  comparison?: { key: string; label: string; competitor_value: unknown; nuvoton_value: unknown }[] };
type Result = { matches: Candidate[]; failed_candidates: Candidate[]; unknown_candidates: Candidate[];
  unranked_candidates: Candidate[]; omitted_source_fields: string[]; ranked_count: number; unranked_count: number;
  eligibility_counts: Record<string, number>; message: string | null };
const FIELDS = [
  ['cpu_freq_mhz', 'Minimum frequency (MHz)', 'gte'], ['flash_kb', 'Minimum Flash (KB)', 'gte'],
  ['ram_kb', 'Minimum RAM (KB)', 'gte'], ['core', 'Exact core', 'eq'], ['package', 'Exact package', 'eq'],
  ['vcc_min', 'Must operate down to (V)', 'lte'], ['vcc_max', 'Must operate up to (V)', 'gte'],
  ['temp_min_c', 'Must operate down to (°C)', 'lte'], ['temp_max_c', 'Must operate up to (°C)', 'gte'],
] as const;
const text = (value: unknown) => value == null ? 'Unknown' : String(value);

export default function STWorkspacePanel({ source, onClear }: { source: WorkspaceSource; onClear: () => void }) {
  const [values, setValues] = useState<Record<string, string>>(() => Object.fromEntries(FIELDS.map(([key]) => [key, source[key] == null ? '' : String(source[key])])));
  const [required, setRequired] = useState<Record<string, boolean>>({ cpu_freq_mhz: true, flash_kb: true, ram_kb: true });
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const active = useRef<AbortController | null>(null);
  useEffect(() => () => active.current?.abort(), []);
  function invalidate() {
    active.current?.abort(); active.current = null;
    setResult(null); setError(null); setLoading(false);
  }
  async function match() {
    invalidate();
    const requirements: { field: string; operator: string; value: string | number }[] = [];
    for (const [field, , operator] of FIELDS) {
      if (!required[field]) continue;
      const raw = values[field].trim();
      const value = field === 'core' || field === 'package' ? raw : Number(raw);
      if (!raw || (typeof value === 'number' && !Number.isFinite(value))) {
        setError(`Enter a valid required value for ${field}.`); return;
      }
      requirements.push({ field, operator, value });
    }
    const controller = new AbortController(); active.current = controller; setLoading(true);
    try {
      const response = await fetch('/api/workspace/match', { method: 'POST', signal: controller.signal,
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ source, requirements, top_k: 5 }) });
      const body = await response.json();
      if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail));
      if (active.current === controller) setResult(body as Result);
    } catch (reason) {
      if (!controller.signal.aborted && active.current === controller) setError(reason instanceof Error ? reason.message : 'Matching failed');
    } finally { if (active.current === controller) setLoading(false); }
  }
  function candidates(title: string, items: Candidate[]) {
    return <section><h3>{title}</h3>{items.length === 0 ? <p>None shown.</p> : items.map((candidate, index) =>
      <details key={`${candidate.part_number}-${index}`}><summary>{candidate.part_number} — {candidate.eligibility}
        {candidate.similarity_pct != null ? ` — selected-spec similarity ${candidate.similarity_pct}%` : ''}</summary>
        {candidate.reason && <p>{candidate.reason}</p>}
        {candidate.requirement_checks.map((check, i) => <p key={i}>
          {check.field}: required {check.operator} {text(check.required_value)}; actual {text(check.actual_value)} — {check.status}
        </p>)}
        {candidate.comparison && <ul>{candidate.comparison.map(row => <li key={row.key}>
          {row.label}: source {text(row.competitor_value)}, candidate {text(row.nuvoton_value)}
        </li>)}</ul>}
      </details>)}</section>;
  }
  return <div className={styles.tabContent}>
    <h3>Temporary workspace: {source.part_number}</h3>
    <p className={styles.hint}>Stored only in this open dialog. Closing, clearing, or refreshing discards the selection.
      No master catalog changes. Source values below are not edited by customer requirements.</p>
    <details><summary>Uploaded source values and provenance</summary><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{JSON.stringify(source, null, 2)}</pre></details>
    <p>Required checks are prefilled from the source; edit them to the customer's needs. Unchecked fields do not gate eligibility.</p>
    {FIELDS.map(([key, label]) => <label key={key}>
      <input type="checkbox" checked={!!required[key]} onChange={event => { invalidate(); setRequired(old => ({ ...old, [key]: event.target.checked })); }} />
      {label} — source: {text(source[key])}
      <input className={styles.input} value={values[key]} type={key === 'core' || key === 'package' ? 'text' : 'number'} step="any"
        disabled={!required[key]} onChange={event => { invalidate(); setValues(old => ({ ...old, [key]: event.target.value })); }} />
    </label>)}
    <p className={styles.hint}>Ranking retains the existing frequency/GPIO/package-area/Flash/RAM factors.
      Missing base data blocks ranking. PASS means checked requirements only, not a drop-in replacement approval.</p>
    <button className={styles.btnPrimary} type="button" disabled={loading} onClick={match}>{loading ? 'Matching…' : 'Find Nuvoton candidates'}</button>
    <button className={styles.btnSecondary} type="button" onClick={() => { invalidate(); onClear(); }}>Clear workspace / return to preview</button>
    {error && <p className={styles.error} role="alert">{error}</p>}
    {result && <div aria-live="polite">
      <p>{result.ranked_count} rankable; {result.unranked_count} unranked. Requirement totals: {JSON.stringify(result.eligibility_counts)}.</p>
      <p>Up to five records shown per group. {result.message}</p>
      {result.omitted_source_fields.length > 0 && <p>Unknown source fields omitted from ranking: {result.omitted_source_fields.join(', ')}</p>}
      {candidates('Ranked candidates', result.matches)}
      {candidates('Failed mandatory checks', result.failed_candidates)}
      {candidates('Mandatory checks need verification', result.unknown_candidates)}
      {candidates('Not ranked: incomplete catalog data', result.unranked_candidates)}
    </div>}
  </div>;
}
