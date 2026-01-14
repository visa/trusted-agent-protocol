import { describe, expect, test, mock, beforeEach } from "bun:test";
import { RedisRegistryService } from "./src";
import type { RegisterAgentRequest } from "./interface";

// Mock Redis Client
const mockRedis = {
    incr: mock(),
    get: mock(),
    set: mock(),
    del: mock(),
    sadd: mock(),
    smembers: mock(),
    hgetall: mock(),
    hmset: mock(),
    keys: mock(),
    exists: mock(),
};

describe("RegistryService", () => {
    let service: RedisRegistryService;

    beforeEach(() => {
        // Reset mocks
        Object.values(mockRedis).forEach(m => m.mockClear());
        service = new RedisRegistryService(mockRedis as any);
    });

    test("createAgent should register agent and key", async () => {
        // Setup Mocks
        mockRedis.incr.mockResolvedValue(1); // Next ID
        mockRedis.exists.mockResolvedValue(0); // Domain unique check
        mockRedis.hmset.mockResolvedValue("OK");
        mockRedis.set.mockResolvedValue("OK");
        mockRedis.sadd.mockResolvedValue(1);

        // Mock getAgent return for addKey check
        mockRedis.hgetall.mockResolvedValue({
            id: "1",
            name: "Test Agent",
            domain: "https://agent.com",
            status: "active",
            created_at: "123",
            updated_at: "123"
        });

        const req: RegisterAgentRequest = {
            name: "Test Agent",
            domain: "https://agent.com",
            jwk: { kty: "RSA", kid: "key-1", n: "abc", e: "AQAB" }
        };

        const agent = await service.createAgent(req);

        expect(agent.id).toBe("1");
        expect(agent.name).toBe("Test Agent");
        expect(mockRedis.incr).toHaveBeenCalledWith("registry:ids:agent");
        // Verify Key was saved
        expect(mockRedis.set).toHaveBeenCalled();
        // Verify Agent was saved
        expect(mockRedis.hmset).toHaveBeenCalled();
        // Verify Lookup was saved
        expect(mockRedis.set).toHaveBeenCalledWith("registry:lookup:domain:https://agent.com", "1");
    });

    test("getKey should retrieve a stored key", async () => {
        const mockKeyData = JSON.stringify({
            kty: "RSA",
            kid: "key-1",
            agent_id: "1",
            created_at: 1234567890,
            status: "active"
        });

        mockRedis.get.mockResolvedValue(mockKeyData);

        const key = await service.getKey("key-1");

        expect(key).not.toBeNull();
        expect(key?.kid).toBe("key-1");
        expect(mockRedis.get).toHaveBeenCalledWith("registry:key:key-1");
    });
});
