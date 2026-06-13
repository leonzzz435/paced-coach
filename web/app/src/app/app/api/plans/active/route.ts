import { apiFetch } from "@/lib/api";

export async function GET() {
  const data = await apiFetch("/api/plans/active", { method: "GET" });
  return Response.json(data);
}

