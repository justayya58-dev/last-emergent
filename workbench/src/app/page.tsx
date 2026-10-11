import Link from "next/link";
import { listFinanceSpaces } from "@/modules/finance-spaces/list-spaces";

export default async function HomePage() {
  const spaces = await listFinanceSpaces();

  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: "40px 20px" }}>
      <p style={{ color: "var(--accent)", fontWeight: 700, letterSpacing: ".08em", textTransform: "uppercase" }}>
        Personal Finance Workbench
      </p>
      <h1 style={{ fontSize: "clamp(2rem, 5vw, 3rem)", marginBottom: 8 }}>Pusat kendali keuangan</h1>
      <p style={{ color: "var(--muted)", maxWidth: 620, lineHeight: 1.7 }}>
        Kelola keuangan pribadi dan kantor di ruang terpisah. Pemisahan diterapkan pada database, bukan hanya tampilan.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 16, marginTop: 28 }}>
        {(["personal", "office"] as const).map((kind) => {
          const space = spaces.find((item) => item.kind === kind);
          return (
            <section key={kind} style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 16, padding: 24 }}>
              <h2 style={{ fontSize: 22, marginTop: 0 }}>{kind === "personal" ? "Keuangan pribadi" : "Keuangan kantor"}</h2>
              <p style={{ color: "var(--muted)", minHeight: 48 }}>
                {space ? space.name : "Ruang belum dibuat. Siapkan data awal melalui migrasi dan proses onboarding."}
              </p>
              <p style={{ fontSize: 13, color: "var(--muted)" }}>Mata uang: {space?.currency ?? "IDR"}</p>
            </section>
          );
        })}
      </div>
      <p style={{ marginTop: 28, color: "var(--muted)", fontSize: 14 }}>
        <Link href="/login">Keluar / masuk dengan akun Supabase</Link>
      </p>
    </main>
  );
}
