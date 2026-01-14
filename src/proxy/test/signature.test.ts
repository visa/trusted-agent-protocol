import { describe, test, expect, beforeAll, afterAll } from "bun:test";
import { startProxy } from "../impl";
import forge from 'node-forge';
import { Agent } from "../../agent/impl";

const AGENT_ID = "proxy-test-agent-sig";
const KEY_ID = "test-key-sig";

let serverCert: string;
let serverKey: string;

let merchantServer: any;
let registryServer: any;
let proxyServer: any;

let agentJwk: any = null;
let proxyUrl: string;
let registryUrl: string;

function generateCert(cn: string) {
    const keys = forge.pki.rsa.generateKeyPair(2048);
    const cert = forge.pki.createCertificate();
    cert.publicKey = keys.publicKey;
    cert.serialNumber = '01';
    cert.validity.notBefore = new Date();
    cert.validity.notAfter = new Date();
    cert.validity.notAfter.setFullYear(cert.validity.notBefore.getFullYear() + 1);
    cert.setSubject([{ name: 'commonName', value: cn }]);
    cert.setIssuer(cert.subject.attributes);
    cert.sign(keys.privateKey, forge.md.sha256.create());
    return {
        cert: forge.pki.certificateToPem(cert),
        key: forge.pki.privateKeyToPem(keys.privateKey)
    };
}

beforeAll(async () => {
    ({ cert: serverCert, key: serverKey } = generateCert('localhost'));

    merchantServer = Bun.serve({
        port: 0,
        fetch(req) {
            return new Response(JSON.stringify({ id: 1, name: "Test Product" }), {
                headers: { "Content-Type": "application/json" }
            });
        }
    });

    const merchantUrl = `http://127.0.0.1:${merchantServer.port}`;

    registryServer = Bun.serve({
        port: 0,
        fetch(req) {
            const url = new URL(req.url);
            if (url.pathname === `/keys/${KEY_ID}`) {
                if (!agentJwk) return new Response("Not Found", { status: 404 });
                return new Response(JSON.stringify(agentJwk), { headers: { "Content-Type": "application/json" } });
            }
            if (url.pathname === '/authority/cert') {
                return new Response(serverCert, { headers: { "Content-Type": "text/plain" } });
            }
            if (url.pathname === `/agents/${AGENT_ID}`) {
                return new Response(JSON.stringify({ id: AGENT_ID, status: 'active' }), { headers: { "Content-Type": "application/json" } });
            }
            return new Response("Not Found", { status: 404 });
        }
    });

    registryUrl = `http://127.0.0.1:${registryServer.port}`;

    proxyServer = await startProxy({
        port: 0,
        merchantUrl: merchantUrl,
        registryUrl: registryUrl,
        authorityUrl: registryUrl,
        debug: true,
        tls: { cert: serverCert, key: serverKey }
    });

    proxyUrl = `https://127.0.0.1:${proxyServer.port}`;
});

afterAll(() => {
    merchantServer?.stop();
    registryServer?.stop();
    proxyServer?.stop();
});

describe("Proxy Signature Authorization", () => {
    test("Valid Signature: Passes without mTLS", async () => {
        const agent = new Agent({
            name: "Proxy Sig Agent",
            registryUrl: registryUrl,
            proxyUrl: proxyUrl,
            authMode: 'signature',
            tls: { rejectUnauthorized: false }
        });

        agent.generateKey(KEY_ID);
        agentJwk = (agent as any).keyPair.publicJwk;
        (agent as any).agentId = AGENT_ID;

        const res = await agent.fetch("/product/1", {
            headers: { 'Connection': 'close' }
        });

        expect(res.status).toBe(200);
        const data = await res.json() as any;
        expect(data.name).toBe("Test Product");
    });
});
