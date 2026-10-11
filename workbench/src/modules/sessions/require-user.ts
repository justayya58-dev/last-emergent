import "server-only";

import { redirect } from "next/navigation";
import { createSupabaseServerClient } from "@/lib/supabase/server";

/**
 * Authoritative session guard for server pages/actions.
 * Middleware may improve navigation UX, but callers must still use this guard.
 */
export async function requireUser() {
  const supabase = await createSupabaseServerClient();
  const { data, error } = await supabase.auth.getUser();

  if (error || !data.user) {
    redirect("/login");
  }

  return { supabase, user: data.user };
}
