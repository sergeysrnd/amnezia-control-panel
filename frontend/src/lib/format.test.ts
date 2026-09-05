import { describe, expect, it } from "vitest";

import { formatBytes, formatDate, truncateEndpoint } from "./format";

describe("formatBytes", () => {
  it("uses binary units without noisy decimals", () => {
    expect(formatBytes(0)).toBe("0 B");
    expect(formatBytes(512 * 1024)).toBe("512 KB");
    expect(formatBytes(1.5 * 1024 ** 3)).toBe("1.50 GB");
  });
});

describe("formatDate", () => {
  it("keeps non-ISO creation dates readable", () => {
    expect(formatDate("дата из старого clientsTable")).toBe("дата из старого clientsTable");
  });
});

describe("truncateEndpoint", () => {
  it("preserves short endpoints and truncates long ones", () => {
    expect(truncateEndpoint("203.0.113.1:51820")).toBe("203.0.113.1:51820");
    expect(truncateEndpoint("[2001:db8:abcd:1234::10]:51820")).toContain("…");
  });
});
