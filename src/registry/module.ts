import type { Server } from "bun";
import { RegistryError } from "./interface";
import type { RegistryService } from "./interface";
import { getRegistryService } from "./storage/module";

export * from "./interface";
export * from "./storage/module";

const corsHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
};

function createHandler(service: RegistryService) {
    return async function handleRequest(req: Request): Promise<Response> {
        const url = new URL(req.url);
        const path = url.pathname;
        const method = req.method;

        // CORS Preflight
        if (method === "OPTIONS") {
            return new Response(null, { headers: corsHeaders });
        }

        try {
            // API Routes

            // GET /agents
            if (method === "GET" && path === "/agents") {
                const agents = await service.listAgents();
                return Response.json(agents, { headers: corsHeaders });
            }

            // POST /agents
            if (method === "POST" && path === "/agents") {
                const body = await req.json() as any;
                const agent = await service.createAgent(body);
                return Response.json(agent, { status: 201, headers: corsHeaders });
            }

            // GET /keys/:kid (Global Lookup)
            const keyMatch = path.match(/^\/keys\/([^\/]+)$/);
            if (method === "GET" && keyMatch) {
                const kid = keyMatch[1] as string;
                const key = await service.getKey(kid);
                if (!key) return new Response("Key not found", { status: 404, headers: corsHeaders });
                return Response.json(key, { headers: corsHeaders });
            }

            // Agent Specific Routes
            const agentMatch = path.match(/^\/agents\/([^\/]+)(.*)$/);
            if (agentMatch) {
                const agentId = agentMatch[1] as string;
                const subPath = agentMatch[2] as string;

                // GET /agents/:id
                if (method === "GET" && (subPath === "" || subPath === "/")) {
                    const agent = await service.getAgent(agentId);
                    if (!agent) return new Response("Agent not found", { status: 404, headers: corsHeaders });
                    return Response.json(agent, { headers: corsHeaders });
                }

                // PUT /agents/:id
                if (method === "PUT" && (subPath === "" || subPath === "/")) {
                    const updates = await req.json() as any;
                    const agent = await service.updateAgent(agentId, updates);
                    return Response.json(agent, { headers: corsHeaders });
                }

                // DELETE /agents/:id
                if (method === "DELETE" && (subPath === "" || subPath === "/")) {
                    await service.deleteAgent(agentId);
                    return new Response(null, { status: 204, headers: corsHeaders });
                }

                // POST /agents/:id/keys
                if (method === "POST" && subPath === "/keys") {
                    const body = await req.json() as any;
                    const key = await service.addKey(agentId, body);
                    return Response.json(key, { status: 201, headers: corsHeaders });
                }

                // GET /agents/:id/keys/:kid
                const keySubMatch = subPath.match(/^\/keys\/([^\/]+)$/);
                if (method === "GET" && keySubMatch) {
                    const kid = keySubMatch[1] as string;
                    const key = await service.getKey(kid);
                    if (!key || key.agent_id !== agentId) {
                        return new Response("Key not found for agent", { status: 404, headers: corsHeaders });
                    }
                    return Response.json(key, { headers: corsHeaders });
                }

                // GET /agents/:id/keys
                if (method === "GET" && subPath === "/keys") {
                    const keys = await service.getAgentKeys(agentId);
                    return Response.json(keys, { headers: corsHeaders });
                }
            }

            return new Response("Not Found", { status: 404, headers: corsHeaders });

        } catch (error) {
            console.error(error);
            if (error instanceof RegistryError) {
                return new Response(JSON.stringify({ error: error.message }), {
                    status: error.status,
                    headers: { ...corsHeaders, "Content-Type": "application/json" }
                });
            }
            return new Response(JSON.stringify({ error: "Internal Server Error" }), {
                status: 500,
                headers: { ...corsHeaders, "Content-Type": "application/json" }
            });
        }
    }
}

export class RegistryServer {
    private server: Server<any> | null = null;
    private service: RegistryService;
    private _port: number;

    constructor(port: number | string = 0, service?: RegistryService) {
        this._port = Number(port);
        this.service = service || getRegistryService();
    }

    get port(): number {
        if (!this.server) {
            throw new Error("Server not started");
        }
        return (this.server as any).port;
    }

    async start(): Promise<void> {
        this.server = Bun.serve({
            port: this._port,
            fetch: createHandler(this.service),
        });
        console.log(`Registry Service listening on port ${this.server.port} (Service: ${this.service.constructor.name})`);
    }

    stop() {
        if (this.server) {
            this.server.stop();
            this.server = null;
        }
    }
}

export function startRegistry(port: number | string = 0, options: { service?: RegistryService } = {}) {
    const server = new RegistryServer(port, options.service);
    server.start();
    return server;
}

if (import.meta.main) {
    const port = process.env.PORT || 9002;
    startRegistry(port);
}
