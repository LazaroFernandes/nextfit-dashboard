import { getSession } from "@/lib/security";
import { redirect } from "next/navigation";
import LoginForm from "@/components/LoginForm";
/* eslint-disable @next/next/no-img-element */

export default async function LoginPage() {
  if (await getSession()) redirect("/admin");
  return <main className="relative grid min-h-screen place-items-center overflow-hidden bg-[#080a0d] px-5">
    <div className="absolute left-1/2 top-[-30%] h-[700px] w-[700px] -translate-x-1/2 rounded-full bg-blue-700/15 blur-[140px]"/>
    <section className="admin-card relative z-10 w-full max-w-md p-8 sm:p-10"><img src="/demo/logo-ct.svg" alt="CT Ítalo Vieira" className="mb-8 h-20 w-auto"/><p className="text-xs font-bold uppercase tracking-[.28em] text-blue-400">Mídia Indoor</p><h1 className="mt-3 text-3xl font-black tracking-tight">Painel de controle</h1><p className="mt-2 text-sm leading-relaxed text-zinc-400">Gerencie a programação, as boas-vindas e os aniversariantes exibidos nas televisões.</p><LoginForm/></section>
  </main>;
}
