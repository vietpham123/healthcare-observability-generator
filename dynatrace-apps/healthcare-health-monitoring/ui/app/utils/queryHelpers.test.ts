import { describe, it, expect } from "vitest";
import { withSiteFilter } from "./queryHelpers";

describe("withSiteFilter", () => {
  it("returns query unchanged when siteCode is null", () => {
    const query = `fetch logs, scanLimitGBytes: 500, samplingRatio: 1
    | filter something == true
    | summarize count()`;
    expect(withSiteFilter(query, null)).toBe(query);
  });

  it("injects epic site filter after first filter line", () => {
    const query = `fetch logs, scanLimitGBytes: 500, samplingRatio: 1
    | filter something == true
    | summarize count()`;
    const result = withSiteFilter(query, "kcrmc-main", "epic");
    expect(result).toContain('healthcare.site == "kcrmc-main"');
    // Should appear between the existing filter and summarize
    const filterIdx = result.indexOf("something == true");
    const siteIdx = result.indexOf("healthcare.site");
    const sumIdx = result.indexOf("summarize");
    expect(siteIdx).toBeGreaterThan(filterIdx);
    expect(siteIdx).toBeLessThan(sumIdx);
  });

  it("includes alias codes for sites with aliases", () => {
    const query = `fetch logs, scanLimitGBytes: 500, samplingRatio: 1
    | filter something == true
    | summarize count()`;
    const result = withSiteFilter(query, "oak-clinic", "epic");
    expect(result).toContain('healthcare.site == "oak-clinic"');
    expect(result).toContain('healthcare.site == "tpk-clinic"');
  });

  it("handles netflow kind with correct field name", () => {
    const query = `fetch logs, scanLimitGBytes: 500, samplingRatio: 1
    | filter log.source == "netflow"
    | summarize count()`;
    const result = withSiteFilter(query, "oak-clinic", "netflow");
    expect(result).toContain('network.device.site == "oak-clinic"');
    expect(result).toContain('network.device.site == "tpk-clinic"');
  });

  it("injects filter param into timeseries queries", () => {
    const query = `timeseries cpu = avg(healthcare.network.device.cpu.utilization), by: {device}, from: now()-2h`;
    const result = withSiteFilter(query, "kcrmc-main", "epic");
    expect(result).toContain('filter: {site == "kcrmc-main"}');
  });

  it("handles timeseries with multiple alias codes using in()", () => {
    const query = `timeseries cpu = avg(healthcare.network.device.cpu.utilization), by: {device}, from: now()-2h`;
    const result = withSiteFilter(query, "oak-clinic", "epic");
    expect(result).toContain("in(site,");
    expect(result).toContain('"oak-clinic"');
    expect(result).toContain('"tpk-clinic"');
  });
});
