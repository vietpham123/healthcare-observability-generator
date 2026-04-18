import { epicSiteFilter, networkSiteFilter, netflowSiteFilter, SITE_ALIAS } from "../queries";

// Inject a site filter clause into a DQL query string.
// For `fetch logs` queries: appends `| filter <clause>` after the first `| filter` line.
// For `timeseries` queries: injects a `filter: { site == "..." }` parameter.
export function withSiteFilter(query: string, siteCode: string | null, kind: "epic" | "network" | "netflow" = "epic"): string {
  if (!siteCode) return query;

  // Handle timeseries queries — metric dimension filtering
  const trimmed = query.trimStart();
  const isTimeseries = trimmed.startsWith("timeseries ") || trimmed.startsWith("timeseries\n");
  if (isTimeseries) {
    const aliases = Object.entries(SITE_ALIAS).filter(([, v]) => v === siteCode).map(([k]) => k);
    const codes = [siteCode, ...aliases];
    // For a single code use ==, for multiple use in()
    const siteFilter = codes.length === 1
      ? `site == "${codes[0]}"`
      : `in(site, ${codes.map((c) => `"${c}"`).join(", ")})`;
    // Insert filter: {...} before the first comma that's followed by a keyword param like by:, from:, interval:
    const kwMatch = trimmed.match(/,\s*(by:|from:|interval:|bins:)/);
    if (kwMatch && kwMatch.index != null) {
      const pos = kwMatch.index;
      return trimmed.slice(0, pos) + `, filter: {${siteFilter}}` + trimmed.slice(pos);
    }
    // No keyword params — append at end
    return trimmed + `, filter: {${siteFilter}}`;
  }

  let clause: string;
  if (kind === "netflow") clause = netflowSiteFilter(siteCode);
  else if (kind === "network") clause = networkSiteFilter(siteCode);
  else clause = epicSiteFilter(siteCode);
  // Insert site filter after the first `| filter` line
  const idx = query.indexOf("| filter");
  if (idx === -1) return query;
  const lineEnd = query.indexOf("\n", idx);
  if (lineEnd === -1) return query + `\n    | filter ${clause}`;
  return query.slice(0, lineEnd) + `\n    | filter ${clause}` + query.slice(lineEnd);
}
