import { startMerchant } from './impl';

const PORT = parseInt(process.env.PORT || "3000");
const DEBUG = process.env.DEBUG === "true";

console.log(`Starting Merchant Service on port ${PORT}...`);

startMerchant({
    port: PORT,
    debug: DEBUG
});

console.log(`Merchant Service listening on http://localhost:${PORT}`);
