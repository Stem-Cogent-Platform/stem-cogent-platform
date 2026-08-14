# STEM COGENT — DOCUMENT 5: AI & INTELLIGENCE ORCHESTRATION SPECIFICATION

**Document Version:** 2.0.0  
**Status:** Active Engineering Source of Truth  
**Classification:** Internal Engineering — Restricted  
**Document ID:** SC-DOC-005  
**Owner:** Intelligence Engineering Lead  
**Depends On:** SC-DOC-001 through SC-DOC-004  
**Referenced By:** SC-DOC-006, SC-DOC-010  
**Last Updated:** 2026-08-07

---

## DOCUMENT CONTROL

This document supersedes the v1.x version with the same Document ID. The v2 reconstruction preserves completed Phase 1 infrastructure work while changing product semantics before database schema implementation. If a downstream document conflicts with this document, the dependency order defined in SC-DOC-001 Section 9 applies.

---

## CANONICAL PRODUCT VOCABULARY

The following terms are normative across the Stem Cogent documentation stack. Do not create synonyms in code, schema, UX copy, or delivery tasks without updating SC-DOC-001 first.

| Term | Canonical meaning |
|---|---|
| **Company Context** | Shared, tenant-level description of the fintech: business model, products, markets, customer segments, dependencies, competitors, regulatory categories, and strategic priorities. |
| **Decision Lens** | User-level profile describing role, responsibilities, priority decision domains, and delivery preferences. One authenticated user has one active Decision Lens at MVP. |
| **Focus Area** | User-configured temporary or persistent subject requiring extra attention: entity, market, product category, initiative, competitor, regulator, or free-text topic. |
| **Signal** | A normalized external or private source event/fact captured by the ingestion pipeline. Signals are evidence, not the product output. |
| **Global Intelligence Output** | Source-grounded, tenant-neutral synthesis of a Signal and its corroborating/historical context. |
| **Decision Relevance Assessment** | Deterministic tenant/user-specific evaluation of whether a Global Intelligence Output matters, what is exposed, what stakes are present, and whether a decision is required. |
| **Decision Brief** | The core customer-facing product unit. It explains what changed, why it matters to this company/user, affected business context, stakes, decision required, owner/time window, uncertainty, and evidence. |
| **My Decision Briefing** | Primary user home view, ranked by the active user's Decision Lens and Focus Areas. |
| **Company Lens** | Shared organisation-level view of material Decision Briefs independent of one user's personal prioritisation. |
| **Wider Intelligence** | Secondary market intelligence surface containing relevant Signals/Global Intelligence Outputs that do not currently require a Decision Brief for the user. |
| **CIL** | Conversational Intelligence Layer; a grounded investigation capability over Stem Cogent evidence, Company Context, and Decision Briefs. It is not the product itself. |

---

# GOVERNING PRINCIPLE — RULES FIRST, LLM BOUNDED

MVP does **not** require custom model training. The launch intelligence stack uses deterministic rules, curated registries, embeddings, and bounded LLM synthesis. Production feedback is collected first; advanced ML is introduced only when real labels and measurable need exist.

---

# SECTION 1 — MVP INTELLIGENCE STACK

```text
SYSTEM A  Entity Registry + deterministic/fuzzy entity resolution
SYSTEM B  Rules-first Signal Taxonomy Classification
SYSTEM C  Embeddings (semantic retrieval, dedup, clustering support)
SYSTEM D  Deterministic Confidence + Urgency
SYSTEM E  Deterministic Decision Relevance Rules
SYSTEM F  Bounded LLM Formatting (Global Intelligence, Decision Brief, CIL)
SYSTEM G  Human Review + Feedback Data
```

Deferred: DistilBERT classifier training, DeBERTa risk model, sentiment model, MLflow training lifecycle, automated drift/retraining, SageMaker endpoints.

---

# SECTION 2 — ENTITY RESOLUTION

## 2.1 Dictionary-First

Entity Registry is primary. It contains fintechs, regulators, infrastructure providers, banks, products/categories, legislation, markets, and other launch entities.

Resolution order:

1. exact canonical/alias match;
2. normalized match;
3. fuzzy string match with contextual constraints;
4. optional spaCy/LLM-assisted unknown-string extraction;
5. unresolved queue for human curation.

Unknown extraction never creates an authoritative entity automatically without a curation rule/threshold.

---

# SECTION 3 — RULES-FIRST TAXONOMY CLASSIFIER

## 3.1 Why Rules First

Launch has insufficient trusted labelled production data to justify a mandatory trained classifier. Rules provide traceability and can be updated without model retraining.

## 3.2 Rule Inputs

- source type/tier;
- keyword/phrase patterns;
- entity types;
- document metadata;
- region;
- regulator/infrastructure source identity.

## 3.3 Output

`primary_domain`, `secondary_domains`, `subcategory_tags`, `classification_confidence`, `classification_method=RULE_BASED`, `taxonomy_version`, `review_flag`.

## 3.4 Future Model Gate

A trained classifier may be introduced only when:

- at least 4,000 reviewed labelled examples exist across target classes;
- class imbalance is documented;
- offline macro F1 ≥ 0.80 and improves over rules baseline;
- inference cost/latency is acceptable;
- rollback path exists.

Until then, rules remain authoritative.

---

# SECTION 4 — EMBEDDINGS

Embeddings support:

- semantic dedup;
- similar historical signal retrieval;
- CIL retrieval;
- clustering candidate generation.

The provider/model/dimension are configuration values. Business logic must not assume a permanent model name.

Input construction uses normalized title + bounded body excerpt + primary domain/entity labels after classification. Sensitive tenant-private text is embedded only through approved provider/privacy configuration and tenant isolation controls.

---

# SECTION 5 — DETERMINISTIC CONFIDENCE & URGENCY

## 5.1 Confidence Formula

```text
source_reliability        0.35
corroboration             0.25
recency                   0.15
entity_resolution_quality 0.15
classification_confidence 0.10
```

No LLM may assign/modify confidence.

## 5.2 Urgency

Urgency represents time sensitivity of the event generally. Inputs may include domain weight, confidence, corroboration, explicit deadline, incident state, and validated risk flags.

Urgency is **not** business impact. Decision Relevance handles impact per tenant/user.

---

# SECTION 6 — DECISION RELEVANCE ENGINE

## 6.1 Inputs

```python
DecisionRelevanceInput = {
    "signal": "structured Signal fields",
    "global_output": "Global Intelligence Output",
    "company_profile": "Company Context",
    "company_objects": "products/markets/dependencies/competitors/etc",
    "decision_rules": "versioned deterministic rules"
}
```

## 6.2 Rule Families

### Applicability Rules
Examples:

- regulator/category match;
- dependency/provider match;
- competitor watchlist match;
- market match;
- product/category match;
- active initiative/focus match.

### Exposure Rules
Map evidence/context to one or more:

`PRODUCT, REVENUE, COST, CUSTOMER, OPERATIONAL, REGULATORY, EXECUTION, MARKET, PARTNERSHIP`.

### Decision Trigger Rules
Examples:

```text
IF domain=REGULATORY
AND applicable_product_or_category=true
AND deadline_days <= configured_threshold
THEN decision_required=true
     decision_type=REGULATORY_PRODUCT_CHANGE
     owner_roles=[PRODUCT, COMPLIANCE_RISK]
```

```text
IF domain=INFRASTRUCTURE
AND dependency_match=true
AND incident_status in [DEGRADED, OUTAGE]
THEN decision_required=true
     decision_type=INFRASTRUCTURE_RESPONSE
     owner_roles=[COO]
```

```text
IF domain=COMPETITIVE
AND competitor_match=true
AND (focus_area_match=true OR cluster_status=ACCELERATING)
THEN decision_required=rule-configured
     decision_type=COMPETITOR_RESPONSE_REVIEW
     owner_roles=[CSO, PRODUCT]
```

Rules are illustrative; exact production rules live in `config.decision_rules` and are versioned/tested.

## 6.3 Relevance Score

Use a transparent weighted score with rule overrides. Initial MVP baseline:

```text
company_applicability      0.40
context_object_match       0.20
signal_urgency             0.15
configured_entity_match    0.10
strategic_priority_match   0.10
focus_area_presence        0.05  # tenant-level focus only if applicable
```

A hard rule may force relevance HIGH/CRITICAL for authoritative regulatory deadlines or critical configured dependency incidents.

Weights are configuration, not immutable constants.

## 6.4 User Decision Lens Priority

Personal ranking occurs after tenant assessment.

Initial factors:

- role/owner match;
- responsibility tag match;
- priority-domain match;
- personal Focus Area match;
- user's delivery threshold.

The user may override defaults. The system must never infer that a CFO cannot care about Product or that a Product user cannot care about Finance.

---

# SECTION 7 — LLM SYNTHESIS SANDBOX

## 7.1 Provider Configuration

Primary and fallback providers/models are environment/config values:

- `LLM_PRIMARY_PROVIDER`
- `LLM_PRIMARY_MODEL`
- `LLM_FALLBACK_PROVIDER`
- `LLM_FALLBACK_MODEL`

Provider changes must not alter output contracts.

## 7.2 Global Intelligence Prompt Contract

System role:

> You are a structured intelligence formatting service. Use only the provided evidence/context. Do not introduce facts, predictions, business exposure, or tenant-specific claims that are not present. Every factual claim must map to a supplied source signal.

Output JSON:

```json
{
  "summary": "string",
  "key_developments": ["string"],
  "global_implication": "string",
  "confidence_note": "string",
  "citations": [{"claim_index": 0, "source_signal_id": "uuid", "source_name": "string"}]
}
```

## 7.3 Decision Brief Formatting Prompt

Inputs include authoritative structured assessment + Company Context labels + active Decision Lens + Global Intelligence evidence.

System role:

> Format the provided Decision Relevance Assessment into concise executive language. Treat all structured relevance/exposure/owner/deadline fields as authoritative inputs. Do not add an exposure, monetary amount, deadline, product, customer segment, competitor, or recommendation that is not supplied. If quantification_status is NOT_AVAILABLE, state that the financial amount is not quantified when relevant.

Output JSON:

```json
{
  "what_changed": "string",
  "why_it_matters": "string",
  "exposure_summary": "string",
  "stakes_summary": "string",
  "decision_prompt": "string",
  "uncertainties": ["string"],
  "citations": [{"claim_text": "string", "source_signal_id": "uuid"}]
}
```

## 7.4 CIL Prompt

CIL receives only authorised retrieved context. If evidence is insufficient, it returns an explicit insufficient-data response. It may explain the rationale for a Decision Brief but cannot silently change its deterministic fields.

Supported CIL answer contract:

```json
{
  "answer_text": "string",
  "citations": [{"claim_text": "string", "source_signal_id": "uuid", "source_name": "string"}],
  "confidence_indicator": "HIGH|MODERATE|LOW|INSUFFICIENT_DATA",
  "response_grounded": true,
  "follow_up_suggestions": ["string"]
}
```

---

# SECTION 8 — CITATION & CLAIM VERIFICATION

Programmatic verification is mandatory:

1. citation IDs must be in context package;
2. entity/date/statistic claims must appear in evidence or structured context;
3. unsupported claims are removed or synthesis fails to template fallback;
4. Decision Brief claims referencing Company Context must map to stored context object IDs/labels;
5. exact financial values require `quantification_status=SUPPORTED` and evidence pointer.

---

# SECTION 9 — HUMAN INTELLIGENCE OPERATIONS

MVP review queues:

- source validation;
- low-confidence classification;
- unresolved entity curation;
- disputed Decision Relevance feedback review.

The human operations layer exists to improve ground truth and rules. It is not a requirement to manually approve every normal signal.

---

# SECTION 10 — FEEDBACK DATA FOR FUTURE ML

Collect:

- Decision Brief viewed/acknowledged;
- relevant/important feedback;
- dismissed + reason;
- escalated;
- acted on;
- CIL helpful/not-helpful;
- classification/entity corrections.

Future training must use de-identified/appropriately governed data according to SC-DOC-008 and customer agreements.

---

# SECTION 11 — DEFERRED ADVANCED ML

Not in MVP:

- fine-tuned DistilBERT taxonomy classifier;
- DeBERTa risk classifier;
- sentiment classifier;
- learned relevance ranker;
- automated decision recommendation model;
- MLflow production training/retraining requirement;
- SageMaker online endpoints;
- drift-triggered automatic retraining.

Potential post-launch order:

1. learned relevance ranking from real user feedback;
2. taxonomy classifier only if rules become a measurable bottleneck;
3. specialised risk/sentiment models only if a paying use case requires them.

---

# SECTION 12 — COST & DEGRADATION

- Cache Global Intelligence synthesis; do not regenerate per tenant.
- Reuse one tenant-level Decision Relevance Assessment across users; personalise only ranking/narrative where required.
- Batch embeddings.
- Use deterministic/template fallback on LLM failure.
- CIL quotas are plan-configured.
- LLM failure must never block storage of validated signal truth or deterministic Decision Relevance Assessment.
