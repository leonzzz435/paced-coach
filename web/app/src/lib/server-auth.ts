export type ServerAuthMode = "local";

export function resolveServerAuthMode(env: NodeJS.ProcessEnv = process.env): ServerAuthMode {
  const rawMode = env.AUTH_MODE ?? env.NEXT_PUBLIC_AUTH_MODE ?? "local";
  const normalized = rawMode.trim().toLowerCase();
  if (normalized !== "local") {
    throw new Error("Invalid AUTH_MODE. Expected 'local'.");
  }
  return "local";
}

export async function backendAuthHeaders(): Promise<Record<string, string>> {
  resolveServerAuthMode();
  return {};
}
