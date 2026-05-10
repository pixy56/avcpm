# Performance Baselines

| Operation | Baseline | Last Run | Trend | Alert Threshold |
|-----------|----------|----------|-------|-----------------|
| Graphify AST update | 5s | 5s | stable | >30s |
| Graphify semantic extract | 180s | 240s | worsening | >300s |
| Search index rebuild | 10s | 10s | stable | >60s |
| Wiki ingest (subagent) | 120s | 120s | stable | >180s |
| gog auth flow | 30s | 30s | stable | >60s |
| gog drive upload | 2s | 2s | stable | >10s |
| PDF generation | 10s | 10s | stable | >30s |

---

## Notes

- **Ollama Model Latency:** `qwen3.6:35b` is the current backend but takes **3–4 minutes** for semantic extraction. Consider a cloud LLM for time-sensitive operations.
