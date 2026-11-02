import type { ChipSpec, Characteristic, MatchResponse } from './types';

const BASE = '/api';

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? 'Request failed');
  }
  return res.json() as Promise<T>;
}

export function getCharacteristics(): Promise<Characteristic[]> {
  return fetchJSON(`${BASE}/characteristics`);
}

export function searchCompetitorParts(query: string): Promise<ChipSpec[]> {
  return fetchJSON(`${BASE}/chips/competitor/search?q=${encodeURIComponent(query)}`);
}

export function getCompetitorPart(partNumber: string): Promise<ChipSpec> {
  return fetchJSON(`${BASE}/chips/competitor/${encodeURIComponent(partNumber)}`);
}

export function findMatches(
  partNumber: string,
  characteristics: string[],
  topK = 5,
): Promise<MatchResponse> {
  return fetchJSON(`${BASE}/match`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ part_number: partNumber, characteristics, top_k: topK }),
  });
}

export interface ImportResult {
  added: number;
  updated: number;
  total_in_catalog: number;
  imported: ChipSpec[];
  errors: string[];
}

export async function importCSV(file: File): Promise<ImportResult> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${BASE}/chips/competitor/import-csv`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? 'Import failed');
  }
  return res.json();
}

export interface ConvertPreview {
  mapping: Record<string, string>;
  unmatched_columns: string[];
  preview: ChipSpec[];
  total_rows: number;
  convertible: number;
  errors: string[];
  converted: ChipSpec[];
}

export async function convertCsvPreview(file: File): Promise<ConvertPreview> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${BASE}/chips/competitor/convert-preview`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? 'Preview failed');
  }
  return res.json();
}

export async function bulkImport(parts: ChipSpec[]): Promise<ImportResult> {
  const res = await fetch(`${BASE}/chips/competitor/bulk`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(parts),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? 'Bulk import failed');
  }
  return res.json();
}

export function addCompetitorPart(part: ChipSpec): Promise<ChipSpec> {
  return fetchJSON(`${BASE}/chips/competitor`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(part),
  });
}

export function downloadTemplate(): void {
  window.open(`${BASE}/chips/competitor/template`, '_blank');
}
