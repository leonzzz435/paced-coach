import assert from "node:assert/strict";

import { localOriginsMatch } from "../../lib/local-origin";

assert.equal(localOriginsMatch("http://localhost:3000", "http://localhost:3000"), true);
assert.equal(localOriginsMatch("http://127.0.0.1:3000", "http://localhost:3000"), true);
assert.equal(localOriginsMatch("http://[::1]:3000", "http://127.0.0.1:3000"), true);
assert.equal(localOriginsMatch("http://127.0.0.1:3001", "http://localhost:3000"), false);
assert.equal(localOriginsMatch("https://127.0.0.1:3000", "http://localhost:3000"), false);
assert.equal(localOriginsMatch("http://local.test:3000", "http://localhost:3000"), false);
assert.equal(localOriginsMatch("not-an-origin", "http://localhost:3000"), false);

console.log("Local write origin matching accepts loopback aliases without weakening port or protocol checks.");
