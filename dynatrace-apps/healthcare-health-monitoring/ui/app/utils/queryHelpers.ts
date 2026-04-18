import { epicSiteFilter, networkSiteFilter, netflowSiteFilter } from "../queries";

// Inject a site filter clause into a DQL query string.
// Appends `| filter <clause>` after the first `| filter` line that contains the pipeline marker.
export function withSiteFilter(query: string, siteCode: string | null, kind: "epic" | "network" | "netflow" = "epic"): string {
  if (!siteCode) return query;
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
