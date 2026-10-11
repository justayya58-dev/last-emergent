import { describe, expect, it } from "vitest";
import { createTransactionSchema } from "./schema";

const valid = {
  spaceId: "c6c2a6a1-9a45-4f67-95e0-9a4d2a2cbe11",
  accountId: "c6c2a6a1-9a45-4f67-95e0-9a4d2a2cbe12",
  kind: "expense",
  amount: "12500.50",
  currency: "IDR",
  occurredOn: "2026-10-11",
};

describe("createTransactionSchema", () => {
  it("accepts a positive decimal amount with at most two fractional digits", () => {
    expect(createTransactionSchema.safeParse(valid).success).toBe(true);
  });

  it("rejects zero, negative, scientific notation, and more than two decimal places", () => {
    for (const amount of ["0", "-1", "1e3", "12.345", "Infinity"]) {
      expect(createTransactionSchema.safeParse({ ...valid, amount }).success).toBe(false);
    }
  });

  it("rejects invalid dates and currencies", () => {
    expect(createTransactionSchema.safeParse({ ...valid, occurredOn: "2026-02-30" }).success).toBe(false);
    expect(createTransactionSchema.safeParse({ ...valid, currency: "idr" }).success).toBe(false);
  });

  it("rejects non-UUID references", () => {
    expect(createTransactionSchema.safeParse({ ...valid, spaceId: "personal" }).success).toBe(false);
  });
});
