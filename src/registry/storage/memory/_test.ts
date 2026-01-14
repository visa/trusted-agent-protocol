import { describe, expect, test, beforeEach } from "bun:test";
import { MemoryRegistryService } from "./src";
import type { RegisterAgentRequest } from "./interface";

describe("MemoryRegistryService", () => {
    let service: MemoryRegistryService;

    beforeEach(() => {
        service = new MemoryRegistryService();
    });

    test("createAgent should register agent and key", async () => {
        const req: RegisterAgentRequest = {
            name: "Test Agent",
            domain: "https://agent.com",
            jwk: { kty: "RSA", kid: "key-1", n: "abc", e: "AQAB" }
        };

        const agent = await service.createAgent(req);

        expect(agent.id).toBeDefined();
        expect(agent.name).toBe("Test Agent");

        // Check lookup
        const found = await service.getAgent(agent.id);
        expect(found).not.toBeNull();
        expect(found?.domain).toBe("https://agent.com");

        // Check key
        const key = await service.getKey("key-1");
        expect(key).not.toBeNull();
        expect(key?.agent_id).toBe(agent.id);
    });

    test("createAgent duplicate domain should fail", async () => {
        const req = {
            name: "Test",
            domain: "https://unique.com",
            jwk: { kty: "RSA", kid: "k1" }
        };
        await service.createAgent(req);

        expect(service.createAgent(req)).rejects.toThrow("Domain https://unique.com already registered");
    });
});
