"""Namespaced constraint types for the mandate document.

Until now a mandate could express exactly one bound, `spend_limit`, as a bare
field with no type discriminator. Adding a second kind of bound to that shape
is not a one-line change: there is nothing to dispatch on, so every consumer
would need to infer a constraint's kind from which keys happen to be present.

A constraint therefore carries a namespaced `type`, and the namespace is the
point. Types arrive from more than one place: ours, a standards body's, and a
counterparty's. `spend.ceiling` and `mastercard.payment.budget` can coexist
without either side having to win a naming argument first.

Unknown types are REJECTED, not skipped. A mandate is an authorization
document, so a bound this version cannot evaluate may be the one that
restricts the grant; treating it as absent would widen authority past what
the issuer signed. That is the same rule the service applies to unknown
top-level fields and to unevaluated `conditions`, and the same one argued
upstream in ocsf#1756.

Registered here is deliberately narrow. Naming a type is a promise to
evaluate it, and a registry longer than the evaluator is how a vocabulary
starts lying about what it enforces.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# --- The namespace ---

#: Dotted lowercase segments: `<domain>.<name>`, at least two deep. Two
#: segments minimum is what makes it a namespace rather than a bare word,
#: so a later `spend.ceiling` and someone else's `budget.ceiling` do not
#: collide on the unqualified noun.
NAMESPACE_PATTERN = r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$"
_NAMESPACE_RE = re.compile(NAMESPACE_PATTERN)

#: Cumulative monetary ceiling over the mandate's life. Registered so the
#: vocabulary names the bound the document already enforces, but NOT valid
#: inside `constraints`: `spend_limit` is its one encoding, and two ways to
#: say the same thing is how the two disagree later. See `Constraint`.
TYPE_SPEND_CEILING = "spend.ceiling"

#: Every type this version knows. Membership means "this name is real", not
#: "this version enforces it". See EVALUABLE_TYPES below.
REGISTERED_TYPES: frozenset[str] = frozenset({TYPE_SPEND_CEILING})

#: Types with an evaluator behind them. A registered type that is not here
#: is a name we have reserved and cannot yet check, which denies rather than
#: passes.
EVALUABLE_TYPES: frozenset[str] = frozenset()

#: Types that may not appear in `constraints` because a dedicated field on
#: the document already carries them.
_FIELD_BACKED_TYPES: frozenset[str] = frozenset({TYPE_SPEND_CEILING})


class UnknownConstraintTypeError(ValueError):
    """Raised for a constraint type this version does not recognize."""


class Constraint(BaseModel):
    """One namespaced bound on a mandate's authority.

    Part of the signed grant. `params` is intentionally open, because the
    shape of a bound varies by type and a closed union here would mean
    every new type is a schema migration; the type's evaluator validates
    its own params.
    """

    model_config = ConfigDict(extra="forbid")

    type: str = Field(
        pattern=NAMESPACE_PATTERN,
        description=(
            "Namespaced constraint type, e.g. 'spend.ceiling'. At least two "
            "dotted segments so an unqualified noun cannot collide with "
            "another vocabulary's."
        ),
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Type-specific parameters, validated by that type's evaluator.",
    )

    @field_validator("type")
    @classmethod
    def type_is_known(cls, v: str) -> str:
        if v in _FIELD_BACKED_TYPES:
            raise ValueError(
                f"'{v}' is carried by its own field on the mandate, not by "
                f"constraints[]. Two encodings of one bound is how the two "
                f"disagree later."
            )
        if v not in REGISTERED_TYPES:
            raise UnknownConstraintTypeError(
                f"Unknown constraint type '{v}'. A bound this version cannot "
                f"evaluate may be the one that restricts the grant, so it is "
                f"rejected rather than ignored. Registered: "
                f"{sorted(REGISTERED_TYPES) or 'none'}."
            )
        return v


def is_namespaced(type_name: str) -> bool:
    """Whether a string is shaped like a constraint type name."""
    return bool(_NAMESPACE_RE.match(type_name))


def unevaluable(constraints: list[Constraint]) -> list[str]:
    """Types present on the mandate that this version cannot check.

    Non-empty means the grant carries a bound nobody evaluated, which denies.
    Separate from validation because a type can be legitimately registered
    before its evaluator lands, and the document should still parse so an
    operator can see what it is holding.
    """
    return sorted({c.type for c in constraints if c.type not in EVALUABLE_TYPES})
