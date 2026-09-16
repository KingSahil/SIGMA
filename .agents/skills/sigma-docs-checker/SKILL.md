---
name: sigma-docs-checker
description: >-
  Use this skill to inspect, verify, and cross-reference SIGMA project documentation (architecture, data pipelines, workflow, technologies) against the actual codebase, check sample datasets, and ensure consistency across docs and code.
---

# SIGMA Project Documentation & Code Checker

This skill guides the agent and developers in inspecting, verifying, and maintaining technical documentation and codebase alignment for **SIGMA** (Signal Intelligence & Generalized Modulation Analyzer).

---

## 1. Documentation Map

All primary project documents live under the [`docs/`](file:///c:/Users/sahil/Downloads/gnu/docs/) directory:

| Document | File Path | Scope & Focus |
| :--- | :--- | :--- |
| **SIH Problem Statement** | [`docs/SIH_PROBLEM_STATEMENT.md`](file:///c:/Users/sahil/Downloads/gnu/docs/SIH_PROBLEM_STATEMENT.md) | Official NTRO SIH 6147 guidelines, evaluation criteria, and 5-stage pipeline specs. |
| **System Architecture** | [`docs/ARCHITECTURE.md`](file:///c:/Users/sahil/Downloads/gnu/docs/ARCHITECTURE.md) | 4-tier system architecture, module relations, threading model, and SIP bridge. |
| **Data Pipeline & Formats** | [`docs/DATA_PIPELINE_AND_FORMATS.md`](file:///c:/Users/sahil/Downloads/gnu/docs/DATA_PIPELINE_AND_FORMATS.md) | Complex float32 (`complex64`) byte layout, WAV stereo/mono conversion, decimation. |
| **Getting Started & Workflow**| [`docs/GETTING_STARTED_AND_WORKFLOW.md`](file:///c:/Users/sahil/Downloads/gnu/docs/GETTING_STARTED_AND_WORKFLOW.md) | Step-by-step launch commands, sample datasets, UI guide, and troubleshooting. |
| **Technologies & Tools** | [`docs/TECHNOLOGIES_USED.md`](file:///c:/Users/sahil/Downloads/gnu/docs/TECHNOLOGIES_USED.md) | GNU Radio 3.10, PyQt5, SIP, NumPy, SciPy, winsound, and Radioconda environment. |
| **Quickstart Guide** | [`README.md`](file:///c:/Users/sahil/Downloads/gnu/README.md) | Root repository overview and setup instructions. |

---

## 2. Standard Verification Procedure

When checking docs and code consistency, follow these steps:

### Step 1: Run Automated Consistency Checker
Execute the project verification script using Radioconda's Python interpreter:

```powershell
& "$env:USERPROFILE\radioconda\python.exe" .agents/skills/sigma-docs-checker/scripts/verify_docs_and_code.py
```

This script verifies:
1. **Sample Datasets Integrity**: Checks that all referenced `.iq` and `.wav` files exist in [`data/iq/`](file:///c:/Users/sahil/Downloads/gnu/data/iq/) and [`data/audio/`](file:///c:/Users/sahil/Downloads/gnu/data/audio/) and are readable.
2. **Module Imports**: Ensures `src.sigma_analyzer_core`, `src.sigma_flowgraph`, `src.sigma_main_window`, and `src.sigma_theme` can be cleanly imported without syntax or import errors.
3. **UI Label Alignment**: Compares button names in [`src/sigma_main_window.py`](file:///c:/Users/sahil/Downloads/gnu/src/sigma_main_window.py) against user instructions in [`docs/GETTING_STARTED_AND_WORKFLOW.md`](file:///c:/Users/sahil/Downloads/gnu/docs/GETTING_STARTED_AND_WORKFLOW.md).
4. **Link Health**: Validates relative file links between markdown documents.

### Step 2: Validate Data Pipelines
Verify that any changes to signal ingestion:
- Preserve raw `complex64` (8 bytes per sample: 4 real + 4 imag in little-endian).
- Support both 2-channel stereo IQ WAVs and 1-channel mono baseband WAVs.
- Correctly update duration ($T = N / f_s$) and sample counts ($N = \text{size} / 8$).

### Step 3: Check Architecture & Tier Boundaries
Ensure separation of concerns is maintained:
- **Presentation Tier** ([`src/sigma_main_window.py`](file:///c:/Users/sahil/Downloads/gnu/src/sigma_main_window.py), [`src/sigma_theme.py`](file:///c:/Users/sahil/Downloads/gnu/src/sigma_theme.py)): UI only; no raw DSP loops.
- **DSP Core** ([`src/sigma_analyzer_core.py`](file:///c:/Users/sahil/Downloads/gnu/src/sigma_analyzer_core.py)): Vectorized NumPy metrics; leaves uncalculated parameters as clean fallbacks (`--`).
- **Streaming Engine** ([`src/sigma_flowgraph.py`](file:///c:/Users/sahil/Downloads/gnu/src/sigma_flowgraph.py)): GNU Radio `top_block` streaming sinks; safe `lock()`/`unlock()` thread transitions.
