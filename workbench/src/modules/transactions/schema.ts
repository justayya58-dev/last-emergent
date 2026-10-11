import { z } from "zod";

export const createTransactionSchema = z.object({
  spaceId: z.string().uuid(),
  accountId: z.string().uuid(),
  categoryId: z.string().uuid().nullable().optional(),
  kind: z.enum(["income", "expense", "transfer"]),
  // Accept a decimal string to avoid JS floating-point arithmetic in money input.
  amount: z.string().regex(/^(?:0|[1-9]\d{0,17})(?:\.\d{1,2})?$/).refine((v) => Number(v) > 0, "Amount must be greater than zero."),
  currency: z.string().regex(/^[A-Z]{3}$/).default("IDR"),
  occurredOn: z.string().date(),
  description: z.string().trim().max(500).default(""),
  reference: z.string().trim().max(120).nullable().optional(),
});

export type CreateTransactionInput = z.infer<typeof createTransactionSchema>;
