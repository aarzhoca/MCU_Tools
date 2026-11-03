import { useState, useEffect, useCallback } from 'react';
import styles from './App.module.css';
import SearchPanel from './components/SearchPanel';
import ResultsPanel from './components/ResultsPanel';
import ImportModal from './components/ImportModal';
import STXlsxPreviewModal from './components/STXlsxPreviewModal';
import { getCharacteristics, findMatches } from './api';
import type { Characteristic, MatchResponse } from './types';

export default function App() {
  const [characteristics, setCharacteristics] = useState<Characteristic[]>([]);
  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);
  const [partNumber, setPartNumber] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<MatchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showImport, setShowImport] = useState(false);
  const [showSTPreview, setShowSTPreview] = useState(false);
  const [importedCount, setImportedCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let retries = 0;
    const MAX_RETRIES = 5;

    function load() {
      getCharacteristics()
        .then(chars => { if (!cancelled) { setCharacteristics(chars); setError(null); } })
        .catch(() => {
          if (cancelled) return;
          if (retries < MAX_RETRIES) {
            retries++;
            setTimeout(load, 2000 * retries);
          } else {
            setError('Cannot reach the backend server. Make sure it is running on port 8000, then refresh the page.');
          }
        });
    }

    load();
    return () => { cancelled = true; };
  }, []);

  const handleSearch = useCallback(async () => {
    if (!partNumber.trim()) { setError('Please enter a competitor part number.'); return; }
    if (selectedKeys.length < 5) { setError('Please select at least 5 parameters.'); return; }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await findMatches(partNumber.trim().toUpperCase(), selectedKeys);
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [partNumber, selectedKeys]);

  const handleReset = useCallback(() => {
    setPartNumber('');
    setSelectedKeys([]);
    setResult(null);
    setError(null);
  }, []);

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <div className={styles.headerRow}>
            <div>
              <div className={styles.logo}>
                <span className={styles.logoRed}>Nuvoton</span>
                <span className={styles.logoTitle}>MCU Cross Reference</span>
              </div>
              <p className={styles.headerSub}>
                Enter a competitor part number, select at least 5 parameters to compare, and find the best-matching Nuvoton MCU.
              </p>
            </div>
            <button className={styles.importBtn} onClick={() => setShowSTPreview(true)} type="button">
              ST Excel preview
            </button>
            <button className={styles.importBtn} onClick={() => setShowImport(true)} type="button">
              + Add competitor parts
              {importedCount > 0 && <span className={styles.importBadge}>{importedCount}</span>}
            </button>
          </div>
        </div>
      </header>

      <main className={styles.main}>
        <div className={styles.grid}>
          <SearchPanel
            characteristics={characteristics}
            selectedKeys={selectedKeys}
            onSelectedKeysChange={setSelectedKeys}
            partNumber={partNumber}
            onPartNumberChange={setPartNumber}
            onSearch={handleSearch}
            onReset={handleReset}
            loading={loading}
          />
          <ResultsPanel
            result={result}
            loading={loading}
            error={error}
            selectedKeys={selectedKeys}
          />
        </div>
      </main>

      <footer className={styles.footer}>
        Nuvoton Technology Corporation — Internal Sales Tool
      </footer>

      {showSTPreview && <STXlsxPreviewModal onClose={() => setShowSTPreview(false)} />}
      {showImport && (
        <ImportModal
          onClose={() => setShowImport(false)}
          onImported={count => {
            setImportedCount((prev: number) => prev + count);
          }}
        />
      )}
    </div>
  );
}
