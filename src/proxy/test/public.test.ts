import { describe, test, expect, beforeAll, afterAll } from "bun:test";
import { startProxy } from "../impl";
import forge from 'node-forge';

let serverCert: string;
let serverKey: string;

let merchantServer: any;
let registryServer: any;
let proxyServer: any;

let proxyUrl: string;

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
            return new Response("Home Page", { status: 200 });
        }
    });

    const merchantUrl = `http://127.0.0.1:${merchantServer.port}`;

    registryServer = Bun.serve({
        port: 0,
        fetch(req) {
            const url = new URL(req.url);
            if (url.pathname === '/authority/cert') {
                return new Response(serverCert, { headers: { "Content-Type": "text/plain" } });
            }
            return new Response("Not Found", { status: 404 });
        }
    });

    const registryUrl = `http://127.0.0.1:${registryServer.port}`;

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

describe("Proxy Public Routes", () => {
    test("Health Check: Accessible without auth", async () => {
        const res = await fetch(`${proxyUrl}/test-proxy`, {
            tls: { rejectUnauthorized: false }
        });
        expect(res.status).toBe(200);
        expect(await res.text()).toBe("Proxy Active");
    });
});
