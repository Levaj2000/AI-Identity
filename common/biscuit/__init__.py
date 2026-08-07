"""Biscuit presentation credentials for mandates (demo tier).

Shared between the Mandate Service (mint) and the gateway (verify) so both
sides agree on the Datalog vocabulary. See common/biscuit/tokens.py.
"""

from common.biscuit.receipts import mint_receipt, verify_receipt
from common.biscuit.tokens import (
    BiscuitUnavailableError,
    MintedBiscuit,
    PresentationResult,
    attenuate_spend_ceiling,
    authorize_presentation,
    mint_mandate_biscuit,
    root_public_key_hex,
)

__all__ = [
    "BiscuitUnavailableError",
    "MintedBiscuit",
    "PresentationResult",
    "attenuate_spend_ceiling",
    "authorize_presentation",
    "mint_mandate_biscuit",
    "mint_receipt",
    "root_public_key_hex",
    "verify_receipt",
]
