import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Routes, Route } from "react-router-dom";
import Home from "@/pages/Home";

type AuthState = "checking" | "signed-out" | "signed-in";

function AuthGate({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>("checking");
  const [username, setUsername] = useState("auditpro-admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function checkSession() {
    try {
      const response = await fetch("/api/auth/me", { credentials: "same-origin" });
      setState(response.ok ? "signed-in" : "signed-out");
    } catch {
      setError("Server tidak dapat dijangkau. Periksa koneksi lalu coba lagi.");
      setState("signed-out");
    }
  }

  useEffect(() => { void checkSession(); }, []);

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) {
        setError(result.detail ?? "Login gagal. Periksa konfigurasi server dan kredensial.");
        return;
      }
      setPassword("");
      setState("signed-in");
    } catch {
      setError("Server tidak dapat dijangkau. Coba lagi.");
    } finally {
      setBusy(false);
    }
  }

  if (state === "checking") {
    return <main className="grid min-h-screen place-items-center bg-background text-foreground">Memeriksa sesi AuditPro…</main>;
  }

  if (state === "signed-out") {
    return (
      <main className="grid min-h-screen place-items-center bg-background px-4 py-10 text-foreground">
        <form onSubmit={login} className="w-full max-w-sm space-y-5 rounded-2xl border bg-card p-6 shadow-sm">
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">AuditPro</p>
            <h1 className="text-2xl font-semibold tracking-tight">Masuk ke workspace</h1>
            <p className="text-sm text-muted-foreground">Gunakan kredensial administrator yang dikonfigurasi di server.</p>
          </div>
          <label className="block space-y-1.5 text-sm font-medium">
            Username
            <input autoComplete="username" required value={username} onChange={(e) => setUsername(e.target.value)} className="w-full rounded-lg border bg-background px-3 py-2.5" />
          </label>
          <label className="block space-y-1.5 text-sm font-medium">
            Password
            <input autoComplete="current-password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className="w-full rounded-lg border bg-background px-3 py-2.5" />
          </label>
          {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
          <button disabled={busy} type="submit" className="w-full rounded-lg bg-primary px-4 py-2.5 font-medium text-primary-foreground disabled:opacity-60">
            {busy ? "Memverifikasi…" : "Masuk"}
          </button>
          <p className="text-xs text-muted-foreground">Sesi menggunakan cookie HttpOnly dan berakhir setelah 8 jam.</p>
        </form>
      </main>
    );
  }

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST", credentials: "same-origin" }).catch(() => undefined);
    setPassword("");
    setState("signed-out");
  }

  return (
    <>
      <div className="fixed right-3 top-3 z-50">
        <button type="button" onClick={() => void logout()} className="rounded-lg border bg-background/95 px-3 py-2 text-xs font-medium text-foreground shadow-sm">
          Keluar
        </button>
      </div>
      {children}
    </>
  );
}

// One <Route> per page in src/pages; BrowserRouter already wraps this in main.tsx.
export default function App() {
  return (
    <AuthGate>
      <Routes>
        <Route path="/" element={<Home />} />
      </Routes>
    </AuthGate>
  );
}
