import styles from './ResultsPanel.module.css';
import type { MatchResponse, Characteristic } from '../types';
import ComparisonTable from './ComparisonTable';
import TopMatches from './TopMatches';

interface Props {
  result: MatchResponse | null;
  loading: boolean;
  error: string | null;
  selectedKeys: string[];
  characteristics?: Characteristic[];
}

function ScoreBadge({ pct }: { pct: number }) {
  const cls = pct >= 80 ? styles.badgeGreen : pct >= 55 ? styles.badgeYellow : styles.badgeGray;
  return <span className={`${styles.badge} ${cls}`}>Match score: {pct.toFixed(0)}%</span>;
}

export default function ResultsPanel({ result, loading, error, selectedKeys }: Props) {
  if (loading) {
    return (
      <section className={styles.card}>
        <div className={styles.empty}>
          <div className={styles.spinner} />
          <p>Finding best Nuvoton matches…</p>
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className={styles.card}>
        <div className={styles.errorBox}>
          <strong>Could not find a match</strong>
          <p>{error}</p>
          <p className={styles.errorHint}>
            Check that the part number is in the competitor catalog and at least one characteristic is selected.
          </p>
        </div>
      </section>
    );
  }

  if (!result) {
    return (
      <section className={styles.card}>
        <div className={styles.empty}>
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none" className={styles.emptyIcon}>
            <circle cx="24" cy="24" r="23" stroke="#dbe3ee" strokeWidth="2"/>
            <path d="M16 24h16M24 16v16" stroke="#dbe3ee" strokeWidth="2.5" strokeLinecap="round"/>
          </svg>
          <p>Enter a competitor part number and select comparison parameters to find the best-matching Nuvoton MCU.</p>
        </div>
      </section>
    );
  }

  const best = result.matches[0];
  const comp = result.competitor_part;

  return (
    <section className={styles.card}>
      {/* Header */}
      <div className={styles.resultHeader}>
        <div>
          <h2 className={styles.sectionTitle}>Best Match</h2>
          <p className={styles.sub}>
            Competitor: <strong>{comp.part_number}</strong>
            <span className={styles.dot}>·</span>
            {comp.manufacturer}
            <span className={styles.dot}>·</span>
            {comp.core}
            {comp.package && <><span className={styles.dot}>·</span>{comp.package}</>}
          </p>
        </div>
        <div className={styles.badges}>
          <ScoreBadge pct={best.similarity_pct} />
          {best.meets_all && (
            <span className={`${styles.badge} ${styles.badgeGreen}`}>All parameters met</span>
          )}
        </div>
      </div>

      {/* Best match card */}
      <div className={styles.matchCard}>
        <div className={styles.matchTop}>
          <div>
            <h3 className={styles.matchPart}>{best.nuvoton_part.part_number}</h3>
            <p className={styles.matchSub}>
              {best.nuvoton_part.manufacturer} · {best.nuvoton_part.family} · {best.nuvoton_part.core}
              {best.nuvoton_part.package && <> · {best.nuvoton_part.package}</>}
            </p>
          </div>
        </div>

        {/* Quick stats for best match */}
        <div className={styles.quickStats}>
          <div className={styles.stat}>
            <span className={styles.statK}>CPU</span>
            <span className={styles.statV}>{best.nuvoton_part.cpu_freq_mhz} MHz</span>
          </div>
          <div className={styles.stat}>
            <span className={styles.statK}>RAM</span>
            <span className={styles.statV}>{best.nuvoton_part.ram_kb} KB</span>
          </div>
          <div className={styles.stat}>
            <span className={styles.statK}>Flash</span>
            <span className={styles.statV}>{best.nuvoton_part.flash_kb} KB</span>
          </div>
          <div className={styles.stat}>
            <span className={styles.statK}>GPIO</span>
            <span className={styles.statV}>{best.nuvoton_part.gpio}</span>
          </div>
          <div className={styles.stat}>
            <span className={styles.statK}>USB FS/HS</span>
            <span className={styles.statV}>
              {best.nuvoton_part.usb ? 'FS' : '—'}
              {best.nuvoton_part.usb_hs ? '+HS' : ''}
            </span>
          </div>
          <div className={styles.stat}>
            <span className={styles.statK}>Ethernet</span>
            <span className={styles.statV}>{best.nuvoton_part.ethernet ? 'Yes' : 'No'}</span>
          </div>
          <div className={styles.stat}>
            <span className={styles.statK}>Temp</span>
            <span className={styles.statV}>−40 ~ {best.nuvoton_part.temp_max_c}°C</span>
          </div>
          {best.nuvoton_part.package && (
            <div className={styles.stat}>
              <span className={styles.statK}>Package</span>
              <span className={styles.statV}>{best.nuvoton_part.package}</span>
            </div>
          )}
        </div>

        {/* Failed parameters banner */}
        {!best.meets_all && (() => {
          const failed = best.comparison.filter(r => !r.nuvoton_better);
          return failed.length > 0 ? (
            <div className={styles.failedBanner}>
              <span className={styles.failedLabel}>Parameters not met: </span>
              {failed.map((r, i) => (
                <span key={r.key}>
                  {i > 0 && <span className={styles.failedSep}> · </span>}
                  <span className={styles.failedParam}>{r.label}</span>
                  {r.competitor_display
                    ? ` (need ${r.competitor_display}, got ${r.nuvoton_display ?? '—'})`
                    : r.unit
                      ? ` (need ${r.competitor_value} ${r.unit}, got ${r.nuvoton_value} ${r.unit})`
                      : ''}
                </span>
              ))}
            </div>
          ) : null;
        })()}

        {/* Comparison table */}
        <div className={styles.tableSection}>
          <h4 className={styles.tableTitle}>Parameter comparison</h4>
          <ComparisonTable
            rows={best.comparison}
            competitorPart={comp.part_number}
            nuvotonPart={best.nuvoton_part.part_number}
          />
        </div>

        {best.nuvoton_part.notes && (
          <p className={styles.notes}>
            <strong>Notes:</strong> {best.nuvoton_part.notes}
          </p>
        )}
      </div>

      {/* Top matches */}
      {result.matches.length > 1 && (
        <>
          <h3 className={styles.topTitle}>All top {result.matches.length} Nuvoton matches</h3>
          <TopMatches matches={result.matches} />
        </>
      )}

      <p className={styles.footnote}>
        Matching uses weighted KNN similarity across the {selectedKeys.length} selected parameter{selectedKeys.length !== 1 ? 's' : ''}.
        {' '}Higher score = closer spec match. Verify availability and pricing with Nuvoton sales.
      </p>
    </section>
  );
}
