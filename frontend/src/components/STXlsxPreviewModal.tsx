import { useEffect, useRef, useState } from 'react';
import styles from './ImportModal.module.css';
import STWorkspacePanel from './STWorkspacePanel';
import type { WorkspaceSource } from './STWorkspacePanel';

type RecordPreview = WorkspaceSource & { field_quality: Record<string, string>;
  source: { file: string; sheet: string; row: number; sha256: string } };
type Preview = { parsed_count: number; matched_count: number; error_count: number;
  records: RecordPreview[]; errors: { row: number; part: string; error: string }[];
  warnings: string[]; mapping: Record<string, string>; exact_query: string };
const display = (value: unknown) => value == null ? 'Unknown' : String(value);
const COLUMNS = ['core', 'cpu_freq_mhz', 'flash_kb', 'ram_kb', 'package', 'temp_min_c', 'temp_max_c', 'vcc_min', 'vcc_max'];

export default function STXlsxPreviewModal({ onClose }: { onClose: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [sheet, setSheet] = useState('ProductsList');
  const [query, setQuery] = useState('');
  const [preview, setPreview] = useState<Preview | null>(null);
  const [workspace, setWorkspace] = useState<WorkspaceSource | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  function reset() {
    controller.current?.abort(); controller.current = null;
    setPreview(null); setError(null); setLoading(false);
  }
  async function loadPreview() {
    if (!file) { setError('Select an ST .xlsx workbook.'); return; }
    if (!file.name.toLowerCase().endsWith('.xlsx') || file.size > 20 * 1024 * 1024) {
      setError('Select an .xlsx workbook no larger than 20 MiB.'); return;
    }
    reset(); const active = new AbortController(); controller.current = active; setLoading(true);
    const form = new FormData();
    form.append('file', file); form.append('sheet', sheet); form.append('part_number', query);
    try {
      const response = await fetch('/api/chips/competitor/st-xlsx-preview', { method: 'POST', body: form, signal: active.signal });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(typeof body?.detail === 'string' ? body.detail : `Preview failed (${response.status})`);
      }
      const body = await response.json() as Preview;
      if (controller.current === active) setPreview(body);
    } catch (reason) {
      if (!active.signal.aborted && controller.current === active) setError(reason instanceof Error ? reason.message : 'Preview failed');
    } finally { if (controller.current === active) setLoading(false); }
  }
  return <div className={styles.overlay}>
    <div className={styles.modal} role="dialog" aria-modal="true" aria-label="ST Excel preview">
      <div className={styles.modalHeader}><h2 className={styles.modalTitle}>ST Excel preview / temporary workspace</h2>
        <button type="button" className={styles.closeBtn} aria-label="Close preview" onClick={onClose}>×</button></div>
      <div className={styles.body}>
        {workspace ? <STWorkspacePanel key={workspace.part_number} source={workspace} onClear={() => setWorkspace(null)} /> :
        <div className={styles.tabContent}>
          <p className={styles.hint}>No catalog changes. Select a preview record for temporary matching.
            CSV/manual imports remain a separate legacy workflow.</p>
          <label>ST workbook (.xlsx, maximum 20 MiB)<input type="file" accept=".xlsx" onChange={event => { reset(); setFile(event.target.files?.[0] ?? null); }} /></label>
          <label>Worksheet<input className={styles.input} maxLength={100} value={sheet} onChange={event => { reset(); setSheet(event.target.value); }} /></label>
          <label>Exact part number (leave blank for first 20 records)<input className={styles.input} maxLength={100} placeholder="STM32F051C6T6" value={query} onChange={event => { reset(); setQuery(event.target.value); }} /></label>
          <button type="button" className={styles.btnPrimary} disabled={!file || loading} onClick={loadPreview}>{loading ? 'Reading workbook…' : 'Preview workbook'}</button>
          <p className={styles.hint} aria-live="polite">{loading ? 'Processing selected workbook.' : ''}</p>
          {error && <p className={styles.error} role="alert">{error}</p>}
          {preview && <>
            <p>{preview.parsed_count} parsed records · {preview.matched_count} exact/filter matches · {preview.error_count} rejected rows. Showing {preview.records.length} records.</p>
            {preview.warnings.map((warning, index) => <p className={styles.hint} key={index}>{warning}</p>)}
            {preview.exact_query && preview.matched_count === 0 && <p className={styles.error}>Exact part not found. No fuzzy substitute was selected.</p>}
            <details><summary>Column mapping and normalization</summary><ul>{Object.entries(preview.mapping).map(([target, source]) => <li key={target}>{source} → {target}</li>)}</ul>
              <p>Core uses explicit FPU data. Unmapped peripherals stay Unknown. Package dimensions are not pin compatibility.</p></details>
            <div className={styles.previewTable}><table>
              <thead><tr><th>Action</th><th>Part</th><th>Core</th><th>MHz</th><th>Flash KB</th><th>RAM KB</th><th>Package</th><th>Min °C</th><th>Max °C</th><th>Min V</th><th>Max V</th></tr></thead>
              <tbody>{preview.records.map(record => <tr key={record.part_number}>
                <td><button type="button" onClick={() => { controller.current?.abort(); setWorkspace(record); }}>Use this part</button></td>
                <td>{record.part_number}</td>{COLUMNS.map(key => <td key={key}>{display(record[key])}</td>)}
              </tr>)}</tbody>
            </table></div>
            <details><summary>Unknown fields and source references</summary>{preview.records.map(record => <p key={record.part_number} className={styles.hint}>
              {record.part_number}: {Object.entries(record.field_quality).filter(([, quality]) => quality === 'unknown').map(([field]) => field).join(', ') || 'No unknown normalized fields'}.
              {' '}Source: {record.source.file}, {record.source.sheet}, row {record.source.row}. SHA-256: {record.source.sha256}
            </p>)}</details>
            {preview.error_count > 0 && <details><summary>Rejected rows (first 20)</summary><ul>{preview.errors.map((item, index) => <li key={index}>Row {item.row}, {item.part}: {item.error}</li>)}</ul></details>}
          </>}
        </div>}
      </div>
    </div>
  </div>;
}
