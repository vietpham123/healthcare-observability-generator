import { describe, it, expect } from "vitest";
import { toDonutData, toBarData } from "./chartHelpers";

describe("toDonutData", () => {
  it("returns empty slices for null/empty input", () => {
    expect(toDonutData([])).toEqual({ slices: [] });
    expect(toDonutData(null as any)).toEqual({ slices: [] });
    expect(toDonutData(undefined as any)).toEqual({ slices: [] });
  });

  it("converts category/count records to donut slices", () => {
    const records = [
      { event_type: "HL7", cnt: 100 },
      { event_type: "FHIR", cnt: 50 },
      { event_type: "ETL", cnt: 25 },
    ];
    const result = toDonutData(records);
    expect(result.slices).toHaveLength(3);
    expect(result.slices[0]).toEqual({ category: "HL7", value: 100 });
    expect(result.slices[1]).toEqual({ category: "FHIR", value: 50 });
    expect(result.slices[2]).toEqual({ category: "ETL", value: 25 });
  });

  it("handles DQL string-encoded numbers", () => {
    const records = [{ vendor: "Cisco", count: "42" }];
    const result = toDonutData(records);
    expect(result.slices[0].value).toBe(42);
  });

  it("uses 'unknown' for null category values", () => {
    const records = [{ category: null, count: 10 }];
    const result = toDonutData(records);
    expect(result.slices[0].category).toBe("unknown");
  });
});

describe("toBarData", () => {
  it("returns empty array for null/empty input", () => {
    expect(toBarData([])).toEqual([]);
    expect(toBarData(null as any)).toEqual([]);
    expect(toBarData(undefined as any)).toEqual([]);
  });

  it("converts single-value records to bar data", () => {
    const records = [
      { site: "kcrmc-main", events: 200 },
      { site: "oak-clinic", events: 80 },
    ];
    const result = toBarData(records);
    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({ category: "kcrmc-main", value: 200 });
    expect(result[1]).toEqual({ category: "oak-clinic", value: 80 });
  });

  it("converts multi-value records to grouped bar data", () => {
    const records = [
      { site: "kcrmc-main", logins: 100, failures: 5 },
      { site: "oak-clinic", logins: 40, failures: 2 },
    ];
    const result = toBarData(records);
    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({
      category: "kcrmc-main",
      value: { logins: 100, failures: 5 },
    });
  });

  it("handles string-encoded numbers from DQL", () => {
    const records = [{ department: "ED", count: "181" }];
    const result = toBarData(records);
    expect(result[0].value).toBe(181);
  });
});
