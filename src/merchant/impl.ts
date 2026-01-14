import type { MerchantConfig, MerchantService, Product } from './interface';
import type { Server } from 'bun';
import path from 'path';

// In-memory data
const PRODUCTS: Product[] = [
    { id: "1", name: "Premium Coffee", price: 12.99, description: "Ethically sourced, medium roast." },
    { id: "2", name: "Wireless Headphones", price: 89.99, description: "Noise cancelling with long battery life." },
    { id: "3", name: "Ergonomic Mouse", price: 45.00, description: "Reduces strain during long work sessions." },
    { id: "4", name: "Mechanical Keyboard", price: 120.50, description: "Tactile switches for satisfying typing." }
];

export class MerchantServer implements MerchantService {
    private server: Server<any> | null = null;
    private config: MerchantConfig;

    constructor(config: MerchantConfig) {
        this.config = config;
    }

    get port(): number {
        if (!this.server) return this.config.port;
        return this.server.port as number;
    }

    start(): void {
        this.server = Bun.serve({
            port: this.config.port,
            fetch: async (req) => {
                const url = new URL(req.url);

                if (this.config?.debug) {
                    console.log(`[Merchant] ${req.method} ${url.pathname}`);
                }

                if (url.pathname === '/api/products' && req.method === 'GET') {
                    return new Response(JSON.stringify(PRODUCTS), {
                        headers: { "Content-Type": "application/json" }
                    });
                }

                const productMatch = url.pathname.match(/^\/api\/products\/([^\/]+)$/);
                if (productMatch && req.method === 'GET') {
                    const id = productMatch[1];
                    const product = PRODUCTS.find(p => p.id === id);

                    if (product) {
                        return new Response(JSON.stringify(product), {
                            headers: { "Content-Type": "application/json" }
                        });
                    } else {
                        return new Response(JSON.stringify({ error: "Product not found" }), {
                            status: 404,
                            headers: { "Content-Type": "application/json" }
                        });
                    }
                }

                // Match static files
                let filePath = url.pathname;
                if (filePath === '/') {
                    filePath = '/index.html';
                }

                const fullPath = path.join(import.meta.dir, "public", filePath);
                const file = Bun.file(fullPath);

                if (await file.exists()) {
                    return new Response(file);
                }

                return new Response("Not Found", { status: 404 });
            }
        });
    }

    stop(): void {
        if (this.server) {
            this.server.stop();
            this.server = null;
        }
    }
}

export function startMerchant(config: MerchantConfig): MerchantService {
    const server = new MerchantServer(config);
    server.start();
    return server;
}
