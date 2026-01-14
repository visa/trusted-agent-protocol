import { describe, test, expect, mock } from "bun:test";
import { Agent } from "./impl";

const CONFIG = {
    name: "Test Agent",
    registryUrl: "http://mock-registry",
    proxyUrl: "http://mock-proxy",
    debug: false
};

describe("TAP Agent", () => {
    test("generateKey() should create valid JWKs", () => {
        const agent = new Agent(CONFIG);
        agent.generateKey("test-key");

        const keys = (agent as any).keyPair;
        expect(keys).toBeDefined();
        expect(keys.publicJwk.kid).toBe("test-key");
    });

    test("fetch() with authMode: 'signature' (default)", async () => {
        const agent = new Agent(CONFIG);
        agent.generateKey();

        const originalFetch = global.fetch;
        let capturedOptions: any;
        global.fetch = mock(async (url, options) => {
            capturedOptions = options;
            return new Response("ok");
        });

        await agent.fetch("/test");

        expect(capturedOptions.headers).toHaveProperty("Signature");
        expect(capturedOptions.headers).toHaveProperty("Signature-Input");
        expect(capturedOptions.tls).toBeUndefined();

        global.fetch = originalFetch;
    });

    test("fetch() with authMode: 'mTLS'", async () => {
        const agent = new Agent({
            ...CONFIG,
            authMode: 'mTLS',
            tls: {
                cert: "CERT",
                key: "KEY",
                ca: "CA",
                rejectUnauthorized: false
            }
        });

        const originalFetch = global.fetch;
        let capturedOptions: any;
        global.fetch = mock(async (url, options) => {
            capturedOptions = options;
            return new Response("ok");
        });

        await agent.fetch("/test");

        // Should NOT have signature headers
        expect(capturedOptions.headers).not.toHaveProperty("signature");

        // Should have TLS configuration
        expect(capturedOptions.tls).toBeDefined();
        expect(capturedOptions.tls.cert).toBe("CERT");
        expect(capturedOptions.tls.key).toBe("KEY");
        expect(capturedOptions.tls.rejectUnauthorized).toBe(false);

        global.fetch = originalFetch;
    });
});
