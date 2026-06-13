import { backendAuthHeaders } from "@/lib/server-auth";

export async function GET() {
  let authHeaders: Record<string, string>;
  try {
    authHeaders = await backendAuthHeaders();
  } catch {
    return new Response(JSON.stringify({ detail: "Not authenticated" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  const apiBase = (process.env.API_BASE_URL ?? "http://localhost:8000").replace(/\/+$/, "");
  return fetch(`${apiBase}/api/oauth/whoop/start`, {
    method: "GET",
    headers: authHeaders,
    redirect: "manual",
    cache: "no-store",
  });
}
