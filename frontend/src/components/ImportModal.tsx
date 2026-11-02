import { useState, useRef, useCallback } from 'react';
import styles from './ImportModal.module.css';
import { importCSV, addCompetitorPart, convertCsvPreview, bulkImport } from '../api';
import type { ImportResult, ConvertPreview } from '../api';
import type { ChipSpec } from '../types';

interface Props {
  onClose: () => void;
  onImported: (count: number) => void;
}

const MANUFACTURERS = [
  'STMicroelectronics', 'NXP', 'Microchip', 'Texas Instruments',
  'Renesas', 'Espressif', 'Infineon', 'Nordic Semiconductor',
  'Silicon Labs', 'Atmel', 'Other',
];

const CORES = [
  'Cortex-M0', 'Cortex-M0+', 'Cortex-M3', 'Cortex-M4',
  'Cortex-M4F', 'Cortex-M7', 'Cortex-M23', 'Cortex-M33',
  'Cortex-M55', 'RISC-V', 'Xtensa LX7', 'MIPS32',
  'AVR8', 'PIC', 'MSP430', '8051', 'Other',
];

const EMPTY_PART: ChipSpec = {
  part_number: '', manufacturer: '', family: '', core: '',
  cpu_freq_mhz: 0, ram_kb: 0, flash_kb: 0, gpio: 0,
  adc_bits: 12, adc_channels: 0, uart: 0, spi: 0, i2c: 0,
  usb: 0, usb_hs: 0, can: 0, can_fd: 0, ethernet: 0, crypto: 0,
  temp_max_c: 85, vcc_min: 1.8, vcc_max: 3.6,
  package: '', notes: '',
};

// ── CSV Upload Tab ────────────────────────────────────────────────────────

function CsvTab({ onImported }: { onImported: (r: ImportResult) => void }) {
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback((f: File) => {
    if (!f.name.endsWith('.csv')) {
      setError('Please select a .csv file.');
      return;
    }
    setFile(f);
    setError(null);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, [handleFile]);

  async function handleUpload() {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const result = await importCSV(file);
      onImported(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed');
    } finally {
      setLoading(false);
    }
  }

  function downloadTemplate() {
    const headers = 'part_number,manufacturer,family,core,cpu_freq_mhz,ram_kb,flash_kb,gpio,adc_bits,adc_channels,uart,spi,i2c,usb,usb_hs,can,can_fd,ethernet,crypto,temp_max_c,vcc_min,vcc_max,package,notes';
    const example = 'STM32F446RE,STMicroelectronics,STM32F4,Cortex-M4F,180,128,512,51,12,16,6,4,3,1,0,0,0,0,0,85,1.7,3.6,LQFP64,FPU';
    const blob = new Blob([headers + '\n' + example + '\n'], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'competitor_template.csv';
    a.click();
  }

  return (
    <div className={styles.tabContent}>
      <p className={styles.hint}>
        Upload a CSV with competitor part specs. Download the template below to see the exact columns.
        Each row is one part — existing parts (same part number) will be updated.
      </p>

      <button className={styles.templateBtn} onClick={downloadTemplate} type="button">
        Download CSV template
      </button>

      <div
        className={`${styles.dropzone} ${dragging ? styles.dropzoneDrag : ''} ${file ? styles.dropzoneReady : ''}`}
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          className={styles.fileInput}
          onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])}
        />
        {file ? (
          <>
            <div className={styles.fileIcon}>CSV</div>
            <p className={styles.fileName}>{file.name}</p>
            <p className={styles.fileSize}>{(file.size / 1024).toFixed(1)} KB — click to change</p>
          </>
        ) : (
          <>
            <div className={styles.uploadIcon}>↑</div>
            <p className={styles.dropText}>Drag & drop a CSV here, or click to browse</p>
          </>
        )}
      </div>

      {error && <p className={styles.error}>{error}</p>}

      <button
        className={styles.btnPrimary}
        onClick={handleUpload}
        disabled={!file || loading}
        type="button"
      >
        {loading ? 'Importing…' : 'Import CSV'}
      </button>
    </div>
  );
}

// ── Add Single Part Tab ───────────────────────────────────────────────────

function AddPartTab({ onAdded }: { onAdded: (saved: ChipSpec) => void }) {
  const [part, setPart] = useState<ChipSpec>({ ...EMPTY_PART });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function set(key: keyof ChipSpec, value: string | number) {
    setPart(prev => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!part.part_number.trim()) { setError('Part number is required.'); return; }
    if (!part.manufacturer.trim()) { setError('Manufacturer is required.'); return; }
    if (!part.core.trim()) { setError('Core is required.'); return; }
    setLoading(true);
    setError(null);
    try {
      const saved = await addCompetitorPart(part);
      onAdded(saved);
      setPart({ ...EMPTY_PART });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className={styles.tabContent} onSubmit={handleSubmit}>
      <p className={styles.hint}>
        Fill in the key specs for one competitor part. Only Part Number, Manufacturer, and Core are required.
      </p>

      <div className={styles.formGrid}>
        {/* Identity */}
        <div className={styles.fieldFull}>
          <label className={styles.fieldLabel}>Part Number *</label>
          <input className={styles.input} placeholder="e.g. STM32F446RE"
            value={part.part_number}
            onChange={e => set('part_number', e.target.value.toUpperCase())} />
        </div>

        <div>
          <label className={styles.fieldLabel}>Manufacturer *</label>
          <select className={styles.input} value={part.manufacturer}
            onChange={e => set('manufacturer', e.target.value)}>
            <option value="">Select…</option>
            {MANUFACTURERS.map(m => <option key={m}>{m}</option>)}
          </select>
        </div>

        <div>
          <label className={styles.fieldLabel}>Family / Series</label>
          <input className={styles.input} placeholder="e.g. STM32F4"
            value={part.family} onChange={e => set('family', e.target.value)} />
        </div>

        <div>
          <label className={styles.fieldLabel}>CPU Core *</label>
          <select className={styles.input} value={part.core}
            onChange={e => set('core', e.target.value)}>
            <option value="">Select…</option>
            {CORES.map(c => <option key={c}>{c}</option>)}
          </select>
        </div>

        <div>
          <label className={styles.fieldLabel}>Package</label>
          <input className={styles.input} placeholder="e.g. LQFP64"
            value={part.package} onChange={e => set('package', e.target.value)} />
        </div>

        {/* Performance */}
        <NumField label="CPU Frequency" unit="MHz" value={part.cpu_freq_mhz}
          onChange={v => set('cpu_freq_mhz', v)} />
        <NumField label="RAM" unit="KB" value={part.ram_kb}
          onChange={v => set('ram_kb', v)} />
        <NumField label="Flash" unit="KB" value={part.flash_kb}
          onChange={v => set('flash_kb', v)} />
        <NumField label="GPIO Count" unit="pins" value={part.gpio}
          onChange={v => set('gpio', v)} isInt />
        <NumField label="ADC Resolution" unit="bits" value={part.adc_bits}
          onChange={v => set('adc_bits', v)} isInt />
        <NumField label="ADC Channels" unit="ch" value={part.adc_channels}
          onChange={v => set('adc_channels', v)} isInt />
        <NumField label="UART" unit="" value={part.uart}
          onChange={v => set('uart', v)} isInt />
        <NumField label="SPI" unit="" value={part.spi}
          onChange={v => set('spi', v)} isInt />
        <NumField label="I2C" unit="" value={part.i2c}
          onChange={v => set('i2c', v)} isInt />
        <NumField label="Max Temp" unit="°C" value={part.temp_max_c}
          onChange={v => set('temp_max_c', v)} />
        <NumField label="Min Voltage" unit="V" value={part.vcc_min}
          onChange={v => set('vcc_min', v)} step={0.1} />
        <NumField label="Max Voltage" unit="V" value={part.vcc_max}
          onChange={v => set('vcc_max', v)} step={0.1} />

        {/* Booleans */}
        <div className={styles.toggleRow}>
          <Toggle label="USB FS" checked={!!part.usb} onChange={v => set('usb', v ? 1 : 0)} />
          <Toggle label="USB HS" checked={!!part.usb_hs} onChange={v => set('usb_hs', v ? 1 : 0)} />
          <Toggle label="CAN (classic)" checked={!!part.can} onChange={v => set('can', v ? 1 : 0)} />
          <Toggle label="CAN FD" checked={!!part.can_fd} onChange={v => set('can_fd', v ? 1 : 0)} />
          <Toggle label="Ethernet" checked={!!part.ethernet} onChange={v => set('ethernet', v ? 1 : 0)} />
          <Toggle label="HW Crypto" checked={!!part.crypto} onChange={v => set('crypto', v ? 1 : 0)} />
        </div>

        <div className={styles.fieldFull}>
          <label className={styles.fieldLabel}>Notes (optional)</label>
          <input className={styles.input} placeholder="Special features, FPU, crypto, etc."
            value={part.notes ?? ''} onChange={e => set('notes', e.target.value)} />
        </div>
      </div>

      {error && <p className={styles.error}>{error}</p>}

      <button className={styles.btnPrimary} type="submit" disabled={loading}>
        {loading ? 'Saving…' : 'Add to catalog'}
      </button>
    </form>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────

function NumField({ label, unit, value, onChange, isInt = false, step = 1 }: {
  label: string; unit: string; value: number;
  onChange: (v: number) => void; isInt?: boolean; step?: number;
}) {
  return (
    <div>
      <label className={styles.fieldLabel}>{label}{unit && <span className={styles.unit}> ({unit})</span>}</label>
      <input
        className={styles.input} type="number" min={0} step={step}
        value={value || ''}
        placeholder="0"
        onChange={e => onChange(isInt ? parseInt(e.target.value || '0') : parseFloat(e.target.value || '0'))}
      />
    </div>
  );
}

function Toggle({ label, checked, onChange }: {
  label: string; checked: boolean; onChange: (v: boolean) => void;
}) {
  return (
    <label className={`${styles.toggle} ${checked ? styles.toggleOn : ''}`}>
      <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)} />
      {label}
    </label>
  );
}

// ── Convert any CSV tab ───────────────────────────────────────────────────

const FIELD_LABELS: Record<string, string> = {
  part_number:'Part Number', manufacturer:'Manufacturer', family:'Family',
  core:'Core', cpu_freq_mhz:'CPU Freq (MHz)', ram_kb:'RAM (KB)',
  flash_kb:'Flash (KB)', gpio:'GPIO', adc_bits:'ADC Bits',
  adc_channels:'ADC Ch', uart:'UART', spi:'SPI', i2c:'I2C',
  usb:'USB FS', usb_hs:'USB HS', can:'CAN (classic)', can_fd:'CAN FD',
  ethernet:'Ethernet', crypto:'HW Crypto',
  temp_max_c:'Max Temp', vcc_min:'VCC Min', vcc_max:'VCC Max',
  package:'Package', notes:'Notes',
};

function ConvertTab({ onImported }: { onImported: (r: ImportResult) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ConvertPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(f: File) {
    setFile(f); setPreview(null); setError(null);
    setLoading(true);
    try {
      const result = await convertCsvPreview(f);
      setPreview(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Detection failed');
    } finally {
      setLoading(false);
    }
  }

  async function handleImport() {
    if (!preview) return;
    setImporting(true); setError(null);
    try {
      const result = await bulkImport(preview.converted as ChipSpec[]);
      onImported(result as ImportResult);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Import failed');
    } finally {
      setImporting(false);
    }
  }

  return (
    <div className={styles.tabContent}>
      <p className={styles.hint}>
        Upload a CSV exported from <strong>any vendor's website</strong> — ST, NXP, Renesas,
        Microchip, TI, Espressif, etc. The tool auto-detects column names and maps them to
        the standard template. Review the mapping before confirming import.
      </p>

      <div
        className={`${styles.dropzone} ${preview ? styles.dropzoneReady : ''}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={e => e.preventDefault()}
        onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleFile(f); }}
      >
        <input ref={inputRef} type="file" accept=".csv" className={styles.fileInput}
          onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])} />
        {loading ? (
          <p className={styles.dropText}>Detecting columns…</p>
        ) : file ? (
          <>
            <div className={styles.fileIcon}>CSV</div>
            <p className={styles.fileName}>{file.name}</p>
            <p className={styles.fileSize}>Click to change file</p>
          </>
        ) : (
          <>
            <div className={styles.uploadIcon}>↑</div>
            <p className={styles.dropText}>Drag & drop any vendor CSV, or click to browse</p>
          </>
        )}
      </div>

      {error && <p className={styles.error}>{error}</p>}

      {preview && (
        <>
          {/* Mapping summary */}
          <div className={styles.mappingBox}>
            <div className={styles.mappingHeader}>
              <span className={styles.mappingTitle}>Column mapping detected</span>
              <span className={styles.mappingStats}>
                {Object.keys(preview.mapping).length} of {Object.keys(preview.mapping).length + preview.unmatched_columns.length} columns matched
                &nbsp;·&nbsp; {preview.convertible} of {preview.total_rows} rows convertible
              </span>
            </div>
            <div className={styles.mappingGrid}>
              {Object.entries(preview.mapping).map(([src, tgt]) => (
                <div key={src} className={styles.mappingRow}>
                  <span className={styles.mappingSrc}>{src}</span>
                  <span className={styles.mappingArrow}>→</span>
                  <span className={styles.mappingTgt}>{FIELD_LABELS[tgt] ?? tgt}</span>
                </div>
              ))}
            </div>
            {preview.unmatched_columns.length > 0 && (
              <p className={styles.unmatchedNote}>
                Ignored: {preview.unmatched_columns.join(', ')}
              </p>
            )}
          </div>

          {/* Preview rows */}
          <div className={styles.mappingHeader} style={{marginTop: 4}}>
            <span className={styles.mappingTitle}>Preview (first 5 rows)</span>
          </div>
          <div className={styles.previewTable}>
            <table>
              <thead>
                <tr><th>Part</th><th>Mfr</th><th>Core</th><th>MHz</th><th>RAM</th><th>Flash</th><th>USB</th><th>ETH</th></tr>
              </thead>
              <tbody>
                {preview.preview.map((p, i) => (
                  <tr key={i}>
                    <td><strong>{p.part_number || '—'}</strong></td>
                    <td>{p.manufacturer || '—'}</td>
                    <td>{p.core || '—'}</td>
                    <td>{p.cpu_freq_mhz || '—'}</td>
                    <td>{p.ram_kb ? `${p.ram_kb} KB` : '—'}</td>
                    <td>{p.flash_kb ? `${p.flash_kb} KB` : '—'}</td>
                    <td>{p.usb ? 'FS' : ''}{p.usb_hs ? '+HS' : ''}{!p.usb && !p.usb_hs ? '—' : ''}</td>
                    <td>{p.ethernet ? 'Yes' : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <button className={styles.btnPrimary} onClick={handleImport}
            disabled={importing || preview.convertible === 0} type="button">
            {importing ? 'Importing…' : `Import all ${preview.convertible} parts`}
          </button>
        </>
      )}
    </div>
  );
}

// ── Main Modal ────────────────────────────────────────────────────────────

export default function ImportModal({ onClose, onImported }: Props) {
  const [tab, setTab] = useState<'convert' | 'csv' | 'form'>('convert');
  const [result, setResult] = useState<ImportResult | null>(null);

  function handleImported(r: ImportResult) {
    setResult(r);
    onImported(r.added + r.updated);
  }

  function handleAdded(saved: ChipSpec) {
    onImported(1);
    setResult({ added: 1, updated: 0, total_in_catalog: 0, imported: [saved], errors: [] });
  }

  return (
    <div className={styles.overlay} onClick={e => e.target === e.currentTarget && onClose()}>
      <div className={styles.modal}>
        <div className={styles.modalHeader}>
          <h2 className={styles.modalTitle}>Add competitor parts</h2>
          <button className={styles.closeBtn} onClick={onClose} type="button">✕</button>
        </div>

        {result ? (
          <div className={styles.successBox}>
            <div className={styles.successIcon}>✓</div>
            <h3>{result.added > 0 ? `${result.added} new part${result.added !== 1 ? 's' : ''} added` : `${result.updated} part${result.updated !== 1 ? 's' : ''} updated`}</h3>
            {result.updated > 0 && result.added > 0 && (
              <p>{result.updated} existing part{result.updated !== 1 ? 's' : ''} updated</p>
            )}
            {result.total_in_catalog > 0 && (
              <p className={styles.total}>Catalog now contains {result.total_in_catalog} competitor parts</p>
            )}
            {result.errors.length > 0 && (
              <div className={styles.errorList}>
                <strong>Warnings:</strong>
                {result.errors.map((e, i) => <p key={i}>{e}</p>)}
              </div>
            )}
            {result.imported.length > 0 && (
              <div className={styles.previewTable}>
                <table>
                  <thead><tr><th>Part</th><th>Manufacturer</th><th>Core</th><th>MHz</th><th>RAM</th><th>Flash</th></tr></thead>
                  <tbody>
                    {result.imported.slice(0, 10).map(p => (
                      <tr key={p.part_number}>
                        <td><strong>{p.part_number}</strong></td>
                        <td>{p.manufacturer}</td>
                        <td>{p.core}</td>
                        <td>{p.cpu_freq_mhz}</td>
                        <td>{p.ram_kb} KB</td>
                        <td>{p.flash_kb} KB</td>
                      </tr>
                    ))}
                    {result.imported.length > 10 && (
                      <tr><td colSpan={6} style={{textAlign:'center', color:'#6b7280'}}>…and {result.imported.length - 10} more</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
            <div className={styles.successActions}>
              <button className={styles.btnPrimary} onClick={onClose}>Done</button>
              <button className={styles.btnSecondary} onClick={() => setResult(null)}>Import more</button>
            </div>
          </div>
        ) : (
          <>
            <div className={styles.tabs}>
              <button
                className={`${styles.tab} ${tab === 'convert' ? styles.tabActive : ''}`}
                onClick={() => setTab('convert')} type="button"
              >
                Any vendor CSV
              </button>
              <button
                className={`${styles.tab} ${tab === 'csv' ? styles.tabActive : ''}`}
                onClick={() => setTab('csv')} type="button"
              >
                Template CSV
              </button>
              <button
                className={`${styles.tab} ${tab === 'form' ? styles.tabActive : ''}`}
                onClick={() => setTab('form')} type="button"
              >
                Add single part
              </button>
            </div>

            <div className={styles.body}>
              {tab === 'convert' && <ConvertTab onImported={handleImported} />}
              {tab === 'csv' && <CsvTab onImported={handleImported} />}
              {tab === 'form' && <AddPartTab onAdded={(saved) => handleAdded(saved)} />}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
