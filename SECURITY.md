# Security Policy

## Supported Versions

Only the latest 1.x release receives security fixes.

| Version | Supported |
| ------- | --------- |
| latest 1.x | Yes |
| older 1.x | No |

## Reporting a Vulnerability

Please do **not** open a public issue for a security vulnerability.

Instead, report it privately via one of:

- **GitHub private security advisory:** <https://github.com/dheckman-dev/cisco-eox-query/security/advisories/new>
- **Email:** [david@heckman.network](mailto:david@heckman.network)

We will acknowledge receipt within **48 hours** and work toward coordinated disclosure, generally publishing a fix and advisory within 90 days or as agreed with the reporter.

## Security Considerations for Users

- **Credentials:** Cisco EOX API credentials (`client_id`/`client_secret`) must be supplied at runtime via environment variables (`EOX_CLIENT_ID`, `EOX_CLIENT_SECRET`, `EOX_ACCESS_TOKEN`) or constructor arguments. Never hard-code or commit credentials.
- **TLS:** All traffic to the Cisco API is over HTTPS. The client does not disable TLS certificate verification.
- **Network posture:** The package only makes outbound requests to the Cisco EOX API endpoints. It does not accept inbound connections.
- **Dependencies:** Dependencies are pinned via `uv.lock`. Keep the package updated to receive dependency security fixes.