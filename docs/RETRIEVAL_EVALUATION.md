# Retrieval Evaluation Report

This report documents retrieval quality and out-of-domain rejection benchmarks for the AgentOS RAG system.

## Evaluation Dataset
- **Corpus**: 20 chunks across 5 academic domains (Machine Learning, DBMS, Operating Systems, Computer Networks, Algorithms).
- **Queries**: 32 total test queries:
  - 24 answerable domain-specific queries mapped to ground-truth expected chunks.
  - 8 unanswerable out-of-domain queries (e.g., sports, cooking, history, biological cellular mechanisms).

## Retrieval Quality Metrics
| Metric | Value | Detail |
|---|---|---|
| **Hit@1** | **100.0%** | Expected chunk ranked #1 |
| **Hit@3** | **100.0%** | Expected chunk within top 3 |
| **Hit@5** | **100.0%** | Expected chunk within top 5 |
| **MRR (Mean Reciprocal Rank)** | **1.0000** | Average reciprocal rank across answerable queries |
| **Abstention @ 0.65 Floor** | **100.0%** | Unanswerable queries rejected below similarity floor |

## Similarity Threshold Sweep
Empirical evaluation sweeping the similarity threshold from 0.50 to 0.80 in 0.05 steps:

| Threshold | Answerable Recall | Unanswerable Rejection | Tradeoff Observation |
|:---:|:---:|:---:|---|
| 0.50 | 100.0% | 12.5% | High recall, but allows out-of-domain queries to leak through. |
| 0.55 | 100.0% | 62.5% | High recall, but allows out-of-domain queries to leak through. |
| 0.60 | 100.0% | 100.0% | Balanced operating window with high recall and robust abstention. |
| 0.65 | 100.0% | 100.0% | Balanced operating window with high recall and robust abstention. |
| 0.70 | 100.0% | 100.0% | Balanced operating window with high recall and robust abstention. |
| 0.75 | 95.8% | 100.0% | Strict abstention, but causes false negatives on nuanced domain queries. |
| 0.80 | 83.3% | 100.0% | Strict abstention, but causes false negatives on nuanced domain queries. |

### Analysis of the 0.65 Similarity Floor
The current default similarity floor in AgentOS (`DOCUMENT_SEARCH_MIN_SIMILARITY=0.65`) achieves **100.0%** answerable recall while maintaining **100.0%** rejection of unanswerable queries on this evaluation corpus.

The sweep demonstrates the expected precision-recall tradeoff:
- Lowering the threshold to 0.50 increases false positives (only 12.5% unanswerable queries rejected).
- Raising the threshold to 0.80 causes false negatives (recall drops to 83.3%).
The threshold can be tuned in `backend/.env` via `DOCUMENT_SEARCH_MIN_SIMILARITY` to suit specific precision/recall priorities.
