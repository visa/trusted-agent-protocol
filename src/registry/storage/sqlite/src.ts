import { Database } from "bun:sqlite";
import {
    type RegistryService,
    type Agent,
    type RegisterAgentRequest,
    type AddKeyRequest,
    type RegistryKey,
    RegistryError
} from "./interface";

export class SqliteRegistryService implements RegistryService {
    private db: Database;

    constructor(dbPath: string = ":memory:") {
        this.db = new Database(dbPath);
        this.init();
    }

    private init() {
        this.db.run(`
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT,
                domain TEXT UNIQUE,
                status TEXT,
                created_at INTEGER,
                updated_at INTEGER
            )
        `);

        this.db.run(`
            CREATE TABLE IF NOT EXISTS keys (
                kid TEXT PRIMARY KEY,
                agent_id TEXT,
                json TEXT,
                created_at INTEGER
            )
        `);
    }

    async listAgents(): Promise<Agent[]> {
        const rows = this.db.query("SELECT * FROM agents").all() as any[];
        return rows.map(row => ({
            id: row.id,
            name: row.name,
            domain: row.domain,
            status: row.status as 'active' | 'inactive',
            created_at: row.created_at,
            updated_at: row.updated_at
        }));
    }

    async getAgent(id: string): Promise<Agent | null> {
        const row = this.db.query("SELECT * FROM agents WHERE id = ?").get(id) as any;
        if (!row) return null;
        return {
            id: row.id,
            name: row.name,
            domain: row.domain,
            status: row.status as 'active' | 'inactive',
            created_at: row.created_at,
            updated_at: row.updated_at
        };
    }

    async getAgentByDomain(domain: string): Promise<Agent | null> {
        const row = this.db.query("SELECT * FROM agents WHERE domain = ?").get(domain) as any;
        if (!row) return null;
        return {
            id: row.id,
            name: row.name,
            domain: row.domain,
            status: row.status as 'active' | 'inactive',
            created_at: row.created_at,
            updated_at: row.updated_at
        };
    }

    async createAgent(req: RegisterAgentRequest): Promise<Agent> {
        const existing = await this.getAgentByDomain(req.domain);
        if (existing) {
            throw new RegistryError("CONFLICT", `Domain ${req.domain} already registered`, 409);
        }

        const id = crypto.randomUUID(); // Use UUID for SQLite
        const now = Date.now();
        const agent: Agent = {
            id,
            name: req.name,
            domain: req.domain,
            status: 'active',
            created_at: now,
            updated_at: now
        };

        const insert = this.db.prepare(`
            INSERT INTO agents (id, name, domain, status, created_at, updated_at)
            VALUES ($id, $name, $domain, $status, $created_at, $updated_at)
        `);

        insert.run({
            $id: agent.id,
            $name: agent.name,
            $domain: agent.domain,
            $status: agent.status,
            $created_at: agent.created_at,
            $updated_at: agent.updated_at
        });

        await this.addKey(id, { jwk: req.jwk });

        return agent;
    }

    async updateAgent(id: string, updates: Partial<Pick<Agent, 'name' | 'status'>>): Promise<Agent> {
        const agent = await this.getAgent(id);
        if (!agent) throw new RegistryError("NOT_FOUND", "Agent not found", 404);

        const now = Date.now();

        if (updates.name) {
            this.db.run("UPDATE agents SET name = ?, updated_at = ? WHERE id = ?", [updates.name, now, id]);
        }
        if (updates.status) {
            this.db.run("UPDATE agents SET status = ?, updated_at = ? WHERE id = ?", [updates.status, now, id]);
        }

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

        const existing = this.db.query("SELECT kid FROM keys WHERE kid = ?").get(kid);
        if (existing) throw new RegistryError("CONFLICT", `Key ${kid} already exists`, 409);

        this.db.run(`
            INSERT INTO keys (kid, agent_id, json, created_at)
            VALUES (?, ?, ?, ?)
        `, [kid, agentId, JSON.stringify(registryKey), now]);

        return registryKey;
    }

    async getKey(kid: string): Promise<RegistryKey | null> {
        const row = this.db.query("SELECT json FROM keys WHERE kid = ?").get(kid) as any;
        if (!row) return null;
        return JSON.parse(row.json);
    }

    async getAgentKeys(agentId: string): Promise<RegistryKey[]> {
        const rows = this.db.query("SELECT json FROM keys WHERE agent_id = ?").all(agentId) as any[];
        return rows.map(row => JSON.parse(row.json));
    }
}
