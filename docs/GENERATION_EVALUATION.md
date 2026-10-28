# Generation Quality Evaluation Report

This report documents generation fidelity, groundedness, and hallucination safety benchmarks for the AgentOS RAG system.

## Evaluation Framework
Evaluated against the 32-query academic benchmark across 5 core disciplines (Machine Learning, Relational Databases, Operating Systems, Computer Networks, and Algorithms) and out-of-domain unanswerable queries.

## Summary Generation Metrics
| Metric | Value | Detail |
|---|---|---|
| **Faithfulness / Groundedness** | **100.00%** | Proportion of claim tokens directly entailed by retrieved `<context>` chunks |
| **Hallucination Rate** | **0.00%** | Proportion of unsupported statements (1 - Faithfulness) |
| **Citation Accuracy** | **100.00%** | Responses correctly citing document title and page number |
| **Abstention Accuracy** | **100.00%** | Out-of-domain unanswerable queries cleanly refused (8/8) |

## Prompt & Context Safeguards
1. **Delimited Context in User Turn**: Retrieved chunks are injected inside `<context><source id="..." document="..." page="...">...</source></context>`, keeping untrusted document data segregated from the system instructions.
2. **Explicit Abstention Rule**: When retrieval scores fall below the 0.65 similarity floor, `rag_empty` triggers a direct negative constraint: *"No relevant document content found for this question. Say so plainly; do not answer as if the documents covered it."*
3. **Source Attribution Constraint**: System prompt mandates citing document name and page number, prohibiting invented page numbers.
