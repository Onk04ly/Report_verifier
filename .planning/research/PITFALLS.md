# Pitfalls Research

## Critical Pitfalls

1. **Silent Degradation**
- Warning signs: BERT load errors followed by continued execution.
- Prevention: hard-fail or explicit invalid-result flagging; surface degraded mode in outputs.
- Phase target: Phase 2.

2. **Config Drift**
- Warning signs: hardcoded thresholds in runtime modules.
- Prevention: centralize all tunables in `medical_config.py` and enforce usage in tests.
- Phase target: Phase 1.

3. **Brittle Safety Matching**
- Warning signs: paraphrased dangerous content passes checks.
- Prevention: hybrid semantic + rule-based safety detectors.
- Phase target: Phase 2.

4. **No Regression Net**
- Warning signs: risk outcomes change after edits without detection.
- Prevention: pytest coverage for risk boundaries, safety triggers, and scoring calculations.
- Phase target: Phase 3.

5. **Reproducibility Gaps**
- Warning signs: artifacts without generation metadata or hashes.
- Prevention: emit and track KB metadata (timestamp, query scope, model versions, hashes).
- Phase target: Phase 4.

---
*Generated: 2026-04-11*

