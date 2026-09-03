# Security Policy

## Reporting a vulnerability

Do not open a public issue containing exploit details, credentials, private
addresses, or logs. Use GitHub's private vulnerability-reporting feature for
this repository. If private reporting is unavailable, open a minimal issue
asking the maintainer to establish a private channel; omit technical details.

Include the affected version/commit, prerequisites, impact, a minimal
reproduction, and suggested remediation. Remove tokens, API keys, cookies,
and private network details (SolarWinds server hostnames, credentials).

## Response targets

These are project targets, not an SLA: acknowledge critical/high reports in
three business days, establish severity and containment in seven, and publish
a coordinated fix/advisory as soon as safely validated. Lower-severity issues
are prioritized by exploitability and impact.

## Supported version

Only the latest published release and the default branch receive security
fixes. Operators should keep Home Assistant and the SolarWinds Orion platform
current and retain a tested rollback/backup.

## Security boundaries

SWIS is a privileged Home Assistant integration, not a sandbox or an
independent compliance product. It stores the configured SolarWinds
Information Service (SWIS) username and password as Home Assistant config
entry data and uses them for read-only SWQL queries; it cannot prevent a
malicious integration in the same Python process from reading shared memory
or files. It does not verify the SolarWinds server's TLS certificate unless
`verify_ssl` is enabled in the config flow.
