import assert from "node:assert/strict";

import { resolveApiTimeoutMs } from "@/lib/api";
import { resolveServerAuthMode } from "@/lib/server-auth";

const originalEnv = process.env.API_FETCH_TIMEOUT_MS;
const originalAuthMode = process.env.AUTH_MODE;
const originalPublicAuthMode = process.env.NEXT_PUBLIC_AUTH_MODE;

process.env.API_FETCH_TIMEOUT_MS = "45000";
assert.equal(resolveApiTimeoutMs(), 45_000);
assert.equal(resolveApiTimeoutMs(90_000), 90_000);
assert.equal(resolveApiTimeoutMs(null), null);

process.env.API_FETCH_TIMEOUT_MS = "not-a-number";
assert.equal(resolveApiTimeoutMs(), 30_000);

delete process.env.AUTH_MODE;
delete process.env.NEXT_PUBLIC_AUTH_MODE;
assert.equal(resolveServerAuthMode(), "local");

process.env.AUTH_MODE = "local";
assert.equal(resolveServerAuthMode(), "local");

process.env.AUTH_MODE = "hosted";
assert.throws(() => resolveServerAuthMode(), /Invalid AUTH_MODE/);

process.env.AUTH_MODE = "unknown";
process.env.NEXT_PUBLIC_AUTH_MODE = "local";
assert.throws(() => resolveServerAuthMode(), /Invalid AUTH_MODE/);

if (originalEnv === undefined) {
    delete process.env.API_FETCH_TIMEOUT_MS;
} else {
    process.env.API_FETCH_TIMEOUT_MS = originalEnv;
}
if (originalAuthMode === undefined) {
    delete process.env.AUTH_MODE;
} else {
    process.env.AUTH_MODE = originalAuthMode;
}
if (originalPublicAuthMode === undefined) {
    delete process.env.NEXT_PUBLIC_AUTH_MODE;
} else {
    process.env.NEXT_PUBLIC_AUTH_MODE = originalPublicAuthMode;
}

console.log("API timeout resolution tests passed.");
