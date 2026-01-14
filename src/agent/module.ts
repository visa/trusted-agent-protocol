import { Agent } from './impl';

// Environment
const REGISTRY_URL = process.env.AGENT_REGISTRY_URL || "http://localhost:9002";
const PROXY_URL = process.env.CDN_PROXY_URL || "http://localhost:3001";
const DEBUG = process.env.DEBUG === "true";

async function main() {
    console.log("=== TAP Agent Demo ===");
    console.log(`Registry: ${REGISTRY_URL}`);
    console.log(`Proxy: ${PROXY_URL}`);

    const agent = new Agent({
        name: "Demo Agent " + Math.floor(Math.random() * 1000),
        registryUrl: REGISTRY_URL,
        proxyUrl: PROXY_URL,
        debug: DEBUG
    });

    try {
        // 1. Setup
        console.log("\n1. Generating Identity...");
        agent.generateKey();

        // 2. Register
        console.log("\n2. Registering with Identity Provider...");
        await agent.register();

        // 2.5 Request Certificate
        console.log("\n2.5 Requesting Certificate from Authority...");
        await agent.requestCertificate();

        // 3. Authenticated Request
        console.log("\n3. Accessing Secured Resource via Proxy...");
        const path = "/product/1";
        const res = await agent.fetch(path);

        console.log(`Response Status: ${res.status} ${res.statusText}`);

        if (res.ok) {
            const data = await res.json();
            console.log("\nSUCCESS! Secured Data Received:");
            console.log(JSON.stringify(data, null, 2));
        } else {
            console.error("\nFAILED! Response Body:");
            console.error(await res.text());
        }

    } catch (e: any) {
        console.error("\nERROR:", e.message);
        process.exit(1);
    }
}

main();
