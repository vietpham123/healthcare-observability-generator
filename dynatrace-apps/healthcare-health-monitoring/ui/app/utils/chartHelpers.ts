import { convertQueryResultToTimeseries } from "@dynatrace/strato-components/charts";

/** Threshold reference line definition */
export interface ThresholdLine {
  label: string;
  value: number;
}

/**
 * Convert useDql result.data to Timeseries[] for TimeseriesChart.
 */
export function toTimeseries(data: any) {
  if (!data) return [];
  try {
    return convertQueryResultToTimeseries(data);
  } catch {
    return [];
  }
}

/**
 * Convert useDql result.data to Timeseries[] and append constant-value threshold reference lines.
 * Threshold series span the full time range of the data using dashed line naming convention.
 */
export function toTimeseriesWithThresholds(data: any, thresholds: ThresholdLine[]) {
  const series = toTimeseries(data);
  if (series.length === 0 || thresholds.length === 0) return series;
  // Extract time range from existing series
  let minDate = new Date();
  let maxDate = new Date(0);
  for (const s of series) {
    for (const dp of (s as any).datapoints ?? []) {
      const d = dp.start instanceof Date ? dp.start : new Date(dp.start);
      if (d < minDate) minDate = d;
      if (d > maxDate) maxDate = d;
    }
  }
  // Create 2-point constant series for each threshold
  for (const t of thresholds) {
    series.push({
      name: `⚠ ${t.label}`,
      datapoints: [
        { start: minDate, value: t.value },
        { start: maxDate, value: t.value },
      ],
    } as any);
  }
  return series;
}

/** Check if a value looks numeric (handles DQL returning numbers as strings). */
function isNumericLike(v: any): boolean {
  if (v == null || v === "" || typeof v === "boolean") return false;
  if (typeof v === "number") return true;
  if (typeof v === "bigint") return true;
  return !isNaN(Number(v));
}

/**
 * Convert DQL summarize records to DonutChart's { slices } format.
 * DQL often returns count() values as strings like "181".
 */
export function toDonutData(records: any[]) {
  if (!records || records.length === 0) return { slices: [] };
  const first = records[0];
  const keys = Object.keys(first);
  let catKey = keys[0];
  let valKey = keys.length > 1 ? keys[1] : keys[0];
  for (const k of keys) {
    const v = first[k];
    if (typeof v === "string" && !isNumericLike(v) && k !== "timestamp") catKey = k;
    if (isNumericLike(v) && k !== catKey) valKey = k;
  }
  return {
    slices: records.map((r: any) => ({
      category: String(r[catKey] ?? "unknown"),
      value: Number(r[valKey]) || 0,
    })),
  };
}

/**
 * Convert DQL summarize records to CategoricalBarChart's [{category, value}] format.
 * DQL often returns count() values as strings like "181".
 */
export function toBarData(records: any[]) {
  if (!records || records.length === 0) return [];
  const first = records[0];
  const keys = Object.keys(first);
  let catKey = keys[0];
  const valKeys: string[] = [];
  // First pass: find the category key (non-numeric string, not timestamp)
  for (const k of keys) {
    const v = first[k];
    if (typeof v === "string" && !isNumericLike(v) && k !== "timestamp") catKey = k;
  }
  // Second pass: find all value keys (numeric-like, not the category key)
  for (const k of keys) {
    if (k === catKey) continue;
    if (isNumericLike(first[k])) valKeys.push(k);
  }
  if (valKeys.length === 0) return [];
  if (valKeys.length === 1) {
    return records.map((r: any) => ({
      category: String(r[catKey] ?? "unknown"),
      value: Number(r[valKeys[0]]) || 0,
    }));
  }
  // Multiple value columns → grouped bar
  return records.map((r: any) => {
    const value: Record<string, number> = {};
    for (const vk of valKeys) value[vk] = Number(r[vk]) || 0;
    return { category: String(r[catKey] ?? "unknown"), value };
  });
}
