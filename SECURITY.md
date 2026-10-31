# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | Yes |
| < 0.1 | No |

## Reporting a vulnerability

Please do **not** open a public issue for a security vulnerability.

Report privately through GitHub's security advisory flow on this
repository ("Security" tab, "Report a vulnerability"), or by email to the
TechAurah team via the contact route at https://techaurah.com.

Please include: the affected version, a description of the issue, and the
steps or proof of concept needed to reproduce it.

We aim to acknowledge reports within 3 business days and to agree a
disclosure timeline with the reporter. QualBench runs agents against mock
tools only, but it handles agent endpoint URLs and API keys in
configuration, so credential-handling issues are in scope and taken
seriously.

## Scope notes

- QualBench never sends real messages, writes to a real CRM, or books a
  real calendar. If you find a path where a scenario run can reach a real
  external system other than the agent endpoint you configured, that is a
  vulnerability: please report it.
- API keys are read from the `--api-key` flag or the `QUALBENCH_API_KEY` /
  `OPENAI_API_KEY` environment variables and are never written to reports
  or results files.
