import type {
    Agent,
    RegistryKey,
    RegistryService,
    RegisterAgentRequest,
    AddKeyRequest,
} from "./interface";
import { RegistryError } from "./interface";

export class MemoryRegistryService implements RegistryService {
    private agents = new Map<string, Agent>();
    private keys = new Map<string, RegistryKey>();
    private domainIndex = new Map<string, string>();
    private idCounter = Math.floor(Math.random() * 1000000);

    async listAgents(): Promise<Agent[]> {
        return Array.from(this.agents.values());
    }

    async getAgent(id: string): Promise<Agent | null> {
        return this.agents.get(id) || null;
    }

    async getAgentByDomain(domain: string): Promise<Agent | null> {
        const id = this.domainIndex.get(domain);
        if (!id) return null;
        return this.agents.get(id) || null;
    }

    async createAgent(req: RegisterAgentRequest): Promise<Agent> {
        if (this.domainIndex.has(req.domain)) {
            throw new RegistryError("CONFLICT", `Domain ${req.domain} already registered`, 409);
        }

        const id = (this.idCounter++).toString();
        const now = Date.now();
        const agent: Agent = {
            id,
            name: req.name,
            domain: req.domain,
            status: 'active',
            created_at: now,
            updated_at: now
        };

        this.agents.set(id, agent);
        this.domainIndex.set(req.domain, id);

        await this.addKey(id, { jwk: req.jwk });

        return agent;
    }

    async updateAgent(id: string, updates: Partial<Pick<Agent, 'name' | 'status'>>): Promise<Agent> {
        const agent = this.agents.get(id);
        if (!agent) throw new RegistryError("NOT_FOUND", "Agent not found", 404);

        if (updates.name) agent.name = updates.name;
        if (updates.status) agent.status = updates.status;
        agent.updated_at = Date.now();

        this.agents.set(id, agent);
        return agent;
    }

    async deleteAgent(id: string): Promise<void> {
        const agent = this.agents.get(id);
        if (!agent) return;

        agent.status = 'inactive';
        agent.updated_at = Date.now();
        this.agents.set(id, agent);
    }

    async addKey(agentId: string, req: AddKeyRequest): Promise<RegistryKey> {
        const agent = this.agents.get(agentId);
        if (!agent) throw new RegistryError("NOT_FOUND", "Agent not found", 404);

        const kid = (req.jwk.kid as string) || `key-${Date.now()}`;

        if (this.keys.has(kid)) {
            throw new RegistryError("CONFLICT", `Key ${kid} already exists`, 409);
        }

        const key: RegistryKey = {
            ...req.jwk,
            kid,
            agent_id: agentId,
            created_at: Date.now(),
            status: 'active'
        };

        this.keys.set(kid, key);
        return key;
    }

    async getKey(kid: string): Promise<RegistryKey | null> {
        return this.keys.get(kid) || null;
    }

    async getAgentKeys(agentId: string): Promise<RegistryKey[]> {
        return Array.from(this.keys.values()).filter(k => k.agent_id === agentId);
    }
}
