# Security Policy

## Supported Versions
| Version | Supported |
|---------|-----------|
| main    | ✅        |

## Reporting a Vulnerability
- **Do not** open a public issue with secrets.
- Email: `robenedwan@gmail.com` or use GitHub Private Vulnerability Reporting (Security tab → Report a vulnerability).
- Include: affected commit/branch, reproduction steps, impact.

## Secrets Handling
- Never commit real `.env` values. `.env.example` must contain placeholders only (`YOUR_KEY_HERE`, `postgresql://user:pass@host/db`).
- GitHub push protection and secret scanning are enabled — leaked Stripe/Paddle/SMTP/DB keys must be rotated immediately.
- Rotate via provider dashboards if a secret was ever pushed (even if reverted).

## Hardening
- Dependabot weekly (npm/pip/docker/github-actions)
- Branch protection on `main` (require PR + `verify` check)
- Actions pinned to SHA where possible
