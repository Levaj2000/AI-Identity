# Security Policy

## Reporting a vulnerability

If you believe you have found a security vulnerability in this repository or in the
AI Identity platform (`api.ai-identity.co`, `www.ai-identity.co`), please report it
privately:

- **Email:** jeff@ai-identity.co (subject line starting with `[SECURITY]`)
- Please include steps to reproduce, the affected component, and impact as you
  understand it.

You will receive an acknowledgment within **3 business days**. Please allow us a
reasonable window to investigate and remediate before any public disclosure — we
will keep you informed of progress and credit you in the fix notes if you wish.

There is currently no bug-bounty program; reports are handled on a coordinated,
good-faith basis.

## Scope

In scope:

- Code in this repository (gateway, API, SDKs, offline verifier CLI)
- The hosted platform endpoints listed above
- The integrity guarantees this project makes: audit-chain tamper evidence,
  signature verification, Evidence Anchor inclusion proofs — **a way to forge or
  silently alter a verifiable record is exactly the class of finding we most want
  to hear about**

Out of scope:

- Denial-of-service or volumetric testing against the hosted platform
- Social engineering, phishing, or physical attacks
- Findings in third-party dependencies with no demonstrated impact here (report
  those upstream)

Please do not run automated scanners or exploit attempts against production
endpoints beyond what is needed for a minimal proof of concept.

## Supported versions

The `main` branch and the currently deployed platform are supported. Exported
Case File bundles embed the verifier at export time; if a verifier issue is
found, re-export after the fix to pick it up.
