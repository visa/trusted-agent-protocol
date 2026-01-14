import { describe, test, expect, beforeAll, afterAll } from "bun:test";
import { startMerchant } from "./impl";
import type { MerchantService, Product } from "./interface";

const TEST_PORT = 3002;
const BASE_URL = `http://localhost:${TEST_PORT}`;

let service: MerchantService;

beforeAll(() => {
    service = startMerchant({
        port: TEST_PORT,
        debug: false
    });
});

afterAll(() => {
    service.stop();
});

describe("Merchant Service", () => {
    test("GET / should return HTML UI", async () => {
        const res = await fetch(`${BASE_URL}/`);
        expect(res.status).toBe(200);
        const text = await res.text();
        expect(text).toContain("TAP Merchant Store");
    });

    test("GET /api/products should return list of products", async () => {
        const res = await fetch(`${BASE_URL}/api/products`);
        expect(res.status).toBe(200);
        const data = await res.json();
        expect(Array.isArray(data)).toBe(true);
        expect(data.length).toBeGreaterThan(0);
        expect(data[0]).toHaveProperty("id");
        expect(data[0]).toHaveProperty("name");
    });

    test("GET /api/products/1 should return specific product", async () => {
        const res = await fetch(`${BASE_URL}/api/products/1`);
        expect(res.status).toBe(200);
        const data = await res.json();
        expect(data.id).toBe("1");
        expect(data.name).toBe("Premium Coffee");
    });

    test("GET /api/products/999 should return 404", async () => {
        const res = await fetch(`${BASE_URL}/api/products/999`);
        expect(res.status).toBe(404);
    });
});
