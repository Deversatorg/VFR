# Security Scan

Use this command when reviewing auth, billing, uploads, AI artifacts, or externally reachable endpoints.

## Workflow

1. Identify trust boundaries and attacker-controlled inputs.
2. Trace each input to persistence, filesystem access, external services, logs, and generated artifacts.
3. Look for missing validation, over-broad access, or dangerous fallbacks.
4. Check whether secrets or internal paths can leak through logs or API responses.
5. Recommend the smallest safe fix and the narrowest useful regression test.

## Repo-Specific Focus

- JWT issuance, validation, and `Testing`-environment behavior
- Billing and admin endpoints in `VFR.Auth`
- Direct browser-to-AI-engine calls and CORS policy
- S3/local-path fallback behavior in `VFR.AiEngine`
- Unsafe model or artifact loading in Python/PyTorch code
- Profile and avatar metadata that may contain sensitive body data

## Output

Return findings first. Include exploit path, impact, and the smallest viable mitigation.
