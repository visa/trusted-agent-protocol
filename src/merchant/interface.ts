export interface Product {
    id: string;
    name: string;
    price: number;
    description: string;
}

export interface MerchantConfig {
    port: number;
    debug?: boolean;
}

export interface MerchantService {
    readonly port: number;
    start(): void;
    stop(): void;
}
