import { convertQueryResultToTimeseries } from "@dynatrace/strato-components/charts";

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
 * Convert DQL summarize records to DonutChart's { slices } format.
 */
export function toDonutData(records: any[]) {
  if (!records || records.length === 0) return { slices: [] };
  const first = records[0];
  const keys = Object.keys(first);
  let catKey = keys[0];
  let valKey = keys[1];
  for (const k of keys) {
    if (typeof first[k] === "string" && k !== "timestamp") catKey = k;
    if (typeof first[k] === "number") valKey = k;
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
 */
export function toBarData(records: any[]) {
  if (!records || records.length === 0) return [];
  const first = records[0];
  const keys = Object.keys(first);
  let catKey = keys[0];
  const valKeys: string[] = [];
  for (const k of keys) {
    if (typeof first[k] === "string" && k !== "timestamp") catKey = k;
    if (typeof first[k] === "number") valKeys.push(k);
  }
  if (valKeys.length === 0) return [];
  if (valKeys.length === 1) {
    return records.map((r: any) => ({
      category: String(r[catKey] ?? "unknown"),
      value: Number(r[valKeys[0]]) || 0,
    }));
  }
  return records.map((r: any) => {
    const value: Record<string, number> = {};
    for (const vk of valKeys) value[vk] = Number(r[vk]) || 0;
    return { category: String(r[catKey] ?? "unknown"), value };
  });
}
