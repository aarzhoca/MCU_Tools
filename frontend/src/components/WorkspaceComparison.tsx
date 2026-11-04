import { useEffect, useRef, useState } from 'react';
import styles from './ImportModal.module.css';

type Cell = { part_number: string; value: unknown; status: string; quality: string };
export type ComparisonSnapshot = { generated_at: string; catalog_sha256: string; disclaimer: string; warnings: string[];
  source: { part_number: string }; candidates: { part_number: string; eligibility: string; field_sources: Record<string, unknown> }[];
  rows: { field: string; label: string; unit: string; requirements: string; source_value: unknown; source_quality: string; candidates: Cell[] }[] };
const text = (value: unknown) => value == null ? 'Unknown' : String(value);

export default function WorkspaceComparison({ snapshotJSON, token }: { snapshotJSON: string; token: string }) {
  const snapshot = JSON.parse(snapshotJSON) as ComparisonSnapshot;
  const [selected, setSelected] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const active = useRef<AbortController | null>(null);
  useEffect(() => () => active.current?.abort(), []);
  function toggle(name: string) {
    active.current?.abort(); active.current = null; setBusy(false); setError(null);
    setSelected(old => old.includes(name) ? old.filter(value => value !== name) : old.length < 3 ? [...old, name] : old);
  }
  async function download() {
    const controller = new AbortController(); active.current = controller;
    setBusy(true); setError(null);
    try {
      const response = await fetch('/api/workspace/export-xlsx', { method: 'POST', signal: controller.signal,
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ snapshot_json: snapshotJSON, token, selected }) });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(typeof body?.detail === 'string' ? body.detail : `Export failed (${response.status})`);
      }
      const blob = await response.blob();
      if (controller.signal.aborted || active.current !== controller) return;
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a'); link.href = url; link.download = 'mcu-comparison.xlsx';
      document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (reason) {
      if (!controller.signal.aborted && active.current === controller) setError(reason instanceof Error ? reason.message : 'Export failed');
    } finally { if (active.current === controller) setBusy(false); }
  }
  return <section>
    <h3>Comparison and Excel export</h3>
    <p>Select one to three returned candidates. UNKNOWN/FAIL records may be compared but are not recommendations.</p>
    <div className={styles.toggleRow}>{snapshot.candidates.map(candidate => <label key={candidate.part_number}>
      <input type="checkbox" checked={selected.includes(candidate.part_number)}
        disabled={selected.length >= 3 && !selected.includes(candidate.part_number)} onChange={() => toggle(candidate.part_number)} />
      {candidate.part_number} — {candidate.eligibility}
    </label>)}</div>
    {selected.length > 0 && <>
      <p className={styles.hint}>Snapshot: {snapshot.generated_at}. {snapshot.disclaimer}</p>
      <div className={styles.previewTable}><table>
        <thead><tr><th>Parameter</th><th>Unit</th><th>Customer requirement</th><th>{snapshot.source.part_number} source</th>
          {selected.map(name => <th key={name}>{name}</th>)}</tr></thead>
        <tbody>{snapshot.rows.map(row => <tr key={row.field}>
          <td>{row.label}</td><td>{row.unit}</td><td>{row.requirements}</td>
          <td>{text(row.source_value)}<br />{row.source_quality}</td>
          {selected.map(name => { const cell = row.candidates.find(item => item.part_number === name)!;
            return <td key={name}>{text(cell.value)}<br />{cell.status} · {cell.quality}</td>; })}
        </tr>)}</tbody>
      </table></div>
      <details><summary>Evidence references and snapshot identity</summary>
        <p className={styles.hint}>Catalog SHA-256: {snapshot.catalog_sha256}</p>
        {snapshot.candidates.filter(candidate => selected.includes(candidate.part_number)).map(candidate =>
          <pre key={candidate.part_number} style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{candidate.part_number}: {JSON.stringify(candidate.field_sources, null, 2)}</pre>)}
        {snapshot.warnings.map((warning, index) => <p key={index}>{warning}</p>)}
      </details>
      <button type="button" className={styles.btnPrimary} disabled={busy} onClick={download}>{busy ? 'Exporting…' : 'Export comparison to Excel'}</button>
    </>}
    {error && <p className={styles.error} role="alert">{error}</p>}
  </section>;
}
