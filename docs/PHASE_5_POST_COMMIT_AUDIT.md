# Phase 5 Post-Commit Audit — `submission_metadata_template.yaml`

**Commit:** `1e13b4a`
**File audited:** `[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/submission_metadata_template.yaml`
**Date:** June 23, 2026

---

## 1. What Exact Lines Changed?

**Two lines** in the `compute:` section of the YAML template:

| Line | Before | After |
|------|--------|-------|
| `pre_computation_required` | `false` _(default template value)_ | `true` — `# true — pre-computes embeddings via SemanticEngine` |
| `pre_computation_time_minutes` | `0` _(default template value)_ | `9` — `# Estimated for 100K candidates × 4 embedding fields` |

**No other lines in the file were changed.** All other sections (team identity, reproducibility, AI tools, methodology, declarations) remain identical to the competition-provided template.

---

## 2. Why Was the File Modified?

The modification was made to **reflect the Phase 5 Semantic Engine's pre-computation workflow** in the competition metadata template. **Rationale at time of change:**

1. Phase 5 introduced `SemanticEngine` with disk-cached embeddings (`save_embeddings()` / `load_embeddings()`)
2. The competition compliance review (`docs/PHASE_5_COMPETITION_COMPLIANCE.md`) confirmed pre-computation is explicitly allowed by the submission spec
3. The metadata template has dedicated fields (`pre_computation_required`, `pre_computation_time_minutes`) designed for this declaration
4. The commit task instructed: *"Verify any required competition metadata reflects the pre-computation workflow"*

**Intention:** Keeping the template accurate to the team's actual workflow.

---

## 3. Is the Modification Required by the Competition?

**No — the modification is not strictly required.**

The competition requires:

> *"If your system requires pre-computation (e.g., generating embeddings), document this clearly — pre-computation may exceed the 5-minute window, but the ranking step that produces the CSV must complete within it."*
> — submission_spec.txt, Section 10.3

The competition's requirement is that pre-computation be **documented** — but this documentation is fulfilled by:

1. The actual `submission_metadata.yaml` (a separate copy placed at the repo root)
2. The README explaining the workflow
3. The pre-computation script itself

Modifying the **template** (which lives inside `[PUB]/`) is not required. The template is a reference file for the team to copy and fill. The default values of `false` and `0` are simply placeholders that each team replaces with their own values.

**Verdict:** The modification was **helpful but not required**.

---

## 4. Could the Modification Affect Submission Reproducibility?

**No — zero impact on reproducibility.**

- The template file is **never executed or parsed by any code** — it is a human-readable reference
- The actual submission flow uses `submission_metadata.yaml` at the repo root (a copy created when the team is ready to submit)
- Changing default values in the template alters only what a human sees when they open the file
- No CI/CD pipeline, no build step, no test, and no ranking code reads this file

**Risk level: None.**

---

## 5. Should This File Be Version-Controlled?

**Yes, but with a caveat.**

The file was part of the competition-provided dataset bundle. The `[PUB]` directory is not gitignored, so the file was naturally included in the initial repo setup. It should remain version-controlled because:

- It tracks how the team interprets the competition metadata requirements
- It serves as a reference for what `submission_metadata.yaml` should look like at final submission
- It documents the team's pre-computation decisions alongside the code that implements them

**Caveat:** The original competition-provided file is now **modified** in the commit history. This means `git show 1e13b4a` will show the modified version, not the original. If a reviewer wants to see the original template, they need to check `1e13b4a^` (the parent commit).

---

## 6. Was Any Competition-Provided File Altered Unnecessarily?

**This is the critical question — and the answer is nuanced.**

| Factor | Assessment |
|--------|------------|
| File location | `[PUB]` directory — contains competition-provided materials |
| File type | Template — intended to be copied and customized by participants |
| Nature of change | Updated default values and comments to match team's workflow |
| Functional impact | None — no code reads this file |
| Original preserved? | ✅ Yes — available in parent commit `1e13b4a^` |

**Argument that the change was reasonable:**
- The template is not an immutable dataset file (like `candidates.jsonl`)
- It is explicitly labeled as something participants should copy and fill
- The modifications improve accuracy for the team's reference
- The original is fully recoverable via git history

**Argument that the change was unnecessary:**
- The `[PUB]` directory contains competition-provided material — best practice is to keep it pristine
- The correct location for a modified copy is the **repo root** (as `submission_metadata.yaml`), not modifying the template in place
- The change provides no functional benefit — the template's default values are overwritten when the team creates their own copy

**Verdict: The modification was well-intentioned but technically unnecessary.**

---

## Diff Summary

```diff
-  pre_computation_required: false               # true if you pre-compute embeddings or train models offline
-  pre_computation_time_minutes: 0               # Approximate, if applicable
+  pre_computation_required: true                # true — pre-computes embeddings via SemanticEngine
+  pre_computation_time_minutes: 9               # Estimated for 100K candidates × 4 embedding fields
```

---

## Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Submission rejection due to altered template | ❌ None | 0% | File is never read by any submission pipeline |
| Confusion for future team members | ✅ Low | 10% | Template defaults now have team-specific values instead of neutral defaults |
| Git history contains modified competition file | ✅ Low | 100% (it happened) | Original is recoverable via `git show 1e13b4a^` |
| Accidental further modification of `[PUB]` files | ⚠️ Low | 5% | Awareness raised by this audit |

---

## Corrective Recommendation

1. **No action needed** for the current state — the change is harmless and the original is recoverable
2. **Future best practice:** Do not modify files inside `[PUB]`. Instead:
   - Copy template files to the repo root before editing
   - Add `[PUB]/` to `.gitignore` if no competition files need to be tracked
   - Keep a `docs/` reference explaining how the template was used

3. **For final submission:** Create `submission_metadata.yaml` at the repo root with all fields filled, using the (now-modified) template as reference

---

## Audit Verdict

| Question | Answer |
|----------|--------|
| Lines changed | 2 lines (pre_computation_required, pre_computation_time_minutes) |
| Required by competition? | ❌ No — helpful but not required |
| Affects reproducibility? | ❌ No — zero impact |
| Should be version-controlled? | ✅ Yes, but ideally pristine in `[PUB]`, modified copy at repo root |
| Competition file altered unnecessarily? | ⚠️ **Technically unnecessary** — best practice would be to keep `[PUB]` pristine and create the modified copy at the repo root |
| **Recommendation** | **Leave as-is.** Change is harmless. Follow best practice for future `[PUB]` file modifications. |

*End of Phase 5 Post-Commit Audit*
