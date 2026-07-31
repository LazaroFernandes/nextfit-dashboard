"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginForm() {
  const router = useRouter(); const [error, setError] = useState(""); const [loading, setLoading] = useState(false);
  return <form className="mt-8 space-y-4" onSubmit={async (event) => { event.preventDefault(); setLoading(true); setError(""); const form = new FormData(event.currentTarget); const response = await fetch("/api/auth/login", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(Object.fromEntries(form)) }); setLoading(false); if (!response.ok) { setError("E-mail ou senha inválidos."); return; } router.push("/admin"); router.refresh(); }}>
    <label className="block text-sm font-semibold text-zinc-300">E-mail<input className="admin-input mt-2" type="email" name="email" required autoComplete="email"/></label>
    <label className="block text-sm font-semibold text-zinc-300">Senha<input className="admin-input mt-2" type="password" name="password" required autoComplete="current-password"/></label>
    {error && <p className="rounded-xl border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-300">{error}</p>}
    <button className="admin-button mt-2 w-full" disabled={loading}>{loading ? "Entrando…" : "Entrar no painel"}</button>
  </form>;
}
