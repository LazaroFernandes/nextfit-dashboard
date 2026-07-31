import { requireAdmin } from "@/lib/security";
import AdminDashboard from "@/components/AdminDashboard";
export default async function AdminPage() { const session = await requireAdmin(); return <AdminDashboard session={session}/>; }
