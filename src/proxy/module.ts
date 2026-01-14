import { startProxy } from './impl';
import { readFileSync, existsSync } from 'node:fs';

// Environment Variables with Defaults
const PORT = parseInt(process.env.PORT || "3001");
const MERCHANT_URL = process.env.MERCHANT_BACKEND_URL || "http://localhost:3000";
const REGISTRY_URL = process.env.AGENT_REGISTRY_URL || "http://localhost:9002";
const DEBUG = process.env.DEBUG === "true";

// TLS Configuration
const CERT_FILE = process.env.CERT_FILE || "cert.pem";
const KEY_FILE = process.env.KEY_FILE || "private.pem";
const CA_FILE = process.env.CA_FILE || "ca.pem";

let tlsConfig = undefined;
if (existsSync(CERT_FILE) && existsSync(KEY_FILE)) {
    tlsConfig = {
        cert: readFileSync(CERT_FILE, 'utf-8'),
        key: readFileSync(KEY_FILE, 'utf-8'),
        ca: existsSync(CA_FILE) ? readFileSync(CA_FILE, 'utf-8') : undefined
    };
    console.log(`TLS Configuration loaded from ${CERT_FILE} and ${KEY_FILE}`);
} else {
    console.warn("No TLS certificates found. Proxy will start without HTTPS/mTLS support unless configured via ProxyConfig.");
}

console.log(`Starting CDN Proxy on port ${PORT}...`);
console.log(`Merchant URL: ${MERCHANT_URL}`);
console.log(`Registry URL: ${REGISTRY_URL}`);

startProxy({
    port: PORT,
    merchantUrl: MERCHANT_URL,
    registryUrl: REGISTRY_URL,
    debug: DEBUG,
    tls: tlsConfig
}).then((service) => {
    service.start();
    const protocol = tlsConfig ? "https" : "http";
    console.log(`CDN Proxy listening on ${protocol}://localhost:${PORT}`);
}).catch(err => {
    console.error("Failed to start proxy:", err);
    process.exit(1);
});
