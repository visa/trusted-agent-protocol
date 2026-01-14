import { describe, test, expect, beforeAll, afterAll } from "bun:test";
import { RegistryServer, MemoryRegistryService } from "./registry/module";
import { AuthorityServer } from "./authority/module";
import { ProxyServer } from "./proxy/impl";
import { MerchantServer } from "./merchant/impl";
import { Agent } from "./agent/impl";
import forge from 'node-forge';

let REGISTRY_URL: string;
let MERCHANT_URL: string;
let PROXY_URL: string;
let AUTHORITY_URL: string;

let authorityServer: AuthorityServer;
let registryServer: RegistryServer;
let merchantServer: MerchantServer;
let proxyServer: any; // Using any for proxyServer because it's a ProxyService from impl
let serverCert: string, serverKey: string;

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

    // 1. Authority
    authorityServer = new AuthorityServer(0);
    await authorityServer.start();
    AUTHORITY_URL = `http://localhost:${authorityServer.port}`;

    // 2. Registry
    registryServer = new RegistryServer(0, new MemoryRegistryService());
    await registryServer.start();
    REGISTRY_URL = `http://localhost:${registryServer.port}`;

    // 3. Merchant
    merchantServer = new MerchantServer({ port: 0 });
    merchantServer.start();
    MERCHANT_URL = `http://localhost:${merchantServer.port}`;

    // 4. Proxy
    proxyServer = new ProxyServer({
        port: 0,
        merchantUrl: MERCHANT_URL,
        registryUrl: REGISTRY_URL,
        authorityUrl: AUTHORITY_URL,
        tls: { cert: serverCert, key: serverKey },
        debug: true
    });
    await proxyServer.start();
    PROXY_URL = `https://localhost:${proxyServer.port}`;
});

afterAll(() => {
    authorityServer?.stop();
    registryServer?.stop();
    merchantServer?.stop();
    proxyServer?.stop();
});

describe("TAP End-to-End Auth Combinations", () => {
    test("1. mTLS + Authority-signed cert (Offline)", async () => {
        const agent = new Agent({
            name: "E2E_MTLS_AGENT",
            registryUrl: REGISTRY_URL,
            authorityUrl: AUTHORITY_URL,
            proxyUrl: PROXY_URL,
            authMode: 'mTLS'
        });
        agent.generateKey("mtls-key", 'rsa');
        await agent.register();
        await agent.requestCertificate();

        const agentTls = (agent as any).keyPair;
        const agentCert = (agent as any).certificate;

        const mtlsAgent = new Agent({
            name: "Authority mTLS Agent",
            registryUrl: REGISTRY_URL,
            authorityUrl: AUTHORITY_URL,
            proxyUrl: PROXY_URL,
            authMode: 'mTLS',
            tls: {
                key: agentTls.privateKey.export({ format: 'pem', type: 'pkcs8' }),
                cert: agentCert,
                rejectUnauthorized: false
            }
        });

        const res = await mtlsAgent.fetch("/product/1");
        expect(res.status).toBe(200);
        const data = await res.json() as any;
        expect(data.id.toString()).toBe("1");
    });

    test("2. mTLS + Registry-verified (Fallback)", async () => {
        const agent = new Agent({
            name: "Registry mTLS Agent",
            registryUrl: REGISTRY_URL,
            authorityUrl: AUTHORITY_URL,
            proxyUrl: PROXY_URL,
            authMode: 'mTLS'
        });
        agent.generateKey("reg-mtls-key");
        await agent.register();
        const agentId = (agent as any).agentId;

        const selfSignedTls = generateCert(agentId);

        const mtlsAgent = new Agent({
            name: "Registry mTLS Agent",
            registryUrl: REGISTRY_URL,
            authorityUrl: AUTHORITY_URL,
            proxyUrl: PROXY_URL,
            authMode: 'mTLS',
            tls: {
                ...selfSignedTls,
                rejectUnauthorized: false
            }
        });

        const res = await mtlsAgent.fetch("/product/1");
        expect(res.status).toBe(200);
    });

    test("3. HTTP Sig + Authority-signed cert (Offline)", async () => {
        const agent = new Agent({
            name: "Authority Sig Agent",
            registryUrl: REGISTRY_URL,
            authorityUrl: AUTHORITY_URL,
            proxyUrl: PROXY_URL,
            authMode: 'signature',
            tls: { rejectUnauthorized: false }
        });
        agent.generateKey("sig-key", 'rsa');
        await agent.register();
        await agent.requestCertificate();

        const res = await agent.fetch("/product/1");
        expect(res.status).toBe(200);
    });

    test("4. HTTP Sig + Registry-verified (Default)", async () => {
        const agent = new Agent({
            name: "Registry Sig Agent",
            registryUrl: REGISTRY_URL,
            authorityUrl: AUTHORITY_URL,
            proxyUrl: PROXY_URL,
            authMode: 'signature',
            tls: { rejectUnauthorized: false }
        });
        agent.generateKey("reg-sig-key");
        await agent.register();

        const res = await agent.fetch("/product/1");
        expect(res.status).toBe(200);
    });
});
