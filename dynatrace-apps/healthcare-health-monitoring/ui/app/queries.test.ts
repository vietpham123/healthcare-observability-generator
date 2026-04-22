import { describe, it, expect } from "vitest";
import { queries, ALL_SITES, SITE_ALIAS, epicSiteFilter, networkSiteFilter, netflowSiteFilter } from "./queries";

describe("queries module", () => {
  it("exports ALL_SITES with 6 sites", () => {
    expect(ALL_SITES).toHaveLength(6);
    const codes = ALL_SITES.map((s) => s.code);
    expect(codes).toContain("kcrmc-main");
    expect(codes).toContain("oak-clinic");
    expect(codes).toContain("hq-dc");
  });

  it("defines site aliases mapping old codes to new", () => {
    expect(SITE_ALIAS["tpk-clinic"]).toBe("oak-clinic");
    expect(SITE_ALIAS["wch-clinic"]).toBe("wel-clinic");
    expect(SITE_ALIAS["lwr-clinic"]).toBe("bel-clinic");
  });

  it("does not use scanLimitGBytes: -1 in any query", () => {
    const queryValues = Object.values(queries);
    for (const q of queryValues) {
      const str = typeof q === "function" ? q("test") : q;
      expect(str).not.toContain("scanLimitGBytes: -1");
    }
  });

  it("all fetch logs queries use scanLimitGBytes: 500", () => {
    const queryValues = Object.values(queries);
    for (const q of queryValues) {
      const str = typeof q === "function" ? q("test") : q;
      if (str.includes("fetch logs")) {
        expect(str).toContain("scanLimitGBytes: 500");
      }
    }
  });
});

describe("site filter functions", () => {
  it("epicSiteFilter returns clause for site without aliases", () => {
    const result = epicSiteFilter("kcrmc-main");
    expect(result).toBe('(healthcare.site == "kcrmc-main")');
  });

  it("epicSiteFilter includes aliases for oak-clinic", () => {
    const result = epicSiteFilter("oak-clinic");
    expect(result).toContain('healthcare.site == "oak-clinic"');
    expect(result).toContain('healthcare.site == "tpk-clinic"');
    expect(result).toContain(" OR ");
  });

  it("networkSiteFilter delegates to epicSiteFilter", () => {
    expect(networkSiteFilter("kcrmc-main")).toBe(epicSiteFilter("kcrmc-main"));
  });

  it("netflowSiteFilter uses network.device.site field", () => {
    const result = netflowSiteFilter("oak-clinic");
    expect(result).toContain('network.device.site == "oak-clinic"');
    expect(result).toContain('network.device.site == "tpk-clinic"');
  });
});
