const LOOPBACK_HOSTS = new Set(["localhost", "127.0.0.1", "[::1]"]);

function effectivePort(url: URL): string {
  if (url.port) return url.port;
  if (url.protocol === "http:") return "80";
  if (url.protocol === "https:") return "443";
  return "";
}

export function localOriginsMatch(rawOrigin: string, rawRequestOrigin: string): boolean {
  try {
    const origin = new URL(rawOrigin);
    const requestOrigin = new URL(rawRequestOrigin);
    if (origin.origin === requestOrigin.origin) return true;

    return (
      LOOPBACK_HOSTS.has(origin.hostname.toLowerCase()) &&
      LOOPBACK_HOSTS.has(requestOrigin.hostname.toLowerCase()) &&
      origin.protocol === requestOrigin.protocol &&
      effectivePort(origin) === effectivePort(requestOrigin)
    );
  } catch {
    return false;
  }
}
