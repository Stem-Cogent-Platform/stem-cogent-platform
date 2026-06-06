# STEM COGENT — DOCUMENT 5: AI/ML ORCHESTRATION SPECIFICATION (v2.0)

**Document Version:** 1.0.0
**Status:** Production Draft
**Classification:** Internal Engineering — Restricted
**Owner:** Intelligence Engineering / ML Platform
**Document ID:** SC-DOC-005
**Cloud Provider:** AWS
**Depends On:** SC-DOC-001, SC-DOC-002, SC-DOC-003, SC-DOC-004
**Referenced By:** SC-DOC-006 (Backend Services), SC-DOC-009 (DevOps)
**Last Updated:** 2026
---

## DOCUMENT CONTROL

| Field | Value |
|---|---|
| Document ID | SC-DOC-005 |
| Document Type | AI/ML Orchestration Specification |
| Approvers | Principal Architect, ML Engineering Lead, Intelligence Engineering Lead |

---

## GOVERNING PRINCIPLE — THE LLM BOUNDARY RULE

**This rule governs the entire document and every model decision within it. It is not a guideline. It is a hard architectural constraint.**


**Version 1.0 applies the following principles:**

1. **Rules beat models before you have labels.** A deterministic rule engine with a well-curated entity registry and signal taxonomy produces 80–90% of the value of a trained classifier — without annotation cost, training infrastructure, or model drift.

2. **Training data is the real bottleneck, not infrastructure.** You cannot build a risk classifier, relevance model, or sentiment model without thousands of human-labeled examples. That labeling work does not happen automatically. It requires a Human Intelligence Operations function that must be built before models that depend on it.

3. **Four ML systems at launch. Not ten.** The launch stack is: spaCy (extraction) + DistilBERT (taxonomy classification) + OpenAI Embeddings (semantic retrieval) + GPT-4o (bounded synthesis). Everything else is deferred until customer feedback and training data justify building it.

4. **The LLM Boundary Rule is unchanged and absolute.** LLMs do not define truth, assign authoritative confidence, determine operational importance, or make classification decisions. This principle survives every revision.

---

## GOVERNING PRINCIPLE — THE LLM BOUNDARY RULE

> LLMs in Stem Cogent do not define truth, assign authoritative confidence scores, determine operational importance, or make classification decisions. LLMs are bounded synthesis and formatting tools that receive fully-assembled, deterministically-validated intelligence context and produce readable human language from it.

**Authoritative operations (deterministic only — no LLM):**
- Confidence score computation (weighted formula)
- Urgency score computation (weighted formula)
- Signal domain classification (rule engine + DistilBERT)
- Recommendation triggering (rule engine)
- Alert threshold evaluation (rule engine)
- Deduplication decisions (hash + vector similarity)
- Entity resolution decisions (registry lookup + fuzzy match)
- Risk detection (rule engine + taxonomy tags + source tier)
- Relevance filtering (source tier + entity presence + region match)

**LLM-permitted operations (synthesis/formatting only):**
- Translating non-English signal text to English
- Extracting raw entity mention strings from unstructured text (as strings — labeling done by spaCy/registry)
- Generating human-readable summaries from pre-assembled context packages
- Formatting recommendation wording from rule-engine outputs
- Synthesizing grounded CIL query responses from retrieved, validated context

---

## TABLE OF CONTENTS

1. Launch ML Architecture — The Four-System Stack
2. System 1 — Named Entity Recognition (spaCy + Entity Registry)
3. System 2 — Signal Taxonomy Classifier (DistilBERT)
4. System 3 — Embedding Pipeline (OpenAI text-embedding-3-small)
5. System 4 — LLM Synthesis Sandbox (GPT-4o)
6. Deterministic Systems (Rule-Based — No ML)
   - 6.1 Relevance Filter
   - 6.2 Risk Detection Engine
   - 6.3 Knowledge Graph Builder
   - 6.4 Confidence Scoring Engine
   - 6.5 Urgency Scoring Engine
   - 6.6 Recommendation Engine
7. Human Intelligence Operations Layer
   - 7.1 Signal Review Queue
   - 7.2 Taxonomy Review Queue
   - 7.3 Source Validation Queue
   - 7.4 Entity Curation Queue
   - 7.5 Labeling Platform
   - 7.6 Human Review Workflows
8. MLflow & Model Lifecycle (Scoped to Launch Stack)
9. Training Data Strategy
10. Model Serving Architecture (AWS)
11. Cost Monitoring & Mitigation
12. Phase-Gated ML Expansion Roadmap
13. Failure Modes & Degradation Strategy

---

---

# SECTION 1 — LAUNCH ML ARCHITECTURE: THE FOUR-SYSTEM STACK

---

## 1.1 What Is Built at Launch

```
INPUT: Raw unstructured text / documents / API payloads
              |
              v
+--------------------------------+
|  SYSTEM 1: EXTRACTION          |
|  spaCy NER                     |
|  + Entity Registry Lookup      |  ← Dictionary-first, model-assisted
+--------------------------------+
              |
              v  Entity mention strings + resolved labels
+--------------------------------+
|  SYSTEM 2: CLASSIFICATION      |
|  DistilBERT (taxonomy)         |  ← ML classification, hybrid with rules
|  + Rule-Based Classifier       |
+--------------------------------+
              |
              v  Domain labels + scores
+--------------------------------+
|  SYSTEM 3: EMBEDDINGS          |
|  OpenAI text-embedding-3-small |  ← Semantic similarity, dedup, clustering
+--------------------------------+
              |
              v  Cluster assignments + similarity scores
+--------------------------------+
|  SYSTEM 4: LLM SYNTHESIS       |  ← SANDBOXED. Context-in, formatted text out.
|  OpenAI GPT-4o                 |
|  + Anthropic Claude (fallback) |
+--------------------------------+
              |
              v  Human-readable intelligence output

EVERYTHING ELSE AT LAUNCH: DETERMINISTIC RULE ENGINES
- Relevance Filter         → Source tier + entity presence + region match
- Risk Detection           → Keyword rules + taxonomy tags + source tier
- Confidence Scoring       → Weighted deterministic formula
- Urgency Scoring          → Weighted deterministic formula
- Recommendation Engine    → Rule evaluation against signal metadata
- Knowledge Graph Builder  → Pattern extraction from NER output
```

## 1.2 What Is Explicitly Deferred

The following systems from v1.0 are **removed from the launch scope** and deferred to Phase 2 or Phase 3:

| Deferred System | Reason for Deferral | When to Build |
|---|---|---|
| `sc-rel-extract-v{n}` (BERT relationship extraction) | Requires expensive relationship-labeled training corpus (thousands of examples). High annotation cost, complex maintenance. Deterministic KG builder covers 80% of value. | Phase 3 — after revenue and labeled data volume |
| `sc-risk-v{n}` (DeBERTa risk classifier) | Risk signals adequately detected by keyword rules + taxonomy tags + source tier combination at launch scale. No training data exists yet. | Phase 2 — after human review queues generate labeled examples |
| `sc-sentiment-v{n}` (DistilBERT consumer sentiment) | Stem Cogent is decision intelligence, not social listening. Consumer sentiment is not a core V1 value driver. | Phase 3 — after consumer signal domain proves demand |
| `sc-relevance-v{n}` (XGBoost relevance scorer) | Source tier + entity presence + region match provides sufficient relevance filtering without a model. Training data requires labeled irrelevance examples. | Phase 2 — after human review generates sufficient negative examples |
| MLflow full training pipeline | No retraining needed at launch. DistilBERT fine-tuning is a Phase 1 end task, not continuous. | Phase 2 |
| SageMaker endpoints | ECS Fargate sufficient at launch signal volumes. | Phase 3 |
| Automated model drift detection | No baseline established yet. Drift detection requires production history. | Phase 2 |

---

---

# SECTION 2 — SYSTEM 1: NAMED ENTITY RECOGNITION (spaCy + ENTITY REGISTRY)

---

## 2.1 Strategy: Dictionary-First, Model-Assisted

The most important architectural decision in the extraction layer is this: **use the Entity Registry as the primary extraction mechanism, not the NER model.**

The Entity Registry is a curated PostgreSQL database of every company, regulator, infrastructure provider, legislation, and financial instrument relevant to the Nigerian/African fintech market. This registry provides near-perfect recall on known entities at zero training cost.

The spaCy model supplements the registry for unknown entity mentions — organizations, people, and products that have not yet been added to the registry.

**This is not a limitation. It is a deliberate architectural choice.** The registry will cover 85–90% of entity mentions in Nigerian fintech signals. The remaining 10–15% of unknown entities flow into the Entity Curation Queue for human review.

## 2.2 Entity Registry (PostgreSQL)

The Entity Registry is seeded at launch with the following minimum coverage:

**Regulatory Bodies (complete at launch):**
```
Central Bank of Nigeria (CBN), Securities & Exchange Commission Nigeria (SEC),
National Data Protection Commission (NDPC), NIBSS (Nigeria Inter-Bank Settlement System),
Financial Reporting Council of Nigeria (FRCN), Federal Competition and Consumer
Protection Commission (FCCPC), National Insurance Commission (NAICOM),
Corporate Affairs Commission (CAC), National Communications Commission (NCC),
Federal Inland Revenue Service (FIRS), Nigerian Deposit Insurance Corporation (NDIC)
```

**Major Fintech Companies (complete at launch):**
```
Flutterwave, Paystack, Moniepoint, OPay, Kuda Bank, PalmPay, TeamApt,
Wave (formerly Sendwave), Chipper Cash, Carbon, FairMoney, Branch International,
Renmoney, Cowrywise, Piggyvest, Bamboo, Risevest, Bankly, Paga, Interswitch,
Quickteller, eTranzact, SystemSpecs (Remita), Unified Payments
```

**Banks (top-tier, complete at launch):**
```
Access Bank, Zenith Bank, GTBank (Guaranty Trust), First Bank of Nigeria,
United Bank for Africa (UBA), Ecobank Nigeria, Fidelity Bank, Sterling Bank,
Stanbic IBTC, Union Bank, Wema Bank, Polaris Bank
```

**Infrastructure Providers:**
```
NIBSS, Interswitch, eTranzact, Nigerian Communications Commission (NCC),
MTN Nigeria, Airtel Nigeria, Glo Mobile, 9mobile, Verve International,
MasterCard Nigeria, Visa Nigeria, UnionPay Nigeria
```

**Legislation & Directives:**
```
Finance Act (2020, 2021, 2022, 2023), CBN Act, BOFIA 2020,
NDPC Act 2023, Investment and Securities Act, CAMA 2020,
Nigerian Startup Act 2022, Federal Competition and Consumer Protection Act
```

### Entity Registry Schema (key fields for extraction)

```python
ENTITY_REGISTRY_CACHE_STRUCTURE = {
    # Loaded into Redis at service startup; refreshed every 30 minutes
    # Key: normalized_string → entity_record

    "central bank of nigeria": {
        "entity_id": "uuid-cbn",
        "canonical_name": "Central Bank of Nigeria",
        "entity_type": "REGULATOR_NG",
        "aliases": ["CBN", "Central Bank", "apex bank", "the bank"]
    },
    "cbn": {
        "entity_id": "uuid-cbn",
        "canonical_name": "Central Bank of Nigeria",
        "entity_type": "REGULATOR_NG",
        "aliases": ["CBN", "Central Bank Nigeria"]
    },
    "flutterwave": {
        "entity_id": "uuid-flw",
        "canonical_name": "Flutterwave",
        "entity_type": "FINTECH_CO",
        "aliases": ["FLW", "Flutterwave Inc", "Flutterwave Technology"]
    }
    # ... all entities loaded at startup
}
```

## 2.3 Extraction Pipeline (Two-Stage)

```python
# nlp/extraction/ner_pipeline.py

import spacy
from functools import lru_cache

class EntityExtractionPipeline:
    """
    Two-stage entity extraction:
    Stage 1: Entity Registry dictionary lookup (primary, high precision)
    Stage 2: spaCy NER for unknown entities (supplementary)

    No LLM in this class. LLM supplement is only triggered for
    USER_UPLOAD signal types where spaCy coverage is low.
    """

    def __init__(self, registry_cache: dict, nlp_model):
        self.registry = registry_cache     # Loaded from Redis/PostgreSQL
        self.nlp = nlp_model               # en_core_web_lg

    def extract(self, title: str, body_text: str,
                signal_type: str) -> ExtractionResult:
        full_text = f"{title}\n\n{body_text[:4000]}"

        # Stage 1: Registry lookup (O(n) pass over normalized token windows)
        registry_matches = self._registry_lookup(full_text)

        # Stage 2: spaCy NER for ORG, GPE, PERSON, LAW entities
        # (catches entities NOT in registry)
        spacy_doc = self.nlp(full_text)
        spacy_entities = [
            {
                "text": ent.text,
                "label": self._map_spacy_label(ent.label_),
                "confidence": None,   # spaCy doesn't expose token-level scores
                "extraction_method": "SPACY"
            }
            for ent in spacy_doc.ents
            if ent.label_ in {"ORG", "GPE", "PERSON", "LAW", "PRODUCT", "FAC"}
            and ent.text not in {m["text"] for m in registry_matches}
        ]

        # Combine: registry matches take precedence for any overlapping text
        all_entities = registry_matches + spacy_entities

        # Route unresolved spaCy entities to Entity Curation Queue
        unresolved = [e for e in spacy_entities if e["resolution_confidence"] is None]

        return ExtractionResult(
            resolved_entities=registry_matches,
            unresolved_mentions=[e["text"] for e in unresolved],
            total_found=len(all_entities),
            registry_coverage=len(registry_matches) / max(len(all_entities), 1)
        )

    def _registry_lookup(self, text: str) -> list[dict]:
        """
        Sliding window lookup against normalized entity registry.
        Window sizes: 1, 2, 3, 4 tokens (catches abbreviations through full names).
        """
        normalized_text = text.lower()
        matches = []
        already_matched_spans = set()

        # Sort by length DESC so longest match wins (e.g., "CBN MPC" before "CBN")
        sorted_entries = sorted(
            self.registry.items(),
            key=lambda x: len(x[0]),
            reverse=True
        )

        for lookup_key, entity_record in sorted_entries:
            pos = normalized_text.find(lookup_key)
            while pos != -1:
                span = (pos, pos + len(lookup_key))
                # Skip if this span overlaps a longer already-matched span
                if not any(s[0] <= span[0] and s[1] >= span[1]
                           for s in already_matched_spans):
                    matches.append({
                        "text": text[pos:pos + len(lookup_key)],  # original case
                        "entity_id": entity_record["entity_id"],
                        "canonical_name": entity_record["canonical_name"],
                        "label": entity_record["entity_type"],
                        "resolution_confidence": 1.0,
                        "resolution_method": "REGISTRY_EXACT",
                        "extraction_method": "REGISTRY"
                    })
                    already_matched_spans.add(span)
                pos = normalized_text.find(lookup_key, pos + 1)

        return matches

    def _map_spacy_label(self, spacy_label: str) -> str:
        return {
            "ORG": "COMPANY",
            "GPE": "GEOGRAPHIC_REGION",
            "PERSON": "PERSON",
            "LAW": "LEGISLATION",
            "PRODUCT": "PRODUCT",
            "FAC": "INFRASTRUCTURE_PROVIDER"
        }.get(spacy_label, "UNKNOWN")
```

## 2.4 LLM Entity Supplement (Scoped Use)

The LLM entity supplement is only triggered for `USER_UPLOAD` signal types (enterprise documents) where body length > 2,000 words and registry coverage < 40%.

```python
async def llm_entity_supplement(title: str, body_text: str) -> list[str]:
    """
    Returns RAW STRINGS ONLY.
    spaCy labels the returned strings — the LLM does NOT label or classify them.
    Trigger: USER_UPLOAD signal type + low registry coverage only.
    """
    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an entity string extraction tool. "
                    "Output only a JSON array of strings. "
                    "Each string is an entity mention exactly as it appears. "
                    "No labels, no classifications, no scores. Nothing else."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Extract all named organizations, regulators, people, "
                    f"products, and locations from this text.\n\n"
                    f"Title: {title}\n\nText: {body_text[:2000]}"
                )
            }
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
        max_tokens=300,
        timeout=8
    )
    raw_strings = json.loads(response.choices[0].message.content)
    return raw_strings  # caller passes through spaCy for labeling
```

## 2.5 NER Fine-Tuning (Deferred)

spaCy NER fine-tuning on a Stem Cogent domain corpus is **deferred to Phase 2**. The registry-first approach provides sufficient entity coverage at launch without annotation cost.

Fine-tuning is scheduled when:
- Human review queues have generated 2,000+ reviewed entity correction examples
- Registry coverage drops below 75% on a rolling 30-day sample audit
- Phase 2 milestone reached and labeling platform is operational

---

---

# SECTION 3 — SYSTEM 2: SIGNAL TAXONOMY CLASSIFIER (DistilBERT)

---

## 3.1 Architecture

**Model:** `distilbert-base-uncased` fine-tuned for 20-class signal domain classification
**Task:** Multi-label classification — primary domain + up to 3 secondary domains
**Input:** `[CLS] {title} [SEP] {body_text[:512]} [SEP]`
**Output:** Softmax probability distribution over 20 domain classes
**Inference target:** < 100ms P95 on c5.xlarge ECS task (CPU-only)

**Why DistilBERT at launch:**
- 40% fewer parameters than BERT-base; 60% faster inference
- Retains 97% of BERT classification performance on domain tasks
- Fine-tunable on a relatively small labeled corpus (500+ examples per class)
- Runs on CPU — no GPU required at launch signal volumes (< 50K signals/day)
- Well-documented; community support; stable API

## 3.2 Hybrid Classification System

The classifier always runs in combination with a rule-based classifier. The rule-based classifier runs first and is always cheaper.

```python
# intelligence/classification/hybrid_classifier.py

class HybridTaxonomyClassifier:
    """
    Rule-based classifier runs first (~2ms).
    If confidence >= 0.88: return rule result, skip ML model call.
    If confidence < 0.88: run ML classifier (~35ms) and blend.
    This reduces ML inference calls by ~40% at launch signal volumes.
    """

    RULE_SHORTCUT_THRESHOLD = 0.88  # High-confidence rules skip ML entirely

    def classify(self, title: str, body_text: str,
                 entity_types: list[str],
                 source_type: str,
                 source_tier: int) -> ClassificationResult:

        # Step 1: Rule-based classification
        rule_result = self.rule_classifier.classify(
            title, body_text, entity_types, source_type, source_tier
        )

        # Fast path: high-confidence rule result skips ML
        if (rule_result is not None and
                rule_result.confidence >= self.RULE_SHORTCUT_THRESHOLD):
            return ClassificationResult(
                primary_domain=rule_result.label,
                secondary_domains=rule_result.secondary_domains,
                confidence=rule_result.confidence,
                method="RULE_ONLY_HIGH_CONFIDENCE",
                review_flag=False
            )

        # Step 2: ML classifier
        ml_result = self.ml_classifier.classify(title, body_text)

        # Step 3: Hybrid resolution
        return self._resolve(rule_result, ml_result)

    def _resolve(self, rule_result, ml_result) -> ClassificationResult:
        if rule_result is None:
            return ClassificationResult(
                primary_domain=ml_result.label,
                confidence=ml_result.confidence,
                method="ML_ONLY",
                review_flag=(ml_result.confidence < 0.75)
            )

        if rule_result.label == ml_result.label:
            # Agreement: blend with slight corroboration boost
            blended = min(1.0, (rule_result.confidence * 0.45 +
                                ml_result.confidence * 0.55) * 1.03)
            return ClassificationResult(
                primary_domain=rule_result.label,
                confidence=blended,
                method="HYBRID_AGREEMENT",
                review_flag=(blended < 0.70)
            )

        # Disagreement: higher confidence wins, penalty applied, flagged
        winner = (rule_result if rule_result.confidence >= ml_result.confidence
                  else ml_result)
        return ClassificationResult(
            primary_domain=winner.label,
            confidence=winner.confidence * 0.90,  # disagreement penalty
            method="HYBRID_CONFLICT",
            review_flag=True,
            route_to_review=(max(rule_result.confidence,
                                 ml_result.confidence) < 0.75)
        )
```

## 3.3 Rule-Based Classifier

The rule-based classifier uses keyword patterns, entity type signals, and source metadata. Rules are stored in `config.recommendation_rules` (database-driven, hot-reloadable — not hardcoded).

```python
# Sample rule definitions (stored in PostgreSQL, loaded into Redis cache)

CLASSIFICATION_RULES = [
    {
        "rule_id": "RULE-001",
        "priority": 100,
        "conditions": {
            "entity_types_any": ["REGULATOR_NG"],
            "source_tier_max": 2,
            "keywords_any": ["circular", "directive", "regulation", "compliance",
                             "directive", "notice", "guidelines", "framework",
                             "policy", "requirement", "mandate", "restriction"]
        },
        "output": {
            "primary_domain": "REGULATORY",
            "secondary_domains": ["COMPLIANCE"],
            "confidence": 0.94
        }
    },
    {
        "rule_id": "RULE-002",
        "priority": 90,
        "conditions": {
            "entity_types_any": ["FINTECH_CO"],
            "keywords_any": ["funding", "series", "raise", "investment",
                             "valuation", "seed round", "pre-seed", "venture"]
        },
        "output": {
            "primary_domain": "CAPITAL_FUNDING",
            "secondary_domains": ["COMPETITIVE"],
            "confidence": 0.91
        }
    },
    {
        "rule_id": "RULE-003",
        "priority": 95,
        "conditions": {
            "entity_types_any": ["FINANCIAL_INFRA"],
            "keywords_any": ["downtime", "outage", "disruption", "failure",
                             "unavailable", "degraded", "incident", "maintenance"]
        },
        "output": {
            "primary_domain": "INFRASTRUCTURE",
            "secondary_domains": ["OPERATIONAL"],
            "confidence": 0.93
        }
    },
    {
        "rule_id": "RULE-004",
        "priority": 85,
        "conditions": {
            "source_type_any": ["RSS_FEED", "API"],
            "keywords_all": ["expand", "launch"],
            "keywords_any": ["market", "country", "region", "africa",
                             "ghana", "kenya", "south africa", "egypt"]
        },
        "output": {
            "primary_domain": "MARKET_EXPANSION",
            "secondary_domains": ["COMPETITIVE"],
            "confidence": 0.88
        }
    }
    # ... 40+ rules at launch, growing via human review feedback
]
```

## 3.4 Initial Training Data Strategy

**The single most important constraint in the entire ML system: you cannot train the classifier without labeled examples.**

**Phase 1 training data approach (launch to first 500 signals per class):**

```python
INITIAL_LABELING_STRATEGY = {
    "method_1_seed_labeling": {
        "description": (
            "Intelligence Operations team manually labels 500 signals per domain "
            "from the first 2 weeks of pipeline operation. "
            "This is the minimum viable training corpus."
        ),
        "time_estimate": "3-4 weeks of part-time labeling",
        "tool": "Custom labeling UI (see Section 7.5)",
        "target": "500 examples per class × 8 priority domains = 4,000 labeled signals"
    },
    "method_2_rule_bootstrapping": {
        "description": (
            "High-confidence rule classifications (confidence >= 0.92) are "
            "auto-labeled as training examples. "
            "Auto-labeled examples are spot-checked at 10% sample rate before use."
        ),
        "acceptance_threshold": 0.92,
        "spot_check_rate": 0.10,
        "estimated_daily_yield": "200-400 auto-labeled examples at launch signal volume"
    },
    "method_3_synthetic_augmentation": {
        "description": (
            "LLM-generated synthetic signal examples for rare classes "
            "(< 50 real examples). "
            "All synthetic examples reviewed by Intelligence Operations before use. "
            "Capped at 20% of any class."
        ),
        "permitted_domains": [
            "FRAUD_RISK",          # rare at launch
            "CROSS_BORDER",        # rare at launch
            "BEHAVIORAL"           # rare at launch
        ],
        "human_review_required": True,
        "max_synthetic_ratio": 0.20
    }
}
```

## 3.5 Classifier Evaluation (Weekly)

```python
EVALUATION_SCHEDULE = {
    "frequency": "weekly",
    "sample_size": 200,
    "sample_source": (
        "pipeline.signals WHERE review_flag = TRUE AND reviewed = TRUE "
        "ORDER BY reviewed_at DESC LIMIT 200"
    ),
    "metrics": {
        "f1_macro_threshold": 0.82,        # minimum to keep current model in production
        "f1_per_domain_minimum": {
            "REGULATORY": 0.88,            # highest bar — business-critical domain
            "INFRASTRUCTURE": 0.85,
            "DEFAULT": 0.78
        },
        "false_positive_rate_max": 0.12
    },
    "action_if_below_threshold": "alert ml_team slack channel; schedule retraining sprint"
}
```

---

---

# SECTION 4 — SYSTEM 3: EMBEDDING PIPELINE (OpenAI text-embedding-3-small)

---

## 4.1 Model Selection

**Model:** `text-embedding-3-small` (OpenAI)
**Dimensions:** 1536
**Cost:** ~$0.00002 per 1K tokens (~$0.000008 per average signal)
**Deployment:** API call from ECS worker via NAT Gateway
**Fallback:** `sentence-transformers/all-MiniLM-L6-v2` (local, 384-d, ECS Fargate)

Embeddings serve three functions in the pipeline:
1. **Semantic deduplication** — detect near-duplicate signals from different sources
2. **Signal clustering** — group related signals into thematic intelligence clusters
3. **CIL retrieval** — find semantically relevant signals for query context assembly

## 4.2 Input Construction

```python
def build_embedding_input(signal: NormalizedSignal) -> str:
    """
    Constructs enriched embedding input.
    Emphasizes semantic content: title, taxonomy tags, primary entities, body excerpt.
    Taxonomy tags and entity names act as semantic anchors that improve
    clustering quality significantly over raw body text alone.
    """
    parts = []

    if signal.title:
        parts.append(f"TITLE: {signal.title}")

    # Taxonomy tags provide explicit domain anchoring
    if signal.subcategory_tags:
        parts.append(f"TAGS: {', '.join(signal.subcategory_tags)}")

    # Entity names ground the signal in the entity space
    if signal.primary_entity_names:
        parts.append(f"ENTITIES: {', '.join(signal.primary_entity_names[:5])}")

    if signal.body_text:
        parts.append(f"CONTENT: {signal.body_text[:1500]}")

    return "\n".join(parts)
    # Typical token count: 350-600 tokens per signal
```

## 4.3 Batching Strategy

```python
EMBEDDING_BATCH_CONFIG = {
    "primary_batch_size": 100,    # OpenAI supports up to 2048 inputs
    "max_tokens_per_batch": 8000, # Stay well under 8192 token limit
    "timeout_seconds": 15,
    "retry_on_timeout": True,
    "retry_count": 2,
    "fallback_on_failure": "local_minilm"
}

async def batch_embed_signals(signals: list[NormalizedSignal]) -> list[np.ndarray]:
    """
    Embeds signals in batches to minimize API call overhead.
    ~60% reduction in API call count vs. one-by-one embedding.
    """
    inputs = [build_embedding_input(s) for s in signals]
    batches = [inputs[i:i+100] for i in range(0, len(inputs), 100)]

    all_embeddings = []
    for batch in batches:
        try:
            response = await openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=batch
            )
            embeddings = [r.embedding for r in response.data]
            all_embeddings.extend(embeddings)
        except (openai.APITimeoutError, openai.APIConnectionError):
            # Fallback to local model for this batch
            fallback_embeddings = local_minilm_model.encode(batch)
            all_embeddings.extend(fallback_embeddings.tolist())

    return all_embeddings
```

## 4.4 Semantic Deduplication

```python
DEDUP_THRESHOLDS = {
    # Tier 1: Exact hash (Redis — O(1))
    "exact_hash": {
        "method": "SHA-256 of normalized body text",
        "action": "EXACT_DUPLICATE — suppress, increment corroboration"
    },
    # Tier 2: Semantic similarity (pgvector — O(log n) HNSW)
    "semantic": {
        "cosine_similarity_threshold": 0.92,
        "entity_overlap_threshold": 0.70,    # Jaccard coefficient
        "time_window_hours": 2,
        "action": "SEMANTIC_DUPLICATE — suppress, increment corroboration"
    },
    # Tier 3: Near-duplicate (same event, multiple sources — keep all)
    "near_duplicate": {
        "entity_overlap_threshold": 0.85,
        "time_window_minutes": 30,
        "action": "NEAR_DUPLICATE — group, increment corroboration, do not suppress"
    }
}
```

## 4.5 Signal Clustering (Online, Single-Pass)

```python
CLUSTERING_CONFIG = {
    "algorithm": "online_nearest_centroid",
    # Single-pass online clustering: no global recomputation required.
    # Each new signal is assigned to the nearest matching cluster or creates a new one.

    "match_thresholds": {
        "semantic_similarity_min": 0.75,   # cosine similarity to cluster centroid
        "entity_overlap_min": 0.40,         # Jaccard overlap with cluster entities
        "temporal_window_hours": 72,        # max age of cluster for assignment
        "composite_score_min": 0.65        # weighted combination of above three
    },
    "composite_weights": {
        "semantic": 0.50,
        "entity_overlap": 0.35,
        "temporal": 0.15
    },
    "centroid_update": {
        "method": "exponential_moving_average",
        "alpha": 0.30    # 30% new signal, 70% existing centroid
    },
    "minimum_signals_for_active_cluster": 2
}
```

## 4.6 CIL Retrieval

```python
def build_cil_query_embedding(query_text: str,
                               intent: str,
                               entities: list[str]) -> str:
    """
    Augments user query with extracted context before embedding.
    Intent context improves retrieval recall by grounding the query
    in the right semantic space.
    """
    augmented = f"QUERY: {query_text}"

    if entities:
        augmented += f"\nENTITIES: {', '.join(entities)}"

    # Intent-to-context mapping (deterministic — no LLM)
    INTENT_CONTEXT = {
        "HISTORICAL_ANALYSIS":      "historical pattern timeline precedent",
        "COMPETITOR_ANALYSIS":      "competitor strategy market positioning movement",
        "REGULATORY_INQUIRY":       "regulatory directive compliance requirement enforcement",
        "TREND_ANALYSIS":           "trend velocity acceleration market pattern",
        "SIGNAL_INVESTIGATION":     "signal context explanation operational impact",
        "RECOMMENDATION_EXPLANATION": "recommended action rationale justification"
    }
    if intent in INTENT_CONTEXT:
        augmented += f"\nCONTEXT: {INTENT_CONTEXT[intent]}"

    return augmented
```

---

---

# SECTION 5 — SYSTEM 4: LLM SYNTHESIS SANDBOX (GPT-4o)

---

## 5.1 Sandbox Architecture — Six Enforcement Mechanisms

```
MECHANISM 1 — System prompt constraint
  Every call includes a system prompt that explicitly prohibits:
  - Introducing claims not in the provided context
  - Making predictions or forecasts
  - Assigning importance scores
  - Drawing on general knowledge beyond the context package
  Prompt is versioned and tested on every deployment.

MECHANISM 2 — Structured JSON output mode
  All synthesis calls use response_format={"type": "json_object"}
  Forces defined structure; prevents narrative tangents.

MECHANISM 3 — Context-only grounding
  Context package contains ONLY data validated by the pipeline.
  No external data is introduced. LLM cannot perform tool calls or web search.

MECHANISM 4 — Post-synthesis citation verification
  Every factual claim in LLM output is checked against the context package.
  Claims without context-traceable support are stripped programmatically.
  (Python function — not another LLM call)

MECHANISM 5 — Low temperature
  temperature=0.1 minimizes hallucination by reducing exploration
  beyond high-probability completions of the provided context.

MECHANISM 6 — Tight token budget
  max_tokens=1000 for signal synthesis.
  max_tokens=800 for CIL responses.
  Prevents verbose, speculative outputs.
```

## 5.2 Context Assembly (Pre-LLM — Mandatory Sequence)

The context package is assembled entirely from validated pipeline data before any LLM call. No LLM is invoked until this assembly is verified complete.

```python
@dataclass
class SynthesisContextPackage:
    """
    The ONLY data an LLM receives. Every field comes from validated pipeline data.
    No external sources. No user-injected content. No LLM-generated preconditions.
    """
    signal_id: str
    title: str
    body_text: str               # from S3 raw payload (first 3,000 chars)
    published_at: str
    source_name: str
    source_tier: int
    source_url: str
    primary_domain: str
    subcategory_tags: list[str]

    # Scores: FROM DETERMINISTIC ENGINES — not from LLM
    confidence_score: float
    confidence_band: str
    urgency_score: float
    urgency_band: str
    corroboration_count: int
    normalized_region_tags: list[str]

    # Entities: from Entity Registry resolution
    entities: list[EntityContext]

    # Corroborating sources (max 5)
    corroborating_sources: list[CorroboratingSource]

    # Historical context (max 3)
    historical_context: list[HistoricalSignalContext]

    # Cluster (if assigned)
    cluster: ClusterContext | None

    # Recommendation: FROM RULE ENGINE — not from LLM
    recommendation: RecommendationContext

    # Context size guard
    estimated_token_count: int  # must be < 12,000 before LLM call


def validate_context_package(ctx: SynthesisContextPackage) -> None:
    assert ctx.signal_id, "signal_id required"
    assert ctx.title or ctx.body_text, "content required"
    assert 0.0 <= ctx.confidence_score <= 1.0
    assert 0.0 <= ctx.urgency_score <= 1.0
    assert ctx.source_tier in range(1, 8)
    assert ctx.estimated_token_count <= 12000, \
        f"Context too large: {ctx.estimated_token_count} tokens"

    # Verify all cited source signal_ids exist in database
    for source in ctx.corroborating_sources:
        assert signal_exists_in_db(source.signal_id)
    for hist in ctx.historical_context:
        assert signal_exists_in_db(hist.signal_id)
```

## 5.3 Synthesis System Prompt (Versioned)

```
SYSTEM_PROMPT_SYNTHESIS_v1.4:

You are a structured intelligence formatting service for Stem Cogent.

YOUR ROLE:
You receive a validated context package. Your task is to format this
data into clear, professional intelligence output.

STRICT CONSTRAINTS:
1. Use ONLY information explicitly present in the context package.
2. Do NOT introduce claims, facts, statistics, or analysis not in context.
3. Do NOT make predictions, forecasts, or speculative assessments.
4. Do NOT use qualifying language like "may", "might", "could" unless
   present in source text.
5. Do NOT evaluate or express opinions on signal importance.
   Importance scores are provided — you format them into language only.
6. Every factual claim MUST reference a source from the citations array
   using the exact source_signal_id values provided.
7. If the context is insufficient to write a sentence, omit the sentence.
   Do not pad with generic statements.

OUTPUT FORMAT:
Return only valid JSON matching this exact structure. No preamble.

{
  "summary": "3-5 sentence executive summary using only provided context",
  "key_developments": ["development 1", "development 2", "development 3"],
  "operational_implication": "2 sentence operational impact statement",
  "confidence_note": "1 sentence citing confidence basis using provided scores",
  "recommendation_text": "2-3 sentence formatted recommendation",
  "citations": [
    {
      "claim_index": 0,
      "source_signal_id": "exact uuid from context",
      "source_name": "exact source name from context"
    }
  ]
}
```

## 5.4 CIL Synthesis System Prompt (Versioned)

```
SYSTEM_PROMPT_CIL_v1.2:

You are an intelligence analyst interface for Stem Cogent.

YOUR ROLE:
Synthesize a grounded, accurate response to the user's query using
ONLY the intelligence context provided below.

STRICT CONSTRAINTS:
1. Use ONLY provided intelligence context. Do NOT use general knowledge.
2. If context is insufficient: respond with "The available intelligence
   does not contain sufficient data to address this question."
   Do NOT fabricate an answer under any circumstances.
3. Do NOT assign or modify confidence scores.
4. Do NOT make forward-looking predictions.
5. Do NOT provide legal or financial advice.
6. Every factual claim must be traceable to a provided source signal.
7. Queries outside Stem Cogent's scope: politely redirect. Explain what
   the CIL can help with instead.

TONE: Professional, analytical, precise.
Do not use conversational filler. Do not over-explain basic concepts.

OUTPUT FORMAT: Return only valid JSON.
{
  "answer_text": "grounded response",
  "citations": [
    {
      "claim_text": "exact claim being cited",
      "source_signal_id": "uuid",
      "source_name": "string",
      "source_date": "ISO date"
    }
  ],
  "confidence_indicator": "HIGH | MODERATE | LOW | INSUFFICIENT_DATA",
  "response_grounded": true,
  "follow_up_suggestions": ["suggestion 1", "suggestion 2"]
}
```

## 5.5 Citation Verification Service

```python
def verify_citations(synthesis_output: dict,
                     context: SynthesisContextPackage) -> CitationResult:
    """
    Programmatic citation check — NOT another LLM call.
    Strips any citation referencing a source_signal_id not in the context package.
    """
    valid_ids = {context.signal_id} | \
                {s.signal_id for s in context.corroborating_sources} | \
                {h.signal_id for h in context.historical_context}

    verified = []
    stripped = 0

    for citation in synthesis_output.get("citations", []):
        if citation.get("source_signal_id") in valid_ids:
            verified.append(citation)
        else:
            stripped += 1
            cloudwatch.put_metric_data(
                Namespace="StemCogent/Synthesis",
                MetricData=[{
                    "MetricName": "CitationHallucinations",
                    "Value": 1,
                    "Unit": "Count"
                }]
            )

    synthesis_output["citations"] = verified
    return CitationResult(verified=len(verified), stripped=stripped)
```

## 5.6 Fallback Synthesis (Template Engine)

When both LLM providers fail, template synthesis produces a complete, structured output without any LLM call:

```python
def template_synthesis(signal: Signal,
                       context: SynthesisContextPackage) -> dict:
    """
    Zero-LLM fallback. All content from validated pipeline fields.
    Quality is reduced. Structure is complete. Signal is delivered.
    """
    entity_clause = (
        f"involving {', '.join(e.entity_name for e in context.entities[:3])}"
        if context.entities else ""
    )
    return {
        "summary": (
            f"A {context.urgency_band.lower()} urgency "
            f"{context.primary_domain.lower()} signal was detected from "
            f"{context.source_name} (Tier {context.source_tier}), "
            f"published {context.published_at[:10]}. {entity_clause}. "
            f"Confidence: {context.confidence_band} "
            f"({context.confidence_score:.2f})."
        ),
        "key_developments": [
            tag.replace("_", " ").title()
            for tag in context.subcategory_tags[:3]
        ],
        "operational_implication": (
            f"This {context.primary_domain.lower()} signal warrants "
            f"review by the relevant team."
        ),
        "confidence_note": (
            f"Based on Tier {context.source_tier} source with "
            f"{context.confidence_band.lower().replace('_', ' ')} confidence."
        ),
        "recommendation_text": format_recommendation_template(
            context.recommendation.recommendation_type,
            context.recommendation.recommendation_priority
        ),
        "citations": [{
            "claim_index": 0,
            "source_signal_id": context.signal_id,
            "source_name": context.source_name
        }],
        "llm_synthesis_failed": True,
        "synthesis_method": "TEMPLATE_FALLBACK"
    }
```

## 5.7 LLM Provider Failover Chain

```
Primary: OpenAI GPT-4o
  Timeout: 15 seconds
  On failure: → Anthropic Claude Sonnet (fallback)

Fallback: Anthropic Claude Sonnet
  Timeout: 15 seconds
  On failure: → Template Synthesis Engine

Template Engine: Zero LLM cost, structured fields only
  Always available. Always completes.

CIL-specific:
  Primary: OpenAI GPT-4o
  Fallback: Anthropic Claude Sonnet
  No template fallback for CIL — CIL returns structured error response:
  "Intelligence retrieval is temporarily operating in reduced mode.
   Please try again in a few minutes."
```

---

---

# SECTION 6 — DETERMINISTIC SYSTEMS (RULE-BASED — NO ML)

---

## 6.1 Relevance Filter

**Replaces:** `sc-relevance-v{n}` (XGBoost model — deferred)

The relevance filter uses a weighted scoring formula on structured metadata. No model required. No training data required.

```python
RELEVANCE_SCORING_WEIGHTS = {
    "source_tier":          {1: 1.0, 2: 0.90, 3: 0.75, 4: 0.60, 5: 0.45,
                             6: 1.0, 7: 0.50},
    "region_match":         1.0,    # source registered region matches NG/target
    "entity_presence":      0.25,   # per resolved registry entity (max contribution 0.50)
    "regulatory_entity":    0.30,   # REGULATOR_NG type entity present
    "has_compliance_term":  0.15,   # KYC, AML, compliance keyword present
    "has_deadline":         0.20,   # compliance deadline extracted
}

def compute_relevance_score(signal: NormalizedSignal,
                             source: SourceRecord) -> float:
    score = 0.0

    # Source tier contribution (most important factor)
    score += RELEVANCE_SCORING_WEIGHTS["source_tier"].get(source.tier, 0.45)

    # Region match
    if source.region in signal.normalized_region_tags:
        score += RELEVANCE_SCORING_WEIGHTS["region_match"]

    # Entity presence (cap at 0.50 total)
    entity_contribution = min(
        0.50,
        len(signal.resolved_entities) * RELEVANCE_SCORING_WEIGHTS["entity_presence"]
    )
    score += entity_contribution

    # Regulatory entity bonus
    if any(e.label == "REGULATOR_NG" for e in signal.resolved_entities):
        score += RELEVANCE_SCORING_WEIGHTS["regulatory_entity"]

    # Compliance terms
    if has_compliance_terms(signal.body_text):
        score += RELEVANCE_SCORING_WEIGHTS["has_compliance_term"]

    # Deadline present
    if signal.compliance_deadline_days is not None:
        score += RELEVANCE_SCORING_WEIGHTS["has_deadline"]

    # Normalize to 0.0–1.0
    max_possible = sum([1.0, 1.0, 0.50, 0.30, 0.15, 0.20])  # = 3.15
    return min(1.0, score / max_possible)

# Suppression threshold
RELEVANCE_SUPPRESSION_THRESHOLD = 0.28
# Signals below this score are discarded before enrichment stage
# (Conservative — false negatives more costly than false positives)
```

---

## 6.2 Risk Detection Engine

**Replaces:** `sc-risk-v{n}` (DeBERTa risk classifier — deferred)

Risk detection at launch is entirely rule-based: keyword patterns + taxonomy signals + source tier signals.

```python
RISK_DETECTION_RULES = [
    # Enforcement actions
    {
        "risk_label": "ENFORCEMENT_ACTION",
        "keywords": ["penalized", "penalty", "revoked", "suspended license",
                     "enforcement action", "fined", "sanctioned", "shutdown",
                     "ordered to cease", "license withdrawal"],
        "entity_types": ["REGULATOR_NG"],
        "min_confidence": 0.85,
        "urgency_boost": 0.20
    },
    # Infrastructure failures
    {
        "risk_label": "INFRASTRUCTURE_FAILURE",
        "keywords": ["outage", "downtime", "service disruption", "unavailable",
                     "system failure", "transaction failure", "switch down",
                     "NIBSS down", "interswitch failure"],
        "entity_types": ["FINANCIAL_INFRA"],
        "min_confidence": 0.80,
        "urgency_boost": 0.25
    },
    # Settlement issues
    {
        "risk_label": "SETTLEMENT_DELAY",
        "keywords": ["settlement delay", "stuck transaction", "failed reversal",
                     "delayed credit", "transaction not reversed", "dispute",
                     "chargeback spike"],
        "entity_types": [],
        "min_confidence": 0.75,
        "urgency_boost": 0.15
    },
    # Fraud signals
    {
        "risk_label": "FRAUD_INCIDENT",
        "keywords": ["fraud", "unauthorized transaction", "account compromise",
                     "data breach", "customer funds stolen", "sim swap",
                     "phishing", "scam"],
        "entity_types": [],
        "min_confidence": 0.82,
        "urgency_boost": 0.20
    }
]

def detect_risk_signals(signal: ClassifiedSignal) -> list[RiskFlag]:
    """
    Evaluates risk detection rules against signal text and entity types.
    Returns list of detected risk flags (can be multiple per signal).
    All rules evaluated — not first-match-wins.
    """
    detected_risks = []
    text_lower = (signal.title + " " + signal.body_text).lower()
    signal_entity_types = {e.label for e in signal.resolved_entities}

    for rule in RISK_DETECTION_RULES:
        # Keyword check (ANY keyword must match)
        keyword_match = any(kw in text_lower for kw in rule["keywords"])
        if not keyword_match:
            continue

        # Entity type check (if specified, at least one must match)
        if rule["entity_types"]:
            entity_match = bool(
                signal_entity_types.intersection(set(rule["entity_types"]))
            )
            if not entity_match:
                continue

        detected_risks.append(RiskFlag(
            risk_label=rule["risk_label"],
            confidence=rule["min_confidence"],
            urgency_boost=rule["urgency_boost"],
            detection_method="RULE_BASED"
        ))

    return detected_risks
```

---

## 6.3 Knowledge Graph Builder

**Replaces:** `sc-rel-extract-v{n}` (BERT relationship extraction — deferred)

Relationships are built deterministically from NER output + taxonomy signals. No BERT model, no training data, no annotation cost.

```python
RELATIONSHIP_INFERENCE_RULES = [
    # REGULATES relationship
    {
        "trigger": "signal has REGULATOR_NG entity + FINTECH_CO entity",
        "domain_match": ["REGULATORY", "COMPLIANCE"],
        "relationship_type": "REGULATES",
        "direction": "REGULATOR_NG → FINTECH_CO",
        "confidence": 0.90
    },
    # LICENSED_BY relationship
    {
        "trigger": "signal title/body contains 'licensed', 'license approval', 'granted license'",
        "entities_required": ["REGULATOR_NG", "FINTECH_CO"],
        "relationship_type": "LICENSED_BY",
        "direction": "FINTECH_CO → REGULATOR_NG",
        "confidence": 0.88
    },
    # COMPETES_WITH relationship
    {
        "trigger": "two or more FINTECH_CO entities in same signal",
        "domain_match": ["COMPETITIVE", "MARKET_EXPANSION"],
        "relationship_type": "COMPETES_WITH",
        "direction": "FINTECH_CO ↔ FINTECH_CO",
        "confidence": 0.72    # lower — competitive relationship is inferred
    },
    # PARTNERS_WITH relationship
    {
        "trigger": "keywords: 'partnership', 'integration', 'collaboration', 'joins forces'",
        "entities_required": ["FINTECH_CO"],
        "relationship_type": "PARTNERS_WITH",
        "direction": "bidirectional",
        "confidence": 0.85
    },
    # PROVIDES_SERVICE_TO relationship
    {
        "trigger": "FINANCIAL_INFRA entity + FINTECH_CO entity in same signal",
        "domain_match": ["INFRASTRUCTURE", "OPERATIONAL"],
        "relationship_type": "PROVIDES_SERVICE_TO",
        "direction": "FINANCIAL_INFRA → FINTECH_CO",
        "confidence": 0.82
    }
]

def build_knowledge_graph_updates(
    signal: EnrichedSignal
) -> list[GraphRelationshipUpdate]:
    """
    Deterministically infers entity relationships from signal content.
    Returns graph update records to be written to Neo4j async queue.
    No ML model involved.
    """
    updates = []
    entity_types = {e.entity_id: e.label for e in signal.resolved_entities}

    for rule in RELATIONSHIP_INFERENCE_RULES:
        entities_matching = evaluate_relationship_rule(rule, signal, entity_types)
        if entities_matching:
            for source_id, target_id in entities_matching:
                updates.append(GraphRelationshipUpdate(
                    source_entity_id=source_id,
                    target_entity_id=target_id,
                    relationship_type=rule["relationship_type"],
                    confidence=rule["confidence"],
                    evidence_signal_id=signal.signal_id,
                    inference_method="DETERMINISTIC_RULE"
                ))

    return updates
```

---

## 6.4 Confidence Scoring Engine

Fully deterministic five-factor formula. No model. No LLM.

```python
CONFIDENCE_WEIGHTS = {
    "source_reliability":        0.35,
    "corroboration":             0.25,
    "recency":                   0.15,
    "entity_resolution_quality": 0.15,
    "classification_confidence": 0.10
}

DOMAIN_VOLATILITY_HOURS = {
    "REGULATORY":     72,
    "COMPETITIVE":    48,
    "INFRASTRUCTURE": 12,
    "FINANCIAL":       6,
    "CONSUMER":       24,
    "DEFAULT":        36
}

def compute_confidence_score(
    source_reliability: float,
    corroboration_count: int,
    published_at: datetime,
    entity_resolution_quality: float,
    classification_confidence: float,
    primary_domain: str
) -> ConfidenceScore:

    # Corroboration score (0 sources=0.50, 1=0.70, 2=0.90, 3+=1.0)
    corroboration_score = min(1.0, 0.50 + (corroboration_count * 0.20))

    # Recency score (decays linearly based on domain volatility)
    hours_since = (datetime.utcnow() - published_at).total_seconds() / 3600
    stale_hours = DOMAIN_VOLATILITY_HOURS.get(primary_domain,
                                               DOMAIN_VOLATILITY_HOURS["DEFAULT"])
    recency_score = max(0.0, 1.0 - (hours_since / stale_hours))

    raw_score = (
        source_reliability        * CONFIDENCE_WEIGHTS["source_reliability"] +
        corroboration_score       * CONFIDENCE_WEIGHTS["corroboration"] +
        recency_score             * CONFIDENCE_WEIGHTS["recency"] +
        entity_resolution_quality * CONFIDENCE_WEIGHTS["entity_resolution_quality"] +
        classification_confidence * CONFIDENCE_WEIGHTS["classification_confidence"]
    )

    score = round(min(1.0, max(0.0, raw_score)), 3)

    band = (
        "HIGH_CONFIDENCE"     if score >= 0.85 else
        "MODERATE_CONFIDENCE" if score >= 0.65 else
        "LOW_CONFIDENCE"      if score >= 0.40 else
        "UNVERIFIED"
    )

    return ConfidenceScore(score=score, band=band, breakdown={
        "source_reliability_contribution":   source_reliability,
        "corroboration_contribution":         corroboration_score,
        "recency_contribution":               recency_score,
        "entity_resolution_contribution":     entity_resolution_quality,
        "classification_confidence_contribution": classification_confidence
    })
```

---

## 6.5 Urgency Scoring Engine

Fully deterministic. No model. Inputs include domain urgency weight, confidence score, corroboration, and compliance deadline proximity.

```python
DOMAIN_URGENCY_WEIGHTS = {
    "REGULATORY":     0.90,   # Highest — regulatory changes have hard deadlines
    "INFRASTRUCTURE": 0.88,   # Critical for operational continuity
    "FRAUD_RISK":     0.85,
    "FINANCIAL":      0.80,
    "COMPETITIVE":    0.65,
    "CONSUMER":       0.60,
    "CAPITAL_FUNDING": 0.55,
    "MARKET_EXPANSION": 0.55,
    "DEFAULT":        0.50
}

def compute_urgency_score(
    primary_domain: str,
    confidence_score: float,
    corroboration_count: int,
    compliance_deadline_days: int | None,
    risk_flags: list[RiskFlag]
) -> UrgencyScore:

    domain_weight = DOMAIN_URGENCY_WEIGHTS.get(
        primary_domain, DOMAIN_URGENCY_WEIGHTS["DEFAULT"]
    )

    # Corroboration normalized (0 sources=0.50, 3+=1.0)
    corroboration_normalized = min(1.0, 0.50 + (corroboration_count * 0.17))

    # Deadline proximity (0.0 if no deadline, 1.0 if deadline is today)
    if compliance_deadline_days is not None and compliance_deadline_days <= 90:
        deadline_score = max(0.0, 1.0 - (compliance_deadline_days / 90))
    else:
        deadline_score = 0.0

    raw_urgency = (
        domain_weight              * 0.35 +
        confidence_score           * 0.30 +
        corroboration_normalized   * 0.20 +
        deadline_score             * 0.15
    )

    # Risk flag urgency boost (additive)
    total_boost = sum(rf.urgency_boost for rf in risk_flags)
    final_urgency = round(min(1.0, raw_urgency + total_boost), 3)

    band = (
        "CRITICAL" if final_urgency >= 0.90 else
        "HIGH"     if final_urgency >= 0.75 else
        "STANDARD" if final_urgency >= 0.55 else
        "LOW"
    )

    return UrgencyScore(score=final_urgency, band=band)
```

---

## 6.6 Recommendation Engine

Fully deterministic rule evaluation. LLM only formats the wording — never generates the recommendation itself.

```python
# Rules stored in config.recommendation_rules (PostgreSQL, hot-reloadable)

RECOMMENDATION_RULES = [
    {
        "rule_id": "REC-001",
        "name": "REGULATORY_HIGH_CONFIDENCE_URGENCY",
        "conditions": {
            "primary_domain": "REGULATORY",
            "urgency_score_min": 0.75,
            "confidence_score_min": 0.80,
            "entity_types_any": ["REGULATOR_NG"]
        },
        "output": {
            "recommendation_type": "COMPLIANCE_ACTION_REQUIRED",
            "recommendation_priority": "HIGH",
            "alert_threshold": "HIGH"
        }
    },
    {
        "rule_id": "REC-002",
        "name": "CRITICAL_REGULATORY",
        "conditions": {
            "primary_domain": "REGULATORY",
            "urgency_score_min": 0.90,
            "confidence_score_min": 0.85
        },
        "output": {
            "recommendation_type": "COMPLIANCE_ACTION_REQUIRED",
            "recommendation_priority": "CRITICAL",
            "alert_threshold": "CRITICAL"
        }
    },
    {
        "rule_id": "REC-003",
        "name": "INFRASTRUCTURE_FAILURE",
        "conditions": {
            "risk_flags_any": ["INFRASTRUCTURE_FAILURE"],
            "urgency_score_min": 0.70
        },
        "output": {
            "recommendation_type": "OPERATIONAL_RISK_ALERT",
            "recommendation_priority": "HIGH",
            "alert_threshold": "HIGH"
        }
    },
    {
        "rule_id": "REC-004",
        "name": "COMPETITIVE_CLUSTER_ACCELERATING",
        "conditions": {
            "primary_domain": "COMPETITIVE",
            "cluster_status": "ACCELERATING",
            "confidence_score_min": 0.70
        },
        "output": {
            "recommendation_type": "COMPETITIVE_MONITORING_ESCALATE",
            "recommendation_priority": "MEDIUM",
            "alert_threshold": "STANDARD"
        }
    }
]
```

---

---

# SECTION 7 — HUMAN INTELLIGENCE OPERATIONS LAYER

---

## 7.1 Overview

The Human Intelligence Operations Layer is the missing component that makes the machine intelligence layer improve over time. Without it, ML quality eventually stagnates or collapses. With it, every human review action directly improves classification accuracy, entity coverage, and signal quality.

This is not a QA function. It is the ground truth generation engine that the entire ML system depends on.

```
MACHINE PIPELINE OUTPUT
        |
        v
+----------------------------------+
|  HUMAN INTELLIGENCE OPS          |
|                                  |
|  Signal Review Queue             |← Low-confidence classifications
|  Taxonomy Review Queue           |← Classification conflicts
|  Source Validation Queue         |← New/suspicious sources
|  Entity Curation Queue           |← Unresolved entity mentions
|  Labeling Platform               |← Active annotation for ML training
+----------------------------------+
        |
        v
IMPROVED TRAINING DATA
        |
        v
BETTER ML MODELS + RULES
```

## 7.2 Signal Review Queue

**Trigger conditions for entry into Signal Review Queue:**

```python
SIGNAL_REVIEW_TRIGGERS = {
    "classification_review_flag": True,          # Hybrid classifier set review_flag=True
    "classification_confidence_below": 0.70,     # Low classification confidence
    "hybrid_conflict": True,                     # Rule and ML classifiers disagreed
    "manipulation_risk_score_above": 0.50,       # Elevated manipulation risk (not yet suspicious)
    "entity_resolution_quality_below": 0.60,     # Poor entity resolution
    "new_source_first_collection": True,         # First collection from any source
}
```

**Review workflow:**

```
Signal Review Queue Item UI:
  ┌─────────────────────────────────────────────────────────┐
  │  SIGNAL REVIEW                          [1 of 47 pending] │
  ├─────────────────────────────────────────────────────────┤
  │  Title: [signal title]                                   │
  │  Source: [name] · Tier [n]                               │
  │  Body preview: [first 400 chars]                         │
  │                                                          │
  │  System classified as: [REGULATORY]  (conf: 0.68)       │
  │  Rule said: REGULATORY  ML said: COMPETITIVE             │
  │                                                          │
  │  Correct domain:  [dropdown — 20 domains]                │
  │  Secondary domains: [multi-select]                       │
  │  Notes: [optional text]                                  │
  │                                                          │
  │  [Confirm Classification]  [Skip]  [Mark as Noise]      │
  └─────────────────────────────────────────────────────────┘
```

**Review output:** Confirmed label written to `feedback.signal_feedback` + `feedback.classification_training_queue`. Every confirmed review is a training data point.

---

## 7.3 Taxonomy Review Queue

**Purpose:** Review signals where classification routing to review is triggered, and where new subcategory tags may need to be added to the taxonomy.

**Trigger conditions:**
- Classification `route_to_review = True`
- Subcategory tag count = 0 (classifier found no matching subcategory)
- New keyword pattern appears > 50 times in 24 hours with no matching taxonomy rule

**Output of taxonomy review:** Either confirm existing classification OR propose new subcategory tag / rule addition. New rules and tags are only activated after ADMIN approval via `/admin/taxonomy` API.

---

## 7.4 Source Validation Queue

**Purpose:** Human evaluation of new sources before they become trusted in the pipeline, and investigation of sources flagged for manipulation risk.

**Trigger conditions:**
- Any source with < 5 completed collection jobs (new source)
- Source reliability_score drops below 0.50 (quality degradation)
- Source manipulation_risk_score > 0.50 on 3+ consecutive signals
- Source registers schema_version change

**Review items:**
- Source URL and publication history
- Publisher identity verification
- Content quality assessment (1-5 rating)
- Action: APPROVE / TIER_DOWNGRADE / PAUSE / REMOVE

---

## 7.5 Entity Curation Queue

**Purpose:** Review unresolved entity mentions from the spaCy extraction stage and decide whether to add them to the Entity Registry.

**Trigger:** `ExtractionResult.unresolved_mentions` list is non-empty

**Review workflow:**

```
Entity Curation Queue Item:
  ┌─────────────────────────────────────────────────────────┐
  │  ENTITY CURATION                        [1 of 23 pending] │
  ├─────────────────────────────────────────────────────────┤
  │  Extracted mention: "Cowrywise Technologies"             │
  │  From signal: [title] · Source: [name]                   │
  │  Context: "...Cowrywise Technologies announced that..."  │
  │                                                          │
  │  Action:                                                 │
  │  ○ Add to registry as new entity                        │
  │    Name: [Cowrywise] Type: [FINTECH_CO] Region: [NG]   │
  │    Aliases: [Cowrywise Technologies, cowrywise.com]     │
  │  ○ Link to existing entity: [search existing...]        │
  │  ○ This is noise — do not add                          │
  │                                                          │
  │  [Submit]  [Skip]                                        │
  └─────────────────────────────────────────────────────────┘
```

**Output:** New entity record in `intelligence.entities` with `is_verified = TRUE`. Entity Registry cache in Redis is refreshed immediately on approval.

---

## 7.6 Labeling Platform

**Purpose:** Active annotation tool for generating ML training data on demand.

**Technology:** Custom internal web UI (Next.js, accessible only to Intelligence Operations team)

**Labeling tasks available:**

| Task | Description | Output |
|---|---|---|
| Signal domain classification | Label signal with correct domain(s) | Training data for DistilBERT classifier |
| Entity span annotation | Mark entity spans and types in text | Training data for future spaCy fine-tuning (Phase 2) |
| Relationship annotation | Mark relationships between entity pairs | Training data for Phase 3 relationship extraction |
| Risk signal labeling | Mark whether signal contains risk indicators | Training data for Phase 2 risk classifier |

**Labeling throughput targets:**

```
Phase 1 labeling goal (first 90 days):
  - 500 domain classification labels per priority domain (8 domains = 4,000 total)
  - 500 entity annotation examples across key entity types
  - 200 risk signal positive examples
  - Labeling velocity: ~50 signals/day by a single operator

Phase 2 labeling goal (months 4-12, post-customer):
  - 2,000+ domain labels per class (sufficient for fine-tuning)
  - 1,000 relationship annotation examples
  - 500 risk signal examples per category
  - Leverage customer feedback as additional labeling signal
```

---

## 7.7 Feedback Loop Architecture

Every human review action flows back into the ML improvement cycle:

```
USER FEEDBACK (from app)
  └─ "Incorrect Classification" → classification_training_queue
  └─ "False Positive" → alert threshold calibration data
  └─ "Strategic" → signal importance signal for ranking

HUMAN OPS REVIEW
  └─ Signal Review Queue → classification training data
  └─ Entity Curation → entity registry expansion
  └─ Source Validation → source reliability score update
  └─ Taxonomy Review → new rules + subcategory tags

AUTOMATED FEEDBACK
  └─ High-confidence rule classifications → auto-labeled training data (with spot check)
  └─ CIL query ratings → synthesis quality monitoring

ALL FEEDBACK → feedback.signal_feedback (PostgreSQL)
               + feedback.classification_training_queue
               + CloudWatch metrics
               → Weekly evaluation run
               → Trigger retraining if thresholds breached
```

---

---

# SECTION 8 — MLFLOW & MODEL LIFECYCLE (SCOPED TO LAUNCH STACK)

---

## 8.1 MLflow Setup

**Scope at launch:** Track DistilBERT classifier training runs only.

```python
MLFLOW_CONFIG = {
    "tracking_uri": "http://mlflow.sc-internal.svc:5000",
    "artifact_location": "s3://sc-ml-artefacts-prod/mlflow/",
    "experiments": {
        "classifier": "sc-signal-taxonomy-classifier"
        # Others added in Phase 2 as models are introduced
    }
}

def train_classifier(train_data, val_data, config):
    with mlflow.start_run(run_name=f"sc-classifier-{config['version']}"):
        mlflow.log_params({
            "base_model": "distilbert-base-uncased",
            "learning_rate": config["learning_rate"],
            "batch_size": config["batch_size"],
            "num_epochs": config["num_epochs"],
            "train_samples": len(train_data),
            "val_samples": len(val_data)
        })
        for epoch_metrics in trainer.train():
            mlflow.log_metrics({
                "eval_f1_macro":    epoch_metrics["f1_macro"],
                "eval_precision":   epoch_metrics["precision"],
                "eval_recall":      epoch_metrics["recall"]
            }, step=epoch_metrics["epoch"])

        for domain, f1 in per_domain_f1.items():
            mlflow.log_metric(f"f1_{domain.lower()}", f1)

        mlflow.pytorch.log_model(
            model, "model",
            registered_model_name="sc-classifier"
        )
```

## 8.2 Model Registry Stages

```
STAGING → PRODUCTION → ARCHIVED

Promotion criteria (STAGING → PRODUCTION):
  - f1_macro >= 0.82 on validation set
  - f1_REGULATORY >= 0.88
  - No regression > 3% vs current PRODUCTION model
  - Shadow deployment passed (48 hours)
  - Manual approval from ML Engineering Lead
```

---

---

# SECTION 9 — TRAINING DATA STRATEGY

---

## 9.1 Training Data Lifecycle

```
PHASE 0 (Pre-launch): Seed corpus
  - Intelligence Operations labels 4,000 signals across 8 priority domains
  - 500 signals per domain minimum before classifier is first trained
  - Duration: 3-4 weeks of part-time labeling

PHASE 1 (Launch, months 1-3): Continuous accumulation
  - High-confidence rule classifications auto-labeled (spot-checked 10%)
  - Human review queues yield ~30-50 reviewed labels/day
  - Customer feedback provides classification correction signal
  - Target: 1,000 labels per domain by end of Phase 1

PHASE 2 (months 4-12): Fine-tuning trigger
  - When any domain drops below f1_macro 0.82 on weekly evaluation
  - Or when labeled corpus doubles from original training set
  - Trigger automated retraining pipeline on SageMaker
  - Target: 2,000+ labels per domain
```

## 9.2 Data Quality Rules

```python
TRAINING_DATA_QUALITY_RULES = {
    "inter_annotator_agreement": {
        "spot_check_rate": 0.05,            # 5% second-reviewed
        "minimum_agreement_rate": 0.85
    },
    "class_balance": {
        "max_imbalance_ratio": 5.0           # No class > 5× smallest class
    },
    "synthetic_data_cap": {
        "max_ratio_per_class": 0.20,         # Max 20% synthetic per class
        "requires_human_review": True
    },
    "auto_label_acceptance": {
        "minimum_rule_confidence": 0.92,     # Only auto-label very high-confidence rules
        "spot_check_rate": 0.10
    }
}
```

---

---

# SECTION 10 — MODEL SERVING ARCHITECTURE (AWS)

---

## 10.1 Phase 1–2: ECS Fargate (CPU-Only)

```yaml
sc-classification-service:
  CPU:    2048        # 2 vCPU
  Memory: 4096 MB     # DistilBERT ~250MB + overhead
  Startup grace period: 60 seconds  (model loading from S3)
  MODEL_S3_PATH: s3://sc-ml-artefacts-prod/models/sc-classifier/v{n}/
  Autoscaling:
    Metric:    SQS ApproximateNumberOfMessagesVisible (pipeline-classified)
    Target:    <100 messages per running task
    Min tasks: 2
    Max tasks: 20
```

## 10.2 Phase 3+: SageMaker Real-Time Endpoints

Migrated when signal volume exceeds 100K/day or ECS classification latency P95 > 150ms.

```python
SAGEMAKER_CONFIG = {
    "instance_type": "ml.g4dn.xlarge",   # 1× T4 GPU, 16GB RAM
    "initial_instance_count": 2,
    "auto_scaling": {
        "min_capacity": 2,
        "max_capacity": 8,
        "target_invocations_per_instance": 200
    }
}
```

---

---

# SECTION 11 — COST MONITORING & MITIGATION

---

## 11.1 LLM Cost Estimation (Launch Scale)

```
Signal synthesis (GPT-4o):
  avg context:  5,000 input tokens + 400 output tokens
  cost/signal:  (5 × $0.0025) + (0.4 × $0.010) = $0.01650
  signals/day requiring synthesis: ~5,000 (10% of 50K)
  daily cost: $82.50

Embeddings (text-embedding-3-small):
  avg tokens/signal: 500
  cost/signal: $0.00001
  signals/day: 50,000
  daily cost: $0.50

CIL queries (GPT-4o):
  avg context:  6,000 input + 500 output tokens
  cost/query:   $0.0200
  queries/day:  200
  daily cost:   $4.00

TOTAL ESTIMATED DAILY: ~$87/day = ~$2,610/month
```

## 11.2 Cost Mitigation Strategies

```python
COST_MITIGATION = {
    "rule_shortcut": {
        "trigger": "rule confidence >= 0.88",
        "effect": "Skip ML inference call entirely (~40% reduction)"
    },
    "tiered_synthesis": {
        "CRITICAL + HIGH": "GPT-4o",
        "STANDARD":        "Anthropic Claude Sonnet (~30% cheaper)",
        "LOW":             "Template synthesis (zero LLM cost)",
        "estimated_savings": "~35% reduction in GPT-4o call volume"
    },
    "embedding_batching": {
        "batch_size": 100,
        "estimated_savings": "60% fewer API calls"
    },
    "dedup_bypass": {
        "rule": "SEMANTIC_DUPLICATE signals skip synthesis entirely",
        "estimated_savings": "~8% fewer synthesis calls"
    }
}
```

## 11.3 CloudWatch Cost Alarms

```python
COST_ALARMS = {
    "daily_llm_warning":  { "threshold_usd": 150, "channel": "Slack #ml-costs" },
    "daily_llm_critical": { "threshold_usd": 300,
                            "channel": "PagerDuty + auto-downgrade synthesis tier" },
    "daily_embedding":    { "threshold_usd": 20,  "channel": "Slack #ml-costs" }
}
```

---

---

# SECTION 12 — PHASE-GATED ML EXPANSION ROADMAP

---

## 12.1 Build Plan by Phase

```
PHASE 1 — LAUNCH (Months 1–3)
  ✓ spaCy NER + Entity Registry (dictionary-first)
  ✓ DistilBERT taxonomy classifier (seed corpus, 4,000 labels)
  ✓ OpenAI Embeddings pipeline
  ✓ GPT-4o synthesis sandbox + Anthropic fallback
  ✓ All deterministic engines (confidence, urgency, relevance, risk, recommendation)
  ✓ Knowledge Graph Builder (rule-based, no BERT)
  ✓ Human Intelligence Operations Layer (all 5 queues + labeling platform)
  ✓ MLflow (classifier tracking only)

PHASE 2 — POST-CUSTOMER (Months 4–12)
  → Risk classifier (DeBERTa) — requires 600+ labeled examples from Human Ops
  → Relevance model (XGBoost) — requires 1,000+ negative examples
  → Classifier retraining pipeline — when labeled corpus reaches 2,000/class
  → spaCy NER fine-tuning — when Entity Curation generates 2,000+ annotations
  → Full MLflow model registry for all models
  → Model drift detection (SageMaker Model Monitor)

PHASE 3 — SCALE (Year 2)
  → Relationship extraction model (BERT) — after 3,000+ relationship labels
  → Sentiment classifier — if consumer domain proves customer demand
  → SageMaker endpoints — at 100K+ signals/day
  → Advanced trend forecasting — after 12+ months historical data
  → Cross-market models (GH, KE) — after regional expansion
```

## 12.2 Phase Advancement Gates

```python
PHASE_GATES = {
    "phase_1_to_2": {
        "revenue":        "First paying customer",
        "training_data":  "1,000 labeled examples per priority domain",
        "product":        "CIL daily active usage by pilot customers",
        "human_ops":      "Review queue latency < 24 hours sustained"
    },
    "phase_2_to_3": {
        "revenue":        "ARR > $500K or Series A closed",
        "training_data":  "2,000+ labeled examples per domain",
        "signal_volume":  "50K+ signals/day sustained",
        "customers":      "10+ paying enterprise customers"
    }
}
```

---

---

# SECTION 13 — FAILURE MODES & DEGRADATION STRATEGY

---

## 13.1 Graceful Degradation Hierarchy

```
SYSTEM 1 — NER FAILURES
  spaCy unavailable:
    → Registry-only extraction; flag SPACY_UNAVAILABLE; pipeline continues
  Entity Registry cache miss:
    → Load from PostgreSQL directly; ~200ms latency increase; pipeline continues

SYSTEM 2 — CLASSIFIER FAILURES
  ML classifier unavailable:
    → Rule-based only; confidence capped at 0.75; flag ML_UNAVAILABLE; alert ops
  Both classifiers fail:
    → Route to Taxonomy Review Queue; pipeline suspended for this signal

SYSTEM 3 — EMBEDDING FAILURES
  OpenAI embedding unavailable:
    → Fallback to local MiniLM (384-d); flag EMBEDDING_FALLBACK_LOCAL
  All embedding providers unavailable:
    → Hash-only deduplication; clustering skipped; flag EMBEDDING_UNAVAILABLE

SYSTEM 4 — LLM SYNTHESIS FAILURES
  GPT-4o unavailable:   → Anthropic Claude fallback (< 5 seconds)
  All LLM unavailable:  → Template synthesis; signal delivered; flag LLM_FAILED

DETERMINISTIC SYSTEMS (confidence, urgency, risk, recommendation):
  These have ZERO external dependencies.
  They never fail due to external service unavailability.
  They are always available.

HUMAN OPS QUEUES — OVERFLOW
  If any review queue exceeds 500 items:
    → Alert Intelligence Ops lead
    → Pipeline continues regardless (review is async)
    → Unreviewed signals delivered with lower confidence scores
```

---

---

*Document End — SC-DOC-005 AI/ML Orchestration Specification v1.0.0*
*Next Document: SC-DOC-008 Security & Compliance Specification*
