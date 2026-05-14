# EU Medical Device Regulation (MDR) MCP

[![PyPI](https://img.shields.io/pypi/v/mdr-medical-device-mcp)](https://pypi.org/project/mdr-medical-device-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-governance--mcp-purple)](https://meok.ai)

EU MDR (Reg 2017/745) and IVDR (Reg 2017/746) compliance for medical device + IVD manufacturers, including AI/ML SaMD classification.

## Install

```bash
pip install mdr-medical-device-mcp
```

## Tools

| Tool | Purpose |
|------|---------|
| `classify_medical_device` | MDR Annex VIII risk classification (Class I/IIa/IIb/III) |
| `classify_ivd` | IVDR Annex VIII IVD classification (Class A/B/C/D) |
| `samd_ai_ml_check` | AI/ML SaMD classification + IMDRF risk framework |
| `ce_marking_requirements` | MDR Article 19 CE marking + Notified Body involvement |
| `eudamed_registration` | EUDAMED UDI-DI + Basic UDI registration requirements |

## Pairs with

- `meok-attestation-api` — POST results to https://meok-attestation-api.vercel.app/sign for cryptographically signed compliance certs
- `meok-attestation-verify` — public verification of any MEOK-signed cert
- Other MEOK governance MCPs via SOV3 `mcp_bridge_call`

## Pricing

- **Free**: 10 calls/day. No API key required.
- **Pro** £79/mo: unlimited + signed attestations. [Subscribe](https://buy.stripe.com/14A4gB3K4eUWgYR56o8k836)
- **Enterprise** £1,499/mo: white-label + on-premise + SLA. hello@meok.ai

## Status

Scaffold v1.0.0 ships the MCP framework + 5 tool stubs. v1.1.0 will add real regulation data ingestion.

If your team needs this MCP fully-loaded faster, ping hello@meok.ai for sponsored development.

## License

MIT © MEOK AI Labs
