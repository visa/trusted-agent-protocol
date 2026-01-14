import { redis } from "bun";
import {
    type RegistryService,
    type Agent,
    type RegisterAgentRequest,
    type AddKeyRequest,
    type RegistryKey,
    RegistryError
} from "./interface";

export class RedisRegistryService implements RegistryService {
    private db: typeof redis;

    constructor(client: typeof redis = redis) {
        this.db = client;
    }

    async listAgents(): Promise<Agent[]> {
        const ids = await this.db.smembers("registry:agents:index");
        const agents: Agent[] = [];

        for (const id of ids) {
            const agent = await this.getAgent(id);
            if (agent) agents.push(agent);
        }

        return agents;
    }

    async getAgent(id: string): Promise<Agent | null> {
        const data = await this.db.hgetall(`registry:agent:${id}`);
        if (!data) return null;

        return {
            id: data.id,
            name: data.name,
            domain: data.domain,
            status: data.status as 'active' | 'inactive',
            created_at: parseInt(data.created_at || '0'),
            updated_at: parseInt(data.updated_at || '0')
        };
    }

    async getAgentByDomain(domain: string): Promise<Agent | null> {
        const id = await this.db.get(`registry:lookup:domain:${domain}`);
        if (!id) return null;
        return this.getAgent(id);
    }

    async createAgent(req: RegisterAgentRequest): Promise<Agent> {
        const existing = await this.getAgentByDomain(req.domain);
        if (existing) {
            throw new RegistryError("CONFLICT", `Domain ${req.domain} already registered`, 409);
        }

        const id = (await this.db.incr("registry:ids:agent")).toString();
        const now = Date.now();

        const agent: Agent = {
            id,
            name: req.name,
            domain: req.domain,
            status: 'active',
            created_at: now,
            updated_at: now
        };

        await Promise.all([
            this.db.hmset(`registry:agent:${id}`, {
                id: agent.id,
                name: agent.name,
                domain: agent.domain,
                status: agent.status,
                created_at: agent.created_at.toString(),
                updated_at: agent.updated_at.toString()
            }),
            this.db.set(`registry:lookup:domain:${req.domain}`, id),
            this.db.sadd("registry:agents:index", id)
        ]);

        await this.addKey(id, { jwk: req.jwk });

        return agent;
    }

    async updateAgent(id: string, updates: Partial<Pick<Agent, 'name' | 'status'>>): Promise<Agent> {
        const agent = await this.getAgent(id);
        if (!agent) throw new RegistryError("NOT_FOUND", "Agent not found", 404);

        const now = Date.now();
        const updateData: Record<string, string> = { updated_at: now.toString() };
        if (updates.name) updateData.name = updates.name;
        if (updates.status) updateData.status = updates.status;

        await this.db.hmset(`registry:agent:${id}`, updateData);

        return (await this.getAgent(id))!;
    }

    async deleteAgent(id: string): Promise<void> {
        const agent = await this.getAgent(id);
        if (!agent) return;

        await this.updateAgent(id, { status: 'inactive' });
    }

    async addKey(agentId: string, req: AddKeyRequest): Promise<RegistryKey> {
        const agent = await this.getAgent(agentId);
        if (!agent) throw new RegistryError("NOT_FOUND", "Agent not found", 404);

        const kid = (req.jwk.kid as string) || crypto.randomUUID();
        const now = Date.now();

        const registryKey: RegistryKey = {
            ...req.jwk,
            kid,
            agent_id: agentId,
            created_at: now,
            status: 'active'
        };

        const keyStr = JSON.stringify(registryKey);

        const exists = await this.db.exists(`registry:key:${kid}`);
        if (exists) throw new RegistryError("CONFLICT", `Key ${kid} already exists`, 409);

        await Promise.all([
            this.db.set(`registry:key:${kid}`, keyStr),
            this.db.sadd(`registry:agent:${agentId}:keys`, kid)
        ]);

        return registryKey;
    }

    async getKey(kid: string): Promise<RegistryKey | null> {
        const data = await this.db.get(`registry:key:${kid}`);
        if (!data) return null;
        return JSON.parse(data);
    }

    async getAgentKeys(agentId: string): Promise<RegistryKey[]> {
        const kids = await this.db.smembers(`registry:agent:${agentId}:keys`);
        const keys: RegistryKey[] = [];

        for (const kid of kids) {
            const k = await this.getKey(kid);
            if (k) keys.push(k);
        }
        return keys;
    }
}
