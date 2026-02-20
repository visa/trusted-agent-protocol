import os
import logging

logger = logging.getLogger(__name__)

# Module-level singleton
_server = None


def initialize_x402():
    """Initialize x402 resource server at startup. Call once from main.py."""
    global _server

    if not os.getenv("X402_ENABLED", "false").lower() == "true":
        logger.info("x402 payments disabled (X402_ENABLED != true)")
        return

    from x402.server import x402ResourceServer
    from x402.http import HTTPFacilitatorClient, FacilitatorConfig
    from x402.mechanisms.evm.exact import ExactEvmServerScheme
    from x402.mechanisms.svm.exact import ExactSvmServerScheme

    facilitator_url = os.getenv(
        "X402_FACILITATOR_URL", "https://x402.org/facilitator"
    )
    config = FacilitatorConfig(url=facilitator_url)
    client = HTTPFacilitatorClient(config)

    svm_network = os.getenv("X402_SVM_NETWORK", "solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1")
    evm_network = os.getenv("X402_EVM_NETWORK", "eip155:84532")

    _server = x402ResourceServer(facilitator_clients=[client])
    _server.register(evm_network, ExactEvmServerScheme())
    _server.register(svm_network, ExactSvmServerScheme())
    _server.initialize()

    logger.info("x402 resource server initialized (facilitator=%s)", facilitator_url)


def is_enabled() -> bool:
    return _server is not None


def build_checkout_requirements(total_usd: float) -> list:
    """Build PaymentRequirements list for configured networks.

    Uses the server's build_payment_requirements() which enriches requirements
    with facilitator data (e.g. feePayer for SVM transactions).
    """
    from x402.schemas import ResourceConfig

    if _server is None:
        return []

    svm_address = os.getenv("X402_SVM_ADDRESS", "")
    evm_address = os.getenv("X402_EVM_ADDRESS", "")
    svm_network = os.getenv("X402_SVM_NETWORK", "solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1")
    evm_network = os.getenv("X402_EVM_NETWORK", "eip155:84532")

    requirements = []

    if svm_address:
        config = ResourceConfig(
            scheme="exact",
            pay_to=svm_address,
            price=total_usd,
            network=svm_network,
            max_timeout_seconds=300,
        )
        requirements.extend(_server.build_payment_requirements(config))

    if evm_address:
        config = ResourceConfig(
            scheme="exact",
            pay_to=evm_address,
            price=total_usd,
            network=evm_network,
            max_timeout_seconds=300,
        )
        requirements.extend(_server.build_payment_requirements(config))

    return requirements


def create_payment_required(requirements: list, description: str = ""):
    """Build a PaymentRequired object for the 402 response."""
    from x402.schemas import PaymentRequired

    return PaymentRequired(
        accepts=requirements,
        error=description or "Payment Required",
    )


async def settle(payment_header: str, requirements: list):
    """
    Decode the payment header, match requirements, and settle on-chain.
    settle_payment() calls verify internally, so no separate verify step needed.

    Returns (success: bool, settle_response | None, error_msg: str)
    """
    from x402.http import decode_payment_signature_header

    if _server is None:
        return False, None, "x402 not initialized"

    try:
        payload = decode_payment_signature_header(payment_header)
    except Exception as exc:
        logger.error("Failed to decode payment header: %s", exc)
        return False, None, f"Invalid payment header: {exc}"

    try:
        matched_req = _server.find_matching_requirements(requirements, payload)
        if matched_req is None:
            return False, None, "Payment does not match any accepted requirement"
    except Exception as exc:
        logger.error("Error matching requirements: %s", exc)
        return False, None, f"Requirement matching failed: {exc}"

    try:
        settle_resp = await _server.settle_payment(payload, matched_req)
        if not settle_resp.success:
            return False, None, f"Settlement failed: {settle_resp.error_reason or 'unknown'}"
    except Exception as exc:
        logger.error("Payment settlement error: %s", exc)
        return False, None, f"Settlement error: {exc}"

    return True, settle_resp, ""
