# SIGMA Development Rules & Guidelines

When working on the **SIGMA** repository:
1. **Always use Radioconda Python**: Run commands with `& "$env:USERPROFILE\radioconda\python.exe"`. Standard python does not include GNU Radio C++ bindings.
2. **Consult Project Documentation**: Primary architecture and specifications are documented in [`docs/`](file:///c:/Users/sahil/Downloads/gnu/docs/).
3. **Verify Compliance with SIH 6147**: Regularly check feature development status against the Smart India Hackathon problem statement requirements using `.agents/skills/sih-problem-auditor/SKILL.md`.
4. **Maintain Doc-Code Synchronization**: When modifying UI buttons, file formats, or DSP pipelines, run `.agents/skills/sigma-docs-checker/scripts/verify_docs_and_code.py` to ensure documentation and code remain in sync.
5. **Truth in Metrics**: Do not mock or fake signal analysis values. Real physical calculations should be implemented using NumPy, and uncomputed stages should fall back cleanly to `'--'`.
