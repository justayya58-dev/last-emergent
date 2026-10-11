import { z } from "zod";

export const financeSpaceKindSchema = z.enum(["personal", "office"]);

export const createFinanceSpaceSchema = z.object({
  kind: financeSpaceKindSchema,
  name: z.string().trim().min(1).max(80),
  currency: z.string().regex(/^[A-Z]{3}$/).default("IDR"),
});

export type FinanceSpaceKind = z.infer<typeof financeSpaceKindSchema>;
export type CreateFinanceSpaceInput = z.infer<typeof createFinanceSpaceSchema>;
