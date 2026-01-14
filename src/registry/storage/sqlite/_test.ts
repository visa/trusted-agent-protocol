import { describe, expect, test, beforeEach, afterEach } from "bun:test";
import { SqliteRegistryService } from "./src";
import type { RegisterAgentRequest } from "./interface";
import { unlinkSync } from "node:fs";

const TEST_DB = "test_registry.db";

describe("SqliteRegistryService", () => {
    let service: SqliteRegistryService;

    beforeEach(() => {
        service = new SqliteRegistryService(TEST_DB);
    });

    afterEach(() => {
        try {
            unlinkSync(TEST_DB);
        } catch (e) { }
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

        const found = await service.getAgent(agent.id);
        expect(found).not.toBeNull();
        expect(found?.domain).toBe("https://agent.com");

        const key = await service.getKey("key-1");
        expect(key).not.toBeNull();
        expect(key?.agent_id).toBe(agent.id);
    });
});
