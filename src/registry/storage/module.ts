import { RegistryService } from "./interface";
import { RedisRegistryService } from "./redis/module";
import { MemoryRegistryService } from "./memory/module";
import { SqliteRegistryService } from "./sqlite/module";

export * from "./interface";
export { RedisRegistryService, MemoryRegistryService, SqliteRegistryService };

export function getRegistryService(): RegistryService {
    const type = process.env.REGISTRY_STORAGE || 'memory';

    switch (type) {
        case 'redis':
            return new RedisRegistryService();
        case 'sqlite':
            return new SqliteRegistryService(process.env.REGISTRY_DB_PATH || 'registry.db');
        case 'memory':
        default:
            return new MemoryRegistryService();
    }
}
