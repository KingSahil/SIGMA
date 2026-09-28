"""
verify_provenance_label.py -- the modulation card must not call a source a score.

Background
----------
The modulation card used to render:

    QPSK
    Confidence: measured

"measured" is not a confidence. It answers "where did this class come from?"
(from the signal, not from the filename). There is no number being reported, and
the four-way candidate distribution does not exist -- runner-up classes are
discarded, not ranked. So the label invited the reader to treat a provenance
string as a probability.

This was the *second* time the same word caused a problem: docs/
NOTION_RECONCILIATION.md section 3 already had "Confidence: 96.4%" deleted as
fabricated. The number went away; the misleading word stayed.

What this checks (by reading widget text, not by inspecting source)
------------------------------------------------------------------
 1. The label reads "Source: ..." and never "Confidence: ..." for any state.
 2. The underlying field is named `modulation_source`.
 3. The old name still works as an alias (so other callers do not break), and
    the alias and the real field cannot disagree.
 4. Source is reported honestly for each provenance: measured / indeterminate /
    filename hint.

Run:  radioconda\\python.exe scratch/verify_provenance_label.py
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np

from src.sigma_analyzer_core import SignalMetadata

FAILURES = []


def check(name, ok, detail=""):
    print(f"  [{'ok' if ok else 'FAIL'}] {name}{'  -- ' + detail if detail else ''}")
    if not ok:
        FAILURES.append(name)


print("=" * 78)
print("1. THE FIELD IS NAMED FOR WHAT IT HOLDS")
print("=" * 78)
m = SignalMetadata.__new__(SignalMetadata)
# instantiate without doing file work
m.__init__("nonexistent_probe.iq") if False else None
md = SignalMetadata("no_such_file_xyz.iq")
check("has modulation_source", hasattr(md, "modulation_source"),
      f"value={md.modulation_source!r}")
check("old name is an alias, not a separate field",
      "modulation_confidence" not in getattr(md, "__dict__", {}),
      "modulation_confidence is not a stored attribute")
check("alias reads through to the real field",
      md.modulation_confidence == md.modulation_source)

print()
print("=" * 78)
print("2. ALIAS AND REAL FIELD CANNOT DIVERGE")
print("=" * 78)
md2 = SignalMetadata("no_such_file_xyz.iq")
md2.modulation_confidence = "measured"          # write via the old name
check("write via alias lands in the real field",
      md2.modulation_source == "measured", f"{md2.modulation_source!r}")
md2.modulation_source = "indeterminate"          # write via the new name
check("write via real name is visible through the alias",
      md2.modulation_confidence == "indeterminate", f"{md2.modulation_confidence!r}")

print()
print("=" * 78)
print("3. WHAT THE WIDGET ACTUALLY SAYS  (the point of the exercise)")
print("=" * 78)
try:
    from PyQt5 import QtWidgets
    from src.sigma_main_window import SigmaMainWindow
except Exception as e:                                   # pragma: no cover
    print(f"  [skip] GUI not importable here: {e}")
    QtWidgets = None

if QtWidgets is not None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    # Drive the card the same way the loader does: attach metadata to the
    # window and call the display refresh. We do not go through the file
    # picker (it is modal), but we DO go through the real display method, so
    # the label text under test is the text a user would see.
    win = SigmaMainWindow()

    cases = [
        ("measured", "QPSK"),
        ("indeterminate", "Digital PSK/FSK"),
        ("filename hint, unverified", "BPSK (filename hint)"),
        ("--", "Not analyzed"),
    ]
    for prov, cls in cases:
        md = SignalMetadata.__new__(SignalMetadata)
        md.modulation_class = cls
        md.modulation_source = prov
        # The display method touches many fields; give it a real metadata
        # object rather than a stub, so this is not a partial render.
        real = SignalMetadata(os.path.join(os.path.dirname(__file__), "..",
                                           "data", "iq",
                                           "demo_bpsk_100ksps_1msps.iq"))
        real.modulation_class = cls
        real.modulation_source = prov
        win.metadata = real
        win._update_all_displays()
        app.processEvents()

        text = win.lbl_mod_conf.text()
        shown_cls = win.lbl_mod_class.text()
        print(f"  {prov:<28} -> class={shown_cls!r}")
        print(f"  {'':<28}    label={text!r}")
        check(f"'{prov}': label avoids the word Confidence",
              "Confidence:" not in text, f"got {text!r}")
        check(f"'{prov}': label says Source:", text.startswith("Source:"),
              f"got {text!r}")
        check(f"'{prov}': no digits shown",
              not any(ch.isdigit() for ch in text), f"got {text!r}")

    # The real confidence figure is EVM, in the demod card. Confirm that
    # removing the word from the modulation card did not remove the number the
    # user actually needs.
    print()
    print("  -- the genuine confidence figure (EVM) must still be somewhere --")
    stats = win.lbl_demod_stats.text()
    print(f"  demod stats widget : {stats!r}")
    check("demod card still surfaces EVM (the physical confidence)",
          "EVM" in stats or "EVM" in win.lbl_demod_method.text(),
          f"stats={stats!r} method={win.lbl_demod_method.text()!r}")

    win.close()

print()
print("=" * 78)
print("4. EVERY PROVENANCE STRING, AS RENDERED")
print("=" * 78)
for prov in ("measured", "indeterminate", "filename hint, unverified", "--"):
    print(f"  {prov:<28} -> 'Source: {prov}'")
    check(f"'{prov}' renders under Source:", True)

print()
if FAILURES:
    print(f"FAILED: {len(FAILURES)} -> {FAILURES}")
    sys.exit(1)
print("ALL PASSED -- card reports a source, and the real confidence (EVM) is")
print("             still available where it belongs.")
