import "server-only";

import { requireUser } from "@/modules/sessions/require-user";

export async function listFinanceSpaces() {
  const { supabase, user } = await requireUser();
  const { data, error } = await supabase
    .from("finance_spaces")
    .select("id, kind, name, currency, created_at")
    .eq("owner_id", user.id)
    .order("kind");

  if (error) {
    throw new Error("Unable to load finance spaces.");
  }

  return data;
}
