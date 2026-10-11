"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { createSupabaseBrowserClient } from "@/lib/supabase/browser";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const supabase = createSupabaseBrowserClient();
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) throw error;
      router.replace("/");
      router.refresh();
    } catch {
      setMessage("Tidak dapat masuk. Periksa email, kata sandi, dan konfigurasi Supabase.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={{ maxWidth: 420, margin: "10vh auto", padding: 24, background: "white", border: "1px solid var(--border)", borderRadius: 16 }}>
      <h1>Masuk ke Workbench</h1>
      <p style={{ color: "var(--muted)", lineHeight: 1.6 }}>Gunakan akun yang sudah dibuat di Supabase Authentication. Pendaftaran publik tidak diaktifkan di aplikasi ini.</p>
      <form onSubmit={onSubmit} style={{ display: "grid", gap: 14 }}>
        <label>Email<input required type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} style={{ display: "block", width: "100%", padding: 12, marginTop: 6, border: "1px solid var(--border)", borderRadius: 8 }} /></label>
        <label>Kata sandi<input required type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} style={{ display: "block", width: "100%", padding: 12, marginTop: 6, border: "1px solid var(--border)", borderRadius: 8 }} /></label>
        <button disabled={busy} type="submit" style={{ padding: 12, background: "var(--accent)", color: "white", border: 0, borderRadius: 8, cursor: busy ? "wait" : "pointer" }}>{busy ? "Memproses…" : "Masuk"}</button>
      </form>
      {message && <p role="alert" style={{ color: "#b91c1c" }}>{message}</p>}
    </main>
  );
}
