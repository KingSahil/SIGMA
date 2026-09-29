# SignalForge — Web Frontend Features (plain-English list)

SignalForge is SIGMA's web lab. Everything below runs in a browser (Next.js). Here is
what it can actually do, in human words.

## 1. Load a signal
- Drag-and-drop a raw capture (`.iq`, `.bin`) or a sound recording (`.wav`).
- Or pick one of the built-in sample signals (satellite / UAV presets) to try instantly.
- It auto-detects the file format (complex64, float32, int16, PCM audio) and sample rate.

## 2. See the signal (live instruments)
- **Spectrum** — a power curve showing where the signal sits in frequency, with peak and bandwidth markers.
- **Waterfall** — the classic scrolling time-vs-frequency heatmap.
- **Constellation** — the I/Q scatter plot that reveals the modulation "shape," with a quality number (EVM).
- **3D Waterfall** — a more immersive time-frequency view (three.js).

## 3. Demodulate
- Choose the modulation family: BPSK, QPSK, 8PSK, 16QAM (64QAM in the simulator), plus 2-FSK / 4-FSK.
- Extracts the symbols and the real bitstream; one click copies the bits to your clipboard.

## 4. Undo interleaving
- Four scrambling schemes: block, convolutional, diagonal, pseudo-random.
- Set the matrix size (rows/columns) and watch bits reorder, with a before/after bit diff.

## 5. Fix errors (FEC)
- Decode with Viterbi, Reed-Solomon, concatenated, or LDPC.
- Shows errors corrected, leftover bit-error rate, and whether the frame checks out.

## 6. Hunt for the frame
- Slide a known sync word (Barker codes, CCSDS-style markers) across the bitstream to find the real message start.
- Auto-pulls the payload and shows it as hex and readable ASCII.

## 7. Hands-on teaching labs
- **Hamming (7,4) demo** — type 4 bits, flip one on "transmission," watch it get corrected live.
- **Error control lab** — parity, syndrome, step through the phases of error control.
- **Signal generator** — dial in modulation, noise, frequency offset, sample count, etc., and make a synthetic signal to test.
- **Intelligence workspace** — the main panel that runs a real capture through the live backend and shows the verdict.
- **Blockchain fingerprint** — compute a SHA-256 hash of a capture so you can prove it wasn't tampered with (registry/wallet step is planned, not live).
- **PDF comparison** — line up what a reference PDF claims about a signal vs. what SIGMA actually measured.

## 8. Ask the AI assistant
- A Gemini-powered chat that reads SIGMA's docs and your past analyses. Ask "why did it decline this signal?" and it answers with the evidence it used.

## 9. Two modes
- **Simulation (default)** — everything runs in your browser; no backend needed. Great for demos and learning.
- **Live** — connects to the real SIGMA backend at `localhost:8000` to analyze actual captures. A header toggle flips between them.

## 10. A guided pipeline
- A step-by-step flow (Input → Spectrum → Modulation → Demod → De-interleave → FEC → Correlate → Report) so you always know where you are.

---

### Honest notes (UI promise vs. live backend today)
- The simulator/types include **64QAM** and **K=7 Viterbi / RS(255,223) / CCSDS**. The actual
  SIGMA backend currently supports up to **16QAM** and **K=3 Viterbi** in live mode — those
  advanced options are fully exercised in **Simulation** but not yet wired to a live decoder.
- The blockchain **"anchor to registry"** step is a stub (UI only). Hashing works locally;
  wallet submission is not implemented.
