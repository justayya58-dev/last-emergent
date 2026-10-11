import { describe, expect, it } from "vitest";
import { createFinanceSpaceSchema } from "./schema";

describe("createFinanceSpaceSchema", () => {
  it("accepts only the personal and office space kinds", () => {
    expect(createFinanceSpaceSchema.safeParse({ kind: "personal", name: "Pribadi" }).success).toBe(true);
    expect(createFinanceSpaceSchema.safeParse({ kind: "office", name: "Kantor" }).success).toBe(true);
    expect(createFinanceSpaceSchema.safeParse({ kind: "company", name: "Company" }).success).toBe(false);
  });

  it("trims names and rejects empty or too-long names", () => {
    expect(createFinanceSpaceSchema.parse({ kind: "personal", name: "  Pribadi  " }).name).toBe("Pribadi");
    expect(createFinanceSpaceSchema.safeParse({ kind: "office", name: "   " }).success).toBe(false);
    expect(createFinanceSpaceSchema.safeParse({ kind: "office", name: "x".repeat(81) }).success).toBe(false);
  });
});
