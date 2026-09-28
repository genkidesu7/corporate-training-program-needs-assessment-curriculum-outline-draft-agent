# Test Specification

## Test Strategy
- Coverage target: 80%
- Test types: Unit / Integration / Proof-of-Boundary
- Achieved coverage: 93% (see Test Execution Summary)

## Framework Compliance Tests (Mandatory)

| TC-ID | Test | Expected Result | Result |
|-------|------|----------------|--------|
| TC-01 | State contract: flat TypedDict | Type check pass, no Pydantic/dataclass | Pass — `tests/proof_of_boundary/test_state_safety.py` (state.py + domain_state.py) |
| TC-02 | SecurityViolationError fires on invalid input | Error raised | Pass — `tests/unit/test_pre_process_node.py::test_s2_rejects_individual_identifier_field` |
| TC-03 | No JWT/Credential in State | CI `gate-credential-scan`: 0 violations | Pass — `check-local.sh` credential pattern scan |
| TC-04 | InvocationContext via configurable only | Direct access raises error | Pass — no state field holds InvocationContext (PB-2/PB-5 scan) |
| TC-05 | S-4: no duplicate lifecycle events in `execute()` | `node_start`/`node_complete`/`node_error` absent from `execute()` body | Pass — `tests/proof_of_boundary/test_pb_invoke_order.py` |
| TC-06 | S-2: `_security_gate_input()` not overridden (`FunctionNode` subclass) | `TypeError` at class definition if overridden | Pass — all nodes only implement `_extra_security_gate_input()` where needed |
| TC-07 | S-3: `_security_gate_output()` not overridden (`FunctionNode` subclass) | `TypeError` at class definition if overridden | Pass — all nodes only implement `_extra_security_gate_output()` where needed |
| TC-08 | `required_trust_level` enforced | Insufficient trust → refused | Pass — `tests/integration/test_graph.py::test_outer_graph_denies_anonymous_caller` |
| TC-09 | S-2: `_extra_security_gate_input()` non-trivial when domain checks needed | Domain-specific input checks execute correctly | Pass — `PreProcessNode._extra_security_gate_input` rejects individual-identifier fields + length limit; `tests/unit/test_pre_process_node.py` |
| TC-10 | S-3: `_extra_security_gate_output()` non-trivial when domain checks needed | Domain-specific output checks execute correctly | Pass — `PostProcessNode._extra_security_gate_output` enforces disclaimer; `tests/unit/test_post_process_node.py` |
| TC-11 | S-4: at least one domain `emit_trace_event()` inside each `execute()` | Domain event emitted on every invocation path | Pass — verified by `check-security.sh` + `test_pb_invoke_order.py` |

## Proof-of-Boundary Tests (Mandatory)

| PB-ID | Boundary | Test | Expected Result | Result |
|-------|----------|------|----------------|--------|
| PB-1 | BaseNode → EventEmitter | `emit_trace_event()` fires on every invocation path | No silent failures | Pass — `test_pb_invoke_order.py` |
| PB-2 | State serialization | Post-invoke State is primitives only | No Pydantic/dataclass | Pass — `test_state_safety.py::test_state_file_safety`, `test_domain_state_file_safety` |
| PB-3 | Level 2 → External service | Real external service connection | Data retrieved | Auto-waived — v1 mock-mode-only for LLM/KB per docs/02_design.md; real client wiring deferred (`NotImplementedError` in non-mock path, verified in `src/services/*.py`) |
| PB-4 | Import isolation | No Level 0 imports | AST scan: 0 violations | Pass — `test_import_isolation.py` |
| PB-5 | Checkpoint safety | No JWT/Pydantic in checkpoint | Inspection pass | Pass — `test_state_safety.py` (covers both state files) |
| PB-6 | Invoke execution order | `__call__()`: S-1 → S-4 `node_start` → S-2 → `execute()` → S-3 → S-4 `node_complete` | Order verified | Pass — `test_pb_invoke_order.py` (all 8 concrete nodes) |
| PB-7 | HITL interrupt propagation *(conditional)* | Required only when `hitl.enabled: true` | N/A | **Auto-waived — non-HITL** (`config/agent.yaml` has no `hitl` block; v1 is fully automated, see docs/02_design.md Design Decision Record) |

## Business Logic Tests

| TC-ID | Test | Input | Expected Result | Result |
|-------|------|-------|----------------|--------|
| BL-01 | Mock-mode flag resolves under `USE_MOCK` | `USE_MOCK=true`, `STG_MOCK_MODE` unset | `mock_mode_enabled()` True | Pass — `tests/unit/test_mock_mode.py::test_mock_mode_enabled_via_use_mock` |
| BL-02 | Mock-mode flag resolves under `STG_MOCK_MODE` alias | `STG_MOCK_MODE=true`, `USE_MOCK` unset | `mock_mode_enabled()` True (deploy-stg regression) | Pass — `test_mock_mode_enabled_via_stg_mock_mode_alias` |
| BL-03 | Mock-mode flag off when neither set | both unset | `mock_mode_enabled()` False | Pass — `test_mock_mode_disabled_when_neither_set` |
| BL-04 | `NeedsDataIngestNode` parses aggregate profile | JSON workforce profile string | `workforce_profile`/`target_dss_level` populated | Pass — `tests/unit/test_domain_nodes.py::TestNeedsDataIngestNode` |
| BL-05 | `NeedsDataIngestNode` rejects individual-identifier field | `workforce_profile` with `employee_name` | `status: error` (S-1/S-5) | Pass — `test_rejects_individual_identifier_field` |
| BL-06 | `SkillGapAnalyzeNode` computes gap matrix via structured lookup | role cohorts + target DSS level | Per-cohort, per-dimension severity — not open-ended LLM judgment | Pass — `TestSkillGapAnalyzeNode::test_success_path` |
| BL-07 | `LearningObjectiveGenerateNode` succeeds in mock mode with zero secrets bound | mock mode, no `bound_secrets()` context | `status: success` (implementation_rule.md rule 2 regression) | Pass — `tests/unit/test_mock_mode_no_secrets.py` |
| BL-08 | `OutlineDraftNode` succeeds in mock mode with zero secrets bound | mock mode, no `bound_secrets()` context | `status: success` | Pass — `test_mock_mode_no_secrets.py` |
| BL-09 | `OutputValidateNode` blocks individual-data leakage | `curriculum_outline` containing `employee_name` | `status: error` (S-3 block) | Pass — `TestOutputValidateNode::test_blocks_on_individual_data_leakage` |
| BL-10 | Inner graph (`CorporateTrainingWorkflowGraph`) compiles and invokes end-to-end | aggregate workforce profile | `status: success`, full 6-node `node_history`, populated `tna_report` | Pass — `tests/integration/test_domain_workflow_graph.py` |
| BL-11 | Outer graph (`EduC2030CorporateTrainingNeedsAssessmentAgent`) compiles and invokes end-to-end | aggregate workforce profile, `VERIFIED_EXTERNAL` caller | `status: success`, disclaimer present | Pass — `tests/integration/test_graph.py::test_outer_graph_invoke_success_verified_external` |
| BL-12 | `/invoke` HTTP route succeeds over real ASGI transport (Test Rule 3 regression) | POST with Bearer auth token | `200`, `status: success` — proves async-route → `asyncio.to_thread` → sync-invoke boundary is safe | Pass — `tests/integration/test_api_server.py::test_invoke_endpoint_succeeds_over_http` |
| BL-13 | `/invoke` rejects invalid bearer token | POST with wrong token | `401` | Pass — `test_invoke_endpoint_rejects_bad_token` |
| BL-14 | `stg_invoke_evidence.py` runnable as local pytest (Test Rule 4) | stub HTTP server, all response variants | `overall: PASS`/`FAIL` per scenario, correct exit code | Pass — `scripts/test_stg_invoke_evidence.py` (12 tests) |
| BL-15 | Real `deploy-stg` repro against live server with `STG_MOCK_MODE=true` (implementation_rule.md rule 4) | `env -i` + `STG_MOCK_MODE=true` + generated `INVOKE_AUTH_TOKEN`, uvicorn subprocess | `overall: PASS`, all 7 assertions `passed: true` | Pass — verified manually, see Test Execution Summary |

## Test Execution Summary
- Execution date: 2026-07-14
- Total tests: 55 (`tests/` + `scripts/test_stg_invoke_evidence.py`)
- Pass: 53 / Fail: 0 / Skip: 2 (PB-7, auto-waived — non-HITL)
- Coverage: 93% (`src/` — target 80%)
- Local CI-gate script: all 12 gates pass (project integrity, legacy-shim deprecation, design content, import isolation, agent class composition, invoke chain, credential pattern scan, trust level declarations, category consistency, stub tests, dependency pinning, full test suite + Stage 5 STG invoke evidence)
- Real `deploy-stg` repro (implementation_rule.md §4): `env -i` + `STG_MOCK_MODE=true` + generated `INVOKE_AUTH_TOKEN` + uvicorn subprocess → `stg_invoke_evidence.py` → `overall: PASS`, all 7 assertions true
