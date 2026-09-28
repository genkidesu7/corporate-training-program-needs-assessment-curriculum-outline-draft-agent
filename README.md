# EDU-C2-030 — Corporate Training Program Needs Assessment & Curriculum Outline Draft Agent

> **Category**: Cat 2 (orchestrates multiple steps to accomplish a specific job-to-be-done)
> **Industry**: EDU

## Overview

EDU-C2-030 turns an HR/L&D manager's aggregate workforce profile and target METI
デジタルスキル標準 (DSS) level into a validated Training Needs Assessment (TNA) report and a
phased, DSS-aligned curriculum outline. It runs a six-node pipeline —
`NeedsDataIngest → SkillGapAnalyze → LearningObjectiveGenerate → CurriculumFrameworkRetrieve →
OutlineDraft → OutputValidate` — that maps role-cohort skill levels to DSS competency
dimensions, generates Bloom's-taxonomy-aligned learning objectives per gap, retrieves relevant
DSS and 職業能力開発促進法 framework passages, and drafts a phased curriculum outline. No
individual employee data is accepted or retained; only aggregate role-cohort data is processed.

This is an agent template built with the **AGENTIC STAR** development platform and the
**AgentCore Framework**. It is intended to be taken as a starting point: fork it, adapt it to
your own data and policies, and run it inside your own AGENTIC STAR deployment.

## Features

- Aggregate-only workforce profile ingestion with input-side individual-data rejection (S-1)
- DSS-taxonomy skill-gap analysis via a structured lookup table (DX-Lite / DX-Standard / DX-Expert)
- Bloom's Revised Taxonomy-aligned learning objective generation per identified gap
- Vector retrieval over DSS and 職業能力開発促進法 / 厚労省 ガイドライン framework indices
- Phased curriculum outline drafting (module titles, sequencing, durations)
- Output-side individual-data leakage scan and audit logging (S-3/S-4)

## Requirements

**This template does not run standalone.** It requires:

| Requirement | Notes |
|---|---|
| **AGENTIC STAR platform** | The agent connects to the platform at start-up. Without it, start-up fails immediately (see *Behaviour without the platform* below). Deployment guides and API documentation: [AGENTIC STAR Developers](https://developers.fd.agenticstar.tm.softbank.jp/) |
| **AgentCore Framework** (`agenticstar-agentcore`) | Installed from PyPI as a dependency. |
| Python | >=3.11 |

```bash
pip install -e .
```

### Behaviour without the platform

The framework is designed to run **only** on AGENTIC STAR. There is no fallback or degraded
mode. If the platform is unreachable or the SDK version does not match, the agent raises
`PlatformRequired` during graph compile / start-up preflight rather than starting in a partially
working state. This is intentional — a half-running agent is worse than one that refuses to start.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest tests/ -v
```

Tests run without a platform connection. Running the agent itself does not.

## Project Structure

```
src/          agent implementation (nodes, services, schemas)
tests/        unit, integration and boundary tests
config/       agent configuration
docs/         design and operational documentation
```

See `docs/` for the design spec and test specification.

## Customising

1. Adjust `config/` for your own environment and policies.
2. Replace the knowledge sources and sample data with your own.
3. Review the node implementations under `src/nodes/` for domain-specific logic.
4. Re-run the test suite.

## License

MIT — see [LICENSE](LICENSE).

## Status of this repository

This template is published **as is**, by its individual author, under the MIT license. It carries
**no warranty and no support commitment**, and no organisation stands behind its behaviour or
fitness for any purpose. Issues and pull requests may or may not receive a response; that is at
the sole discretion of the repository owner.

---
