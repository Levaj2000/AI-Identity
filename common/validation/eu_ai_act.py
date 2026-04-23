"""EU AI Act Annex III risk-class enumeration + validation.

Source: Regulation (EU) 2024/1689, Annex III (high-risk AI systems).
The categories below are the canonical letter-codes used throughout the
Act; storing only the code (e.g. `"3(a)"`) on the agent keeps the field
compact and lets the export builder resolve the human-readable label
from this module at render time — avoiding a schema migration every
time the Commission publishes corrigenda.

Used by:
- `Agent.eu_ai_act_risk_class` (validated at schema layer on create/update)
- Compliance export builder (#273) when producing
  `agent_risk_classification.csv` and the Annex IV section
"""

# Canonical Annex III category codes. Keys are the stored value; values
# are the human-readable title, resolved by the export builder.
# `not_in_scope` is the explicit "we considered it and this agent is not
# a high-risk system under Annex III" marker — distinct from `None`
# which means "not yet classified".
ANNEX_III_CATEGORIES: dict[str, str] = {
    # 1. Biometrics (Art. 6(2), Annex III §1)
    "1(a)": "Remote biometric identification systems",
    "1(b)": "Biometric categorisation by sensitive attributes",
    "1(c)": "Emotion recognition systems",
    # 2. Critical infrastructure (Annex III §2)
    "2(a)": "Safety components in critical digital infrastructure, road traffic, and supply of water, gas, heating, and electricity",
    # 3. Education and vocational training (Annex III §3)
    "3(a)": "Determining access, admission, or assignment to educational institutions",
    "3(b)": "Evaluating learning outcomes, including steering the learning process",
    "3(c)": "Assessing the appropriate level of education an individual will receive",
    "3(d)": "Monitoring and detecting prohibited behaviour during tests",
    # 4. Employment and workers' management (Annex III §4)
    "4(a)": "Recruitment, job-ad targeting, application analysis, candidate evaluation",
    "4(b)": "Decisions on promotion/termination, task allocation, performance monitoring",
    # 5. Access to essential private and public services (Annex III §5)
    "5(a)": "Eligibility for public assistance benefits and services",
    "5(b)": "Evaluating creditworthiness or establishing credit score (excluding fraud detection)",
    "5(c)": "Dispatching or prioritising emergency response services",
    "5(d)": "Risk assessment and pricing in life and health insurance",
    # 6. Law enforcement (Annex III §6)
    "6(a)": "Assessing risk of a natural person becoming a victim of criminal offences",
    "6(b)": "Polygraphs and similar tools",
    "6(c)": "Evaluating reliability of evidence during investigation or prosecution",
    "6(d)": "Assessing risk of offending or re-offending",
    "6(e)": "Profiling of natural persons in the course of detection / investigation / prosecution",
    # 7. Migration, asylum, and border control (Annex III §7)
    "7(a)": "Polygraphs and similar tools in migration, asylum, or border control",
    "7(b)": "Risk assessment of a person seeking to enter or having entered",
    "7(c)": "Examining applications for asylum, visa, or residence permits",
    "7(d)": "Detection, recognition, or identification in the migration context",
    # 8. Administration of justice and democratic processes (Annex III §8)
    "8(a)": "Assisting judicial authorities in researching and interpreting facts and law",
    "8(b)": "Influencing the outcome of elections or referendums, or voting behaviour",
}

# Sentinel for agents the deployer has evaluated and determined to be
# out of scope for Annex III. Explicit — not the same as `None`, which
# means "not classified yet".
NOT_IN_SCOPE = "not_in_scope"

# Union of all accepted values. `None` on the column means unclassified;
# presence in this set means the deployer has made a determination.
ALLOWED_RISK_CLASSES: frozenset[str] = frozenset({*ANNEX_III_CATEGORIES.keys(), NOT_IN_SCOPE})


def validate_risk_class(value: str | None) -> str | None:
    """Validate a proposed `eu_ai_act_risk_class` value.

    `None` is always valid — it means "not classified yet". For non-None
    values, raise `ValueError` if the code isn't an Annex III category
    or the `not_in_scope` sentinel.
    """
    if value is None:
        return None
    if value not in ALLOWED_RISK_CLASSES:
        msg = (
            f"Invalid eu_ai_act_risk_class: {value!r}. "
            f"Expected one of the EU AI Act Annex III category codes "
            f"(e.g. '3(a)', '4(b)') or '{NOT_IN_SCOPE}'."
        )
        raise ValueError(msg)
    return value
