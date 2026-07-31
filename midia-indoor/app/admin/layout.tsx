import { requireAdmin } from "@/lib/security";
export default async function AdminLayout({ children }: { children: React.ReactNode }) { await requireAdmin(); return children; }
