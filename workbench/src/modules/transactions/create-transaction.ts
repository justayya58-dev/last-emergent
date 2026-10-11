import "server-only";

import { createTransactionSchema } from "./schema";
import { requireUser } from "@/modules/sessions/require-user";

/**
 * Validate and insert using the caller's Supabase session. PostgreSQL RLS is
 * the final ownership boundary; never use a service-role key for user requests.
 */
export async function createTransaction(rawInput: unknown) {
  const input = createTransactionSchema.parse(rawInput);
  const { supabase, user } = await requireUser();

  const { data, error } = await supabase
    .from("transactions")
    .insert({
      space_id: input.spaceId,
      account_id: input.accountId,
      category_id: input.categoryId ?? null,
      kind: input.kind,
      amount: input.amount,
      currency: input.currency,
      occurred_on: input.occurredOn,
      description: input.description,
      reference: input.reference ?? null,
      created_by: user.id,
    })
    .select("id, space_id, account_id, category_id, kind, amount, currency, occurred_on, description, reference, status, created_at")
    .single();

  if (error) {
    // Keep database internals out of user-facing errors; log structured detail
    // in the deployment's server logger when observability is added.
    throw new Error("Unable to create transaction. Check the selected account and finance space.");
  }

  return data;
}
