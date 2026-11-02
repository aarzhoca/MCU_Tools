import styles from './TopMatches.module.css';
import type { MatchResult } from '../types';

interface Props {
  matches: MatchResult[];
}

export default function TopMatches({ matches }: Props) {
  return (
    <div className={styles.grid}>
      {matches.map((m, i) => (
        <div key={m.nuvoton_part.part_number} className={`${styles.card} ${i === 0 ? styles.best : ''}`}>
          <div className={styles.rank}>#{i + 1}</div>
          <div className={styles.part}>{m.nuvoton_part.part_number}</div>
          <div className={styles.family}>{m.nuvoton_part.family} · {m.nuvoton_part.core}</div>
          <div className={styles.score}>{m.similarity_pct.toFixed(0)}% match</div>
          {m.meets_all && <div className={styles.meetsAll}>All params met ✓</div>}
          <div className={styles.specs}>
            <span>{m.nuvoton_part.cpu_freq_mhz} MHz</span>
            <span>{m.nuvoton_part.ram_kb} KB RAM</span>
            <span>{m.nuvoton_part.flash_kb} KB Flash</span>
          </div>
        </div>
      ))}
    </div>
  );
}
