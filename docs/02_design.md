# Template Design Specification

Status: completed
Date: 2026-07-14
Reviewer: [TBD]

## Position in AgentCore Architecture

- **Agent Class**: `EduC2030CorporateTrainingNeedsAssessmentAgent`
- **L1 Base**: AgentBaseGraph (outer graph, Cat 2) — inner domain workflow graph inherits `BaseGraph`
- **Three-Layer Separation**:
  - State: flat TypedDict composition (no Pydantic — msgpack incompatible)
  - Node: L1 inheritance (Template Method: `execute(self, state: dict) -> dict` override only)
  - Graph: composition (`register_nodes()` for node substitution)

## Architecture Overview

This is a **Cat 2** template: it orchestrates a fixed, six-step domain workflow
(needs assessment → skill-gap analysis → objective generation → framework
retrieval → outline drafting → output validation) to accomplish one
job-to-be-done — turning an aggregate workforce profile into a DSS-aligned
TNA report and curriculum outline. Per the Cat 2 pattern, the outer graph
keeps the standard 5-node backbone and the domain complexity is fully
encapsulated inside a `GraphNode` in the `main` slot, wrapping an inner
`domain_workflow_graph.py`.

### Outer Graph — `src/graph/graph.py`

```
START → initialize → pre_process → main → {route} → post_process → finalize → END
                                       ↓ (RETRY, max 3)
                                    pre_process
```

- `pre_process`: validates raw `user_input` is present/non-empty, rejects any
  field resembling an individual employee identifier (S-1 aggregate-only
  gate), and produces `validated_input`.
- `main`: `CorporateTrainingWorkflowGraphNode` (a `GraphNode`) — wraps the
  inner six-node domain workflow described below.
- `post_process`: formats the validated TNA report + curriculum outline into
  the final `formatted_output`, attaches the mandatory disclaimer.

### Inner Graph — `src/graph/domain_workflow_graph.py`

Inherits `BaseGraph` (fully custom topology, no pre_process/main/post_process
slots — those are outer-graph concerns).

```
START → needs_data_ingest → skill_gap_analyze → learning_objective_generate
      → curriculum_framework_retrieve → outline_draft → output_validate → END
```

Linear topology — no conditional branching required; `route()` is
implemented per the `BaseGraph` ABC contract but never invoked
(`add_conditional_edges()` is not used).

### Node Configuration

| Node | Responsibility | Input State | Output State | Inherits/Overrides |
|------|---------------|-------------|--------------|-------------------|
| initialize | Sets schema_version, session_id, trust_level | — | `schema_version`, `session_id` | InitializeNode (default) |
| pre_process | Validates aggregate-only workforce profile input; rejects individual-employee-identifier fields | `user_input`, `input_context` | `validated_input`, `enriched_context` | PreProcessNode |
| main | Invokes inner domain workflow graph; merges TNA + outline result | `validated_input` | `result`, `status` | CorporateTrainingWorkflowGraphNode (GraphNode) |
| post_process | Formats TNA report + curriculum outline, attaches disclaimer | `result` | `formatted_output` | PostProcessNode |
| finalize | Builds response_metadata, total_time_ms | — | `response_metadata` | FinalizeNode (default) |

#### Inner workflow nodes (`src/graph/domain_workflow_graph.py` + `src/nodes/domain/*.py`)

| Node | Responsibility | Input State | Output State |
|------|---------------|-------------|--------------|
| NeedsDataIngest | Parses/validates the aggregate workforce profile (≤3000 chars) against the aggregate-only schema; rejects any individual-identifier field before it enters state | `validated_input`/`user_input` | `workforce_profile`, `target_dss_level` |
| SkillGapAnalyze | Maps each role cohort's current skill level to DSS competency dimensions (DX-Lite/DX-Standard/DX-Expert) via a structured lookup table; computes per-dimension gap severity | `workforce_profile`, `target_dss_level` | `skill_gap_matrix` |
| LearningObjectiveGenerate | LLM call constrained by retrieved Bloom's Revised Taxonomy templates; one objective set generated per gap dimension, tagged to cognitive level | `skill_gap_matrix` | `learning_objectives` |
| CurriculumFrameworkRetrieve | Vector similarity search over the DSS framework index and the 職業能力開発促進法/厚労省ガイドライン index, filtered to target DSS level and gap dimensions | `skill_gap_matrix`, `target_dss_level` | `retrieved_framework_passages` |
| OutlineDraft | LLM drafts a multi-phase curriculum outline (module titles, sequencing, durations), grounded in retrieved passages and learning objectives | `learning_objectives`, `retrieved_framework_passages` | `curriculum_outline` |
| OutputValidate | Runs `_extra_security_gate_output()` to scan the drafted output for individual-level data before returning; blocks/re-drafts on leakage; writes the S-4 audit log entry | `curriculum_outline` | `tna_report`, `status` |

### Data Flow

```
START → initialize → pre_process → main → {route} → post_process → finalize → END
                                            ↓ (retry)
                                          pre_process

  main = CorporateTrainingWorkflowGraphNode.execute():
    inner_graph.invoke(validated_input)
      START → needs_data_ingest → skill_gap_analyze → learning_objective_generate
            → curriculum_framework_retrieve → outline_draft → output_validate → END
    merge_output(state, sub_result) → {"result": ..., "status": ...}
```

**⚠️ Inner graph starts with fresh state.** `CorporateTrainingWorkflowGraphNode.extract_input()`
returns `validated_input` (falling back to `user_input`), but `BaseGraph.invoke()` builds a
brand-new inner `initial_state` containing only `user_input`. Every inner node that reads the
profile text (`NeedsDataIngest` and any node after it that re-reads raw text) must therefore
read via `state.get("validated_input", state.get("user_input", ""))`, never `validated_input`
alone.

### State Definition

**Outer state** (`src/schemas/state.py`, extends `AgentState`):

| Field | Type | Purpose | Required |
|-------|------|---------|----------|
| `result` | `dict` | Merged TNA report + curriculum outline from inner graph | No (set by `main`) |
| `formatted_output` | `dict` | Final formatted output incl. disclaimer | No (set by `post_process`) |

**Inner state** (`src/schemas/domain_state.py`, extends `AgentState`):

| Field | Type | Purpose | Required |
|-------|------|---------|----------|
| `workforce_profile` | `dict` | Parsed aggregate role-cohort profile (role types, skill levels, business goals) | No (set by NeedsDataIngest) |
| `target_dss_level` | `str` | Target DSS level: `DX-Lite` \| `DX-Standard` \| `DX-Expert` | No (set by NeedsDataIngest) |
| `skill_gap_matrix` | `dict` | Per-role-cohort, per-DSS-dimension gap severity | No (set by SkillGapAnalyze) |
| `learning_objectives` | `list[dict]` | Bloom's-aligned objectives per gap, tagged to cognitive level | No (set by LearningObjectiveGenerate) |
| `retrieved_framework_passages` | `list[dict]` | DSS + 職業能力開発促進法 framework passages relevant to gaps | No (set by CurriculumFrameworkRetrieve) |
| `curriculum_outline` | `dict` | Draft phased curriculum outline (modules, sequencing, durations) | No (set by OutlineDraft) |
| `tna_report` | `dict` | Final validated TNA report + curriculum outline | No (set by OutputValidate) |

**State Constraints (mandatory):**
- Flat TypedDict only (primitives + JSON-serializable types)
- No JWT, API keys, credentials in State (checkpoint DB leakage)
- InvocationContext via `config["configurable"]` only (not in State)
- No Pydantic models, dataclass, arbitrary Python objects (msgpack incompatible)
- No individual employee identifiers/names/performance data in any state field —
  aggregate role-cohort data only (S-5)

## Framework Utilization

### Shared Components Used
- [x] InvocationContext (correlation_id, session_id, permissions, credential handle)
- [x] ConnectionPolicy (retry/timeout strategy)
- [x] SecurityViolationError
- [x] S-2: `_extra_security_gate_input()` — domain-specific input check hook
      (runs after the default PII scan; rejects any field resembling an
      individual employee identifier in the workforce profile; input size
      limit ≤3000 chars)
- [x] S-3: `_extra_security_gate_output()` — domain-specific output check hook
      (runs after the default credential scan; scans the drafted TNA report
      and curriculum outline for individual-level employee data before
      release; blocks/re-drafts on match)
- [x] S-4: `emit_trace_event()` — at least one domain-specific event inside each `execute()`
      (mandatory; audit log entry per invocation: input hash, output type,
      timestamp — emitted from `OutputValidate`; do NOT emit `node_start` /
      `node_complete` / `node_error` — `BaseNode.__call__()` emits these
      automatically)

> **S-2/S-3 gate behaviour by node type (ADR-017):**
> - `FunctionNode` subclass → framework `@final` gate always runs automatically;
>   extend via `_extra_security_gate_input()` / `_extra_security_gate_output()` only
> - `GraphNode` / `RemoteAgentNode` → deliberate no-op (upstream or remote node's gate already applied)
> - Custom `BaseNode` subclass → must implement `_security_gate_input()` and
>   `_security_gate_output()` directly (`@abstractmethod` — omission raises `TypeError` at instantiation)

### Composition Pattern

- **Pattern**: GraphNode (subgraph) — `CorporateTrainingWorkflowGraphNode` in the outer `main` slot
- **Composition target**: `src/graph/domain_workflow_graph.py` — `CorporateTrainingWorkflowGraph` (inherits `BaseGraph`, fully custom 6-node linear topology)
- **Error propagation strategy**: `propagate` (default — inner errors re-raise as `SubgraphError`; a mis-scored DSS gap or a failed framework retrieval should fail the invocation, not silently degrade into an incomplete curriculum). `propagate_hitl: False` — no HITL is used in v1 (fully automated draft; human validation happens downstream by the HR manager, outside the agent boundary).

## Import Isolation Confirmation
- [x] Template does not import agenticstar-platform SDK (Level 0)
- [x] Import targets: framework/ and shared/ only (no agents/base/ required)

## Services

- **LLMService** (`src/services/llm_service.py`) — used by `LearningObjectiveGenerate`
  and `OutlineDraft`; credential resolved via `InvocationContext.credential_handle`,
  never a raw key.
- **KnowledgeBaseService** (`src/services/kb_service.py`) — vector similarity search
  over three indices: METI デジタルスキル標準 (DSS) framework, 職業能力開発促進法 +
  厚労省 キャリア形成・リスキリング ガイドライン, and Bloom's Revised Taxonomy
  templates. `kb_path: ./kb/` is the only required config for the zero-config
  demo path.
- **DssGapAnalysisService** (`src/services/dss_gap_analysis_service.py`) — the
  structured DSS-to-role-cohort lookup table and gap-severity scoring logic used
  by `SkillGapAnalyze`; deliberately not open-ended LLM judgment, so gap scoring
  stays auditable. Both service and lookup table use mock data (`stub_*` functions
  in `mock_data.py`) when mock mode is on.

## Design Decision Record

| Decision | Option A | Option B | Chosen | Rationale |
|----------|----------|----------|--------|-----------|
| L1 base type | AgentBaseGraph | AutonomousBaseGraph | AgentBaseGraph (outer) | Fixed multi-step workflow for one job-to-be-done — no autonomous reasoning loop needed; matches Cat 2 judgment in `docs/01_proposal.md`. |
| Composition pattern | Standalone (single graph) | GraphNode (subgraph) | GraphNode | Six domain steps with distinct responsibilities (ingest, gap analysis, objective gen, retrieval, drafting, validation) belong in an inner workflow graph per the Cat 2 pattern, keeping the outer 5-node backbone untouched. |
| Inner graph base | BaseGraph | AgentBaseGraph | BaseGraph | The inner workflow is a fully custom linear 6-node topology with no pre_process/main/post_process slots — `BaseGraph` fits without forcing an unused 5-node backbone inside the backbone. |
| SkillGapAnalyze logic | LLM judgment | Structured lookup table | Structured lookup table | Per `docs/engineer_proposal.md` §4 and §11 risk #1 — auditability and DSS-framework-validated accuracy are required; open-ended LLM scoring would be unauditable and is the proposal's identified high risk if under-modeled. |
| HITL | Enabled | Disabled | Disabled | v1 is a fully automated first-draft generator; human validation (HR manager, qualified training professional) happens downstream of the agent boundary per the proposal's disclaimer requirement, not via an in-graph interrupt. |
| Error strategy (GraphNode) | propagate | handle | propagate | A failed gap analysis or framework retrieval should fail fast rather than silently produce an incomplete/inaccurate curriculum outline that an HR manager could mistakenly treat as reliable. |
