import { describe, test, expect, beforeAll, afterAll } from "bun:test";
import { startProxy } from "../impl";
import forge from 'node-forge';
import { Agent } from "../../agent/impl";

const AGENT_ID = "mtls-isolated-agent";

let serverCert: string;
let serverKey: string;
let clientCert: string;
let clientKey: string;

let merchantServer: any;
let registryServer: any;
let proxyServer: any;

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
    ({ cert: clientCert, key: clientKey } = generateCert(AGENT_ID));

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
            if (url.pathname === `/agents/${AGENT_ID}`) {
                return new Response(JSON.stringify({ id: AGENT_ID, status: 'active' }), { headers: { "Content-Type": "application/json" } });
            }
            if (url.pathname === '/authority/cert') {
                return new Response(serverCert, { headers: { "Content-Type": "text/plain" } });
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

describe("Proxy mTLS Authorization", () => {
    test("Authorized via mTLS: Bypasses Signature Check", async () => {
        const agent = new Agent({
            name: "Proxy mTLS Agent",
            registryUrl: registryUrl,
            proxyUrl: proxyUrl,
            authMode: 'mTLS',
            tls: {
                cert: clientCert,
                key: clientKey,
                rejectUnauthorized: false
            }
        });

        const res = await agent.fetch("/product/1", {
            headers: { 'Connection': 'close' }
        });
        expect(res.status).toBe(200);
        const data = await res.json() as any;
        expect(data.name).toBe("Test Product");
    });
});
