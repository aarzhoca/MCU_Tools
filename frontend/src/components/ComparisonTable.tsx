import styles from './ComparisonTable.module.css';
import type { ComparisonRow } from '../types';

// Maps CORE_RANK value → display name (mirrors backend CORE_RANK table)
const RANK_TO_CORE: Record<number, string> = {
  10: 'Cortex-M55+NPU', 9: 'Cortex-M55', 8: 'Cortex-M7',
  7: 'Cortex-M33/M4F', 6: 'Cortex-M3/M4', 5: 'Cortex-M23/RISC-V',
  4: 'Cortex-M0+', 3: 'Cortex-M0', 2: 'PIC', 1: '8051',
};

interface Props {
  rows: ComparisonRow[];
  competitorPart: string;
  nuvotonPart: string;
}

function RatioBar({ pct, nuvotonBetter }: { pct: number; nuvotonBetter: boolean }) {
  const color = nuvotonBetter ? '#16a34a' : pct >= 70 ? '#d97706' : '#dc2626';
  return (
    <div className={styles.barWrap}>
      <div className={styles.barTrack}>
        <div className={styles.barFill} style={{ width: `${Math.min(pct, 100)}%`, background: color }} />
      </div>
      <span className={styles.barPct} style={{ color }}>{pct.toFixed(0)}%</span>
    </div>
  );
}

function StatusBadge({ nuvotonBetter }: { nuvotonBetter: boolean }) {
  return nuvotonBetter ? (
    <span className={`${styles.badge} ${styles.badgeMeets}`}>Meets</span>
  ) : (
    <span className={`${styles.badge} ${styles.badgeBelow}`}>Below</span>
  );
}

export default function ComparisonTable({ rows, competitorPart, nuvotonPart }: Props) {
  function fmt(val: number, unit: string, key: string): string {
    if (key === 'core') return RANK_TO_CORE[val] ?? `Class ${val}`;
    if (unit === '' && (val === 0 || val === 1)) return val === 1 ? 'Yes' : 'No';
    if (unit && unit !== 'class') return `${val} ${unit}`;
    return String(val);
  }

  function fmtDelta(row: ComparisonRow): string {
    if (row.key === 'core' || row.competitor_display != null || row.nuvoton_display != null) return '—';
    const isBoolean = row.unit === '' && (row.competitor_value === 0 || row.competitor_value === 1);
    if (isBoolean) return '—';
    const delta = row.nuvoton_value - row.competitor_value;
    if (delta === 0) return '=';
    const d = delta % 1 === 0 ? delta : parseFloat(delta.toFixed(2));
    return `${delta > 0 ? '+' : ''}${d}`;
  }

  return (
    <table className={styles.table}>
      <thead>
        <tr>
          <th>Parameter</th>
          <th>{competitorPart}</th>
          <th className={styles.nuvotonCol}>Nuvoton {nuvotonPart}</th>
          <th>Score</th>
          <th>Status</th>
          <th>Delta</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(row => (
          <tr key={row.key} className={row.nuvoton_better ? '' : styles.rowBelow}>
            <td className={styles.paramName}>{row.label}</td>
            <td>{row.competitor_display ?? fmt(row.competitor_value, row.unit, row.key)}</td>
            <td className={`${styles.nuvotonCol} ${row.nuvoton_better ? styles.textMeets : styles.textBelow}`}>
              {row.nuvoton_display ?? fmt(row.nuvoton_value, row.unit, row.key)}
            </td>
            <td><RatioBar pct={row.similarity_pct} nuvotonBetter={row.nuvoton_better} /></td>
            <td><StatusBadge nuvotonBetter={row.nuvoton_better} /></td>
            <td className={`${styles.delta} ${row.nuvoton_better ? styles.deltaPos : styles.deltaNeg}`}>
              {fmtDelta(row)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
