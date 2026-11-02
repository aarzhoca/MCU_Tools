import { useState, useEffect, useRef } from 'react';
import styles from './SearchPanel.module.css';
import { searchCompetitorParts } from '../api';
import type { ChipSpec, Characteristic } from '../types';

const MIN_SELECT = 5;

const SAMPLE_PARTS = [
  'STM32F103C8', 'STM32F411CEU6', 'STM32H743VI',
  'ATMEGA328P', 'LPC55S69JBD100', 'ESP32-S3', 'RA4M1',
];

interface Props {
  characteristics: Characteristic[];
  selectedKeys: string[];
  onSelectedKeysChange: (keys: string[]) => void;
  partNumber: string;
  onPartNumberChange: (v: string) => void;
  onSearch: () => void;
  onReset: () => void;
  loading: boolean;
}

export default function SearchPanel({
  characteristics,
  selectedKeys,
  onSelectedKeysChange,
  partNumber,
  onPartNumberChange,
  onSearch,
  onReset,
  loading,
}: Props) {
  const [suggestions, setSuggestions] = useState<ChipSpec[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const allKeys = characteristics.map(c => c.key);
  const allSelected = allKeys.length > 0 && allKeys.every(k => selectedKeys.includes(k));
  const meetsMinimum = selectedKeys.length >= MIN_SELECT;

  useEffect(() => {
    if (partNumber.length < 2) {
      setSuggestions([]);
      setShowDropdown(false);
      return;
    }
    const t = setTimeout(() => {
      searchCompetitorParts(partNumber).then((parts) => {
        setSuggestions(parts.slice(0, 8));
        setShowDropdown(parts.length > 0);
      });
    }, 250);
    return () => clearTimeout(t);
  }, [partNumber]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (!dropdownRef.current?.contains(e.target as Node) &&
          !inputRef.current?.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  function toggleKey(key: string) {
    if (selectedKeys.includes(key)) {
      onSelectedKeysChange(selectedKeys.filter(k => k !== key));
    } else {
      onSelectedKeysChange([...selectedKeys, key]);
    }
  }

  function toggleAll() {
    if (allSelected) {
      onSelectedKeysChange([]);
    } else {
      onSelectedKeysChange(allKeys);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') onSearch();
  }

  const remaining = MIN_SELECT - selectedKeys.length;

  return (
    <section className={styles.card}>
      <h2 className={styles.sectionTitle}>Search</h2>

      <label className={styles.label} htmlFor="partInput">
        Competitor chip part number
      </label>
      <div className={styles.inputWrap}>
        <input
          id="partInput"
          ref={inputRef}
          className={styles.input}
          type="text"
          placeholder="e.g. STM32F103C8, ATMEGA328P, ESP32-S3"
          value={partNumber}
          onChange={e => onPartNumberChange(e.target.value)}
          onKeyDown={handleKeyDown}
          autoComplete="off"
        />
        {showDropdown && (
          <div ref={dropdownRef} className={styles.dropdown}>
            {suggestions.map(s => (
              <button
                key={s.part_number}
                className={styles.dropdownItem}
                type="button"
                onMouseDown={() => {
                  onPartNumberChange(s.part_number);
                  setShowDropdown(false);
                }}
              >
                <span className={styles.ddPart}>{s.part_number}</span>
                <span className={styles.ddMeta}>{s.manufacturer} · {s.core}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      <p className={styles.hint}>Sample parts to try:</p>
      <div className={styles.samples}>
        {SAMPLE_PARTS.map(p => (
          <button key={p} className={styles.sampleBtn} type="button"
            onClick={() => onPartNumberChange(p)}>
            {p}
          </button>
        ))}
      </div>

      <div className={styles.divider} />

      {/* Header row: label + Select All toggle */}
      <div className={styles.paramHeader}>
        <label className={styles.label} style={{ margin: 0 }}>
          Comparison parameters
        </label>
        <button
          className={`${styles.selectAllBtn} ${allSelected ? styles.selectAllActive : ''}`}
          type="button"
          onClick={toggleAll}
          disabled={characteristics.length === 0}
        >
          {allSelected ? 'Deselect all' : 'Select all'}
        </button>
      </div>

      <p className={styles.hint}>
        Select at least {MIN_SELECT}. Select all to compare across every parameter.
      </p>

      <div className={styles.grid}>
        {characteristics.map(c => {
          const checked = selectedKeys.includes(c.key);
          return (
            <label
              key={c.key}
              className={`${styles.choice} ${checked ? styles.choiceChecked : ''}`}
            >
              <input
                type="checkbox"
                checked={checked}
                onChange={() => toggleKey(c.key)}
              />
              <span className={styles.choiceLabel}>
                <span className={styles.choiceName}>{c.label}</span>
                {c.unit && <span className={styles.choiceUnit}>{c.unit}</span>}
              </span>
            </label>
          );
        })}
      </div>

      {/* Counter — warns when below minimum */}
      <div className={styles.counter}>
        {selectedKeys.length === 0 ? (
          <span className={styles.counterWarn}>Select at least {MIN_SELECT} parameters</span>
        ) : !meetsMinimum ? (
          <span className={styles.counterWarn}>
            {selectedKeys.length} selected — need {remaining} more
          </span>
        ) : allSelected ? (
          <span className={styles.counterAll}>All {selectedKeys.length} parameters selected</span>
        ) : (
          <span className={styles.counterOk}>{selectedKeys.length} of {allKeys.length} selected</span>
        )}
      </div>

      <div className={styles.actions}>
        <button
          className={styles.btnPrimary}
          onClick={onSearch}
          disabled={loading || !meetsMinimum}
          type="button"
        >
          {loading ? 'Searching…' : 'Find best Nuvoton match'}
        </button>
        <button className={styles.btnSecondary} onClick={onReset} type="button">
          Reset
        </button>
      </div>
    </section>
  );
}
