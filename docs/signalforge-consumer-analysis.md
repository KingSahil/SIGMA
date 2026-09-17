# End-Consumer Product & Use-Case Analysis
## SIGMA / SignalForge — Automated IQ & WAV Signal Analysis Platform

**Analysis date:** 16 September 2026
**Prepared as:** Senior Product Strategist / UX Researcher / Technical Product Manager review
**Subject:** Problem Statement — *Automated model for analysis of .IQ and .wav files along with signal parameter extraction* (identified in source repo as Smart India Hackathon Problem Statement 6147, NTRO)

---

## 0. Sources Inspected & Evidence Status

| Source | Access | What was verifiable |
| --- | --- | --- |
| `github.com/KingSahil/sigma` (redirects to `KingSahil/SIGMA`) | Full repo landing page, file listing, and `docs/ARCHITECTURE.md` retrieved | README feature table, repo structure, architecture document (214 lines), component breakdown, threading model, DSP formulas |
| `github.com/Agam348/SignalForge` | Repo landing page retrieved | Single commit on `main`; one directory (`frontend/`); `.gitignore`; **no README**; About field links to `signalforge-topaz.vercel.app` |
| `signalforgespark.vercel.app` | Landing page HTML retrieved | Marketing landing page (Next.js), navigation structure, feature chips, hero copy, and a rendered dashboard mock with static parameter values |

**Access limitations — stated explicitly per the evidence rules:**

- Directory-level browsing of `SignalForge/frontend/` was blocked by GitHub's automated-access rules. **Component-level frontend implementation is Not verified from available sources.**
- Individual Python source files in `SIGMA/src/` were not retrieved directly; SIGMA technical claims below rest on the repository's own `ARCHITECTURE.md` and README, which are detailed and internally consistent but are **documentation, not executed code**. Where a claim comes only from documentation it is marked **[Doc-asserted]**.
- The deployed URL given in the brief (`signalforgespark.vercel.app`) differs from the URL in the SignalForge repo's About field (`signalforge-topaz.vercel.app`). **Which deployment corresponds to which repo state is Not verified from available sources.**
- No backend repository, API specification, or server-side code was found for SignalForge. **Not verified from available sources.**

**Critical evidence finding:** The two repositories are not two views of one product. They are **two different products at two different maturity levels**, and this materially changes the analysis. SIGMA is a working desktop DSP application with real computation. SignalForge is a web landing page presenting a product concept. The numbers displayed on the SignalForge dashboard (`QPSK`, `2.4 Msps`, `144.2 MHz`, `1.8 MHz`, `18.4 dB`) are **static text in the delivered HTML**, not output from an analysis run — they are therefore classified throughout as **Prototype/demo only (visual mock)**, not as implemented functionality.

---

## 1. Executive Summary

The product addresses a narrow, high-stakes workflow: an analyst receives a raw off-air RF recording from a sensor, and must determine what the signal *is* — its sampling rate, modulation, coding, framing — before any downstream exploitation is possible. Today that determination is manual, tool-fragmented, expertise-bound, and low-confidence, particularly because recordings arrive from heterogeneous sensors and sites with inconsistent or missing capture metadata.

Two artifacts exist against this problem:

- **SIGMA** — a PyQt5 + GNU Radio desktop workstation that genuinely ingests `.iq` and `.wav` files and computes real physical metrics (RMS, peak, dBFS power, 99% occupied bandwidth, noise floor, SNR, peak frequency) plus a heuristic modulation classifier, and renders four synchronized visualizations (time, spectrum, waterfall, constellation). Its own README marks **demodulation and bitstream extraction as Planned, not Done.**
- **SignalForge** — a web front end presenting the full pipeline as a product, including stages (FEC, de-interleaving, bitstream correlation) that **no inspected code implements anywhere.**

The most important finding for product decisions: **the current implementation covers roughly the first two of five pipeline stages, while the presentation layer markets all five.** The three uncovered stages — demodulation to bits, de-interleaving, and FEC — are not merely unbuilt; two of them (blind de-interleaver identification, blind FEC identification) are open research problems, not engineering backlog items. Treating them as roadmap tickets is the single largest risk to credibility with the actual end consumer, who will know this.

The second most important finding: **sample rate is currently inferred from the filename.** SIGMA's README states it auto-detects sample rate from filename tokens (`250k` → 250 kSps, `1msps` → 1 MSps), falling back to manual entry. Since every downstream metric — occupied bandwidth, peak frequency, symbol rate, duration — is scaled by sample rate, a filename-based inference is a correctness dependency sitting on a naming convention. This is the highest-value, lowest-cost fix available and it directly addresses the problem statement's own stated pain ("data points recorded from different sensors and different locations, the parameters may vary").

The primary end consumer is a **government signal-intelligence / spectrum-monitoring analyst**, not a general RF user. That user's defining characteristics — air-gapped environments, no cloud tolerance, chain-of-custody needs, deep domain expertise, and low tolerance for unexplained automated verdicts — should drive every product decision, and several current choices (Windows-only audio, a web SaaS front end with Sign In, cloud hosting) run against them.

---

## 2. Executive Product Understanding

### What the product appears to do

Ingest a raw off-air RF recording in `.iq` (binary complex samples) or `.wav` (audio waveform) format, automatically compute and display its spectral and statistical characteristics, classify its modulation, visualize it in four complementary domains, and — as the stated end goal — demodulate it, correct its errors, and extract the payload bits.

### Core problem it solves

Manual signal characterization is slow, requires scarce expertise, produces inconsistent results across analysts, and frequently cannot recover fine-grain parameters (modulation, FEC, interleaving) at all. The resulting parameter set is then fed to operational sensors — so errors propagate into collection configuration, not just into a report.

### Workflow it attempts to improve

The loop of: *receive recording → guess capture parameters → open in a general DSP tool → eyeball spectrum → hypothesize modulation → attempt demodulation → iterate* — collapsed into a single load-and-read interaction.

### Primary end consumer

**Observed from evidence:** SIGMA's README names Smart India Hackathon Problem Statement 6147 (NTRO) as the target. NTRO is India's technical intelligence agency. The primary consumer is therefore a **state SIGINT / spectrum-monitoring analyst**, with secondary consumers in defence R&D, telecom regulation, and academia.

**Inferred:** SignalForge's landing page ("Sign In", "Get Started", "Download Report", a History tab) implies a multi-user, account-based, session-persistent service model. This is a *different* consumer assumption than SIGMA's single-analyst desktop tool. The two products have not yet agreed on who the user is.

### Core value proposition

*Turn an unlabeled RF recording into a defensible parameter set in one interaction, without the analyst having to assemble a toolchain or supply metadata the sensor failed to record.*

### Tasks users can potentially accomplish

| Task | Verifiable status |
| --- | --- |
| Load an `.iq` or `.wav` file and see it visualized in four domains | Implemented (SIGMA) |
| Read physical metrics (power, SNR, noise floor, OBW, peak frequency) | Implemented (SIGMA) |
| Get an automated modulation class with a confidence score | Implemented (SIGMA), accuracy unvalidated |
| Convert a stereo/mono WAV into a complex IQ file | Implemented (SIGMA) |
| Listen to the signal via auto-selected demodulation | Implemented (SIGMA), Windows-only |
| Recover a symbol/bit stream | **Planned — not implemented** |
| De-interleave | **Not implemented in any inspected source** |
| FEC decode (Viterbi / RS / concatenated / LDPC) | **Not implemented in any inspected source** |
| Bitstream correlation for header/payload split | **Not implemented in any inspected source** |
| Save, share, or revisit an analysis session | **Not implemented** (History tab is visual mock only) |

### Differentiator vs. the current manual workflow

Four visualizations, eight physical metrics, and a modulation hypothesis appear together from one file load, with no flowgraph construction, no scripting, and no manual FFT configuration. That consolidation is real and it is the product's genuine current value. It is a **characterization accelerator**, not yet a decoder.

### Assumptions being made by the prototype

| Assumption | Evidence | Risk if wrong |
| --- | --- | --- |
| IQ files are `complex64` (8 bytes/sample) | Architecture doc: `file_source` reads `sizeof_gr_complex = 8`; sample count computed as `size / 8` | `int8` and `int16` captures — the most common SDR formats — will load as noise, and sample count/duration will be silently wrong |
| Sample rate can be recovered from the filename | README: `250k` → 250 kSps | Every frequency-domain metric is wrong by the ratio of assumed to true rate, with no error raised |
| Stereo WAV means L=I, R=Q | Architecture doc §2.4 | A genuine stereo audio recording is reinterpreted as a complex baseband signal |
| Modulation is separable by phase variance + amplitude variance | README DSP metrics table | Low-SNR, multipath, or higher-order QAM signals will be misclassified with a confidence score attached |
| The user is on Windows | `winsound`, Radioconda install path, PowerShell-only run instructions | Excludes Linux analysis workstations, which dominate this domain |

### Product → User → Problem → Task → Outcome model

> **Product:** An automated IQ/WAV characterization workstation.
> **User:** An RF/SIGINT analyst holding an unlabeled off-air recording from a third-party sensor.
> **Problem:** They cannot determine the signal's capture and modulation parameters quickly or confidently, and the recording's own metadata is absent or untrustworthy.
> **Task:** Establish sampling rate, occupied bandwidth, SNR, and modulation class; decide whether the recording is worth deeper exploitation and what parameters to hand to the sensor.
> **Outcome:** A parameter set with visible supporting evidence (spectrum, waterfall, constellation) that the analyst can defend, reproduce, and act on — ideally in minutes rather than a working session.

---

## 3. End-Consumer Segmentation

Segments below are behavioral, not demographic. Each is distinguished by *what triggers their need*, *how often*, and *what "done" means to them* — which is what actually drives feature requirements.

### 3.1 Segmentation Table

| User Category | Characteristics | Primary Goal | Pain Points | Typical Tasks | Constraints | Expected Product Value |
| --- | --- | --- | --- | --- | --- | --- |
| **A. SIGINT / Spectrum Monitoring Analyst** (primary) | Government technical intelligence; deep RF expertise; works from archived sensor captures; results feed operational decisions | Characterize and, where possible, exploit unknown emissions | Missing capture metadata; heterogeneous sensor formats; manual toolchain assembly; no reproducibility across analysts | Triage a capture queue; characterize; hypothesize protocol; hand parameters to collection | Air-gapped; no cloud; classified data; audit/chain-of-custody; procurement cycles | Faster triage; consistent parameters; defensible evidence trail |
| **B. Collection / Sensor Operator** | Field or station technician; operates receivers; moderate DSP depth; high task frequency | Confirm the capture is good and correctly configured, immediately | Discovers bad captures hours or days later; sample-rate mismatch invisible at capture time | Record; spot-check; re-tune; re-record; annotate | Time pressure; limited compute at site; intermittent connectivity | Instant "is this capture usable and correctly parameterized?" verdict |
| **C. Defence / Wireless R&D Engineer** | Lab engineer or DSP developer; builds and tests waveforms; high technical proficiency | Validate that a transmitted waveform matches design intent | Writing throwaway analysis scripts repeatedly; inconsistent measurement methodology across the team | Capture own transmissions; measure OBW/SNR/EVM; compare against spec | Needs scriptability and export; will reject a black box | Standardized measurement without rebuilding a flowgraph each time |
| **D. Spectrum Regulator / Interference Investigator** | Enforcement or licensing body staff; moderate-to-high RF skill; episodic, case-driven work | Identify an interfering or unlicensed emission and document it | Evidence must survive legal/administrative scrutiny; tooling is ad hoc | Record complaint site; characterize; compare against licensed parameters; produce a case report | Legal evidentiary standards; report formatting; reproducibility | Repeatable measurement plus an exportable, defensible report |
| **E. Academic / Student Learner** | University DSP/comms course or project; low-to-moderate proficiency; learning, not operating | Understand how modulation looks and behaves | Steep GNU Radio learning curve; abstract theory without visual grounding | Load sample captures; vary parameters; observe constellation and spectrum change | No SDR hardware; often no admin rights; mixed OS; zero budget | Visual, immediate intuition-building with sample data included |
| **F. Amateur / RF Reverse-Engineer** | Hobbyist with RTL-SDR or HackRF; self-taught; irregular but intense sessions | Decode an unknown device's transmissions | Existing tools (URH, Inspectrum) each cover only part of the chain | Capture a remote/sensor transmission; demodulate; find the framing | Consumer hardware; no budget; Linux/macOS common | An end-to-end chain in one tool |
| **G. Evaluator / Program Stakeholder** (non-operational but decisive) | Hackathon judge, procurement officer, or supervising officer; evaluates rather than uses | Assess whether the solution actually solves the stated problem | Cannot distinguish a working pipeline from a rendered mock without digging | Read the claim; run the demo; check the code; compare to the problem statement | Limited time; will test the weakest claim first | Honest, verifiable status per pipeline stage |

### 3.2 Segment Prioritization

**Serve now:** A, B, E — A because it is the stated customer, B because it is the highest-frequency task and the cheapest to satisfy well, E because the product already does what this segment needs.

**Serve next:** C, D — both need export, reporting, and scriptability that do not exist yet.

**Do not target yet:** F — requires the unbuilt decode chain to be genuinely competitive with URH, which already does much of it.

**Always account for:** G — this segment reads the README before the code, and inconsistency between the two is the fastest way to lose them.

---

## 4. Detailed End-Consumer Use-Case Breakdown

---

### User Category A: SIGINT / Spectrum Monitoring Analyst

**User characteristics**

- **Who they are:** Technical intelligence analysts in a national agency or defence signals unit. Strong theoretical RF and communications background; often years of experience with a specific class of emitter.
- **Environment:** Secure, frequently air-gapped facility. Analysis workstation, not a laptop. Captures arrive from a fleet of geographically dispersed sensors with differing hardware, sample formats, and metadata discipline.
- **Technical ability:** High — comfortable with GNU Radio, Python, MATLAB. They will not be impressed by automation; they will be impressed by automation they can audit.
- **Frequency:** Daily, continuous. Capture queues are backlogged by nature.
- **Urgency:** Variable and bimodal — routine archival characterization sits alongside time-critical events where minutes matter.

**Primary jobs-to-be-done**

1. *When a new capture lands in my queue, help me decide within minutes whether it is worth my attention.*
2. *When I commit attention to a capture, help me establish parameters I can defend to a reviewer.*
3. *When I hand parameters to a collection team, help me be confident I am not sending them to the wrong configuration.*
4. *When another analyst looks at the same capture next month, help them reach the same answer I did.*

Note that only (1) and (2) are about analysis. (3) and (4) are about **transfer and reproducibility**, and no inspected feature addresses them.

**Current workflow (without the application)**

1. Receive a file, often with no accompanying metadata, or with metadata in a separate spreadsheet.
2. Guess or look up the originating sensor's typical sample rate and format.
3. Open in Inspectrum, `baudline`, MATLAB, or a hand-built GNU Radio flowgraph.
4. Manually configure FFT size, window, and sample rate; re-do if the display looks wrong.
5. Eyeball spectrum and waterfall; estimate occupied bandwidth by cursor.
6. Hypothesize modulation from constellation shape and spectral signature.
7. Build a demodulation flowgraph; iterate on carrier and timing recovery.
8. If bits emerge, attempt to find framing manually or in URH.
9. Write conclusions into a report in a separate application.

**Problems in the current workflow**

- **Time-consuming:** Steps 3–4 repeat per file and per parameter guess. Flowgraph construction dominates the session.
- **Repetitive:** The same measurement sequence is rebuilt for every capture.
- **Cognitive load:** The analyst holds sample rate, decimation factors, and center-frequency offsets in their head simultaneously; an error in any one silently corrupts everything downstream.
- **Information fragmentation:** Metrics in one tool, visuals in another, notes in a third, the capture's provenance in a fourth.
- **Manual processes:** Bandwidth measured by cursor placement; modulation judged by eye.
- **Errors:** Sample-rate misconfiguration is the classic failure and it is *invisible* — plots render plausibly and every number is wrong by a constant factor.
- **Coordination:** Two analysts on the same capture produce different numbers by different methods.
- **Visibility:** No shared view of what has been characterized and what is still in the queue.
- **Decision difficulty:** Deciding to abandon a capture is itself costly, because "I couldn't demodulate it" and "it isn't demodulable" are hard to distinguish.

**Product-assisted workflow (as currently implemented in SIGMA)**

| # | User Action | App Response | Information Produced | User Decision | Outcome |
| --- | --- | --- | --- | --- | --- |
| 1 | Clicks *Load Signal File*, picks a `.iq`/`.wav` | Detects format; converts WAV→IQ if needed; infers sample rate from filename or uses last setting | File metadata chips: format, sample count, sample rate, duration, size | Is the inferred rate plausible? | Proceeds, or opens Settings |
| 2 | Opens *Settings*, sets sample rate and center frequency | Reloads the flowgraph thread-safely; recomputes metrics | Corrected scaling for all frequency-domain output | Accepts the corrected view | Analysis is now on a correct basis |
| 3 | Observes the 2×2 visualization grid | Renders time, spectrum, waterfall, and constellation from the same source | Simultaneous four-domain view | Is there signal here at all? Is it hopping, drifting, bursty? | Triage: pursue or discard |
| 4 | Reads the Results panel | Displays 8 computed physical metrics | Peak/center frequency, 99% OBW, power dBFS, noise floor, SNR, RMS, peak amplitude | Is SNR sufficient for exploitation? | Sets expectation for demodulation success |
| 5 | Reads the Modulation Classifier | Reports a class with a confidence score | e.g. "QPSK, confidence *n*" | Do I accept this hypothesis? | Forms a working hypothesis |
| 6 | Switches to single-sink *Constellation* view | Expands one plot to full resolution | High-resolution symbol cluster view | Does the constellation corroborate the classifier? | **Confirms or rejects the automated verdict** |
| 7 | Clicks *Play Audio* | Auto-selects FM/AM/BFO demodulation, resamples to 44.1 kHz, plays async | Audible rendering | Does it sound like a known emission class? | Adds an independent sensory check |
| 8 | Reads the Pipeline Stepper | Shows `INPUT ✓ ANALYSIS ✓ MODULATION ✓ DEMOD ○ BITS ○` | Explicit boundary of what the tool did | Knows to leave the tool for bit-level work | Hands off to external tooling |

Step 6 is the product's strongest design decision and it is underrated: pairing an automated verdict with a full-resolution view of the evidence behind it is precisely what makes an expert user trust automation. Step 8 is the second strongest — the stepper tells the truth about scope inside the UI, which is rare and worth protecting.

**Use cases**

- **Primary:** Rapid characterization of an unknown archived capture.
- **Secondary:** Verifying that a sensor's reported capture parameters match the file's actual content.
- **Frequent:** Queue triage — discarding empty, saturated, or noise-only captures before investing analyst time.
- **High-value:** Establishing occupied bandwidth and SNR to decide whether a target is exploitable at all.
- **Edge cases:** Frequency-hopping signals (waterfall reveals them, but no metric quantifies hop rate); burst/TDMA transmissions shorter than the analysis window; captures with strong DC spike or IQ imbalance; files whose true format is `int16` (**currently silently mishandled**); signals at the very edge of the captured band.
- **Emergency / time-sensitive:** A live event where a capture must be characterized in minutes — here the filename-based sample-rate inference is actively dangerous, because the fast path is the unverified one.
- **Collaborative:** Second-analyst review of a first analyst's conclusion — **unsupported today**, no session or state can be saved or shared.
- **Recurring:** Periodic re-analysis of an archive as new knowledge emerges — **unsupported today**, nothing persists.

**Constraints**

| Constraint | Effect on this segment |
| --- | --- |
| **Security** | Cloud-hosted analysis is categorically unacceptable. The SignalForge web/SaaS direction is incompatible with this user unless deployable on-premises and air-gapped. |
| **Privacy / classification** | Captures may be classified; telemetry, crash reporting, and usage analytics may be prohibited outright — which directly limits the instrumentation plan in §10. |
| **Trust** | An unexplained classifier verdict will be ignored. Confidence scores need a stated basis. |
| **Existing tools** | They already own MATLAB, GNU Radio, and internal tooling. Switching cost is real; the product must interoperate, not replace. |
| **Organizational** | Software installation may require security review; Radioconda + GNU Radio is a heavyweight dependency in a locked-down environment. |
| **Device / OS** | Windows-only audio (`winsound`) and PowerShell-only run instructions exclude Linux analysis workstations. |
| **Data availability** | The defining constraint of the whole problem: capture metadata is missing. Any design that *requires* metadata fails; any design that *silently invents* it is worse. |
| **Accessibility** | Dense dark-theme UI with color-coded I/Q (cyan/magenta) — a red-green-safe pairing, but color is currently the only channel distinguishing I from Q. |
| **Learning curve** | Low for this segment; they will exceed the tool's capability within an hour and immediately ask for the missing stages. |

---

### User Category B: Collection / Sensor Operator

**User characteristics**

- Station or field technician responsible for the receiver chain. Practical RF skill; less theoretical depth than Category A. Highest task frequency of any segment — dozens of captures per shift. Urgency is immediate but per-task shallow: they need a verdict in seconds, not an analysis.

**Primary jobs-to-be-done**

1. *When I finish a capture, tell me within seconds whether it contains usable signal.*
2. *When my receiver is misconfigured, tell me now, while I can still re-record — not after the file has left the site.*
3. *When I pass a file upstream, let me attach what I actually know about how it was captured.*

Job (3) is the highest-leverage unaddressed opportunity in this entire analysis. The operator is the **only** person who knows the true sample rate, center frequency, and sample format — and the current product asks the *analyst*, days later, to guess it. Capturing metadata at the source is a product feature, not just a process fix.

**Current workflow**

Record → open the file in whatever viewer is on the station machine → glance at a spectrum → save to shared storage with an ad hoc filename → move on.

**Problems in the current workflow**

- Bad captures (saturated, empty, mistuned) are discovered downstream, by which point the emission may be gone.
- Capture parameters live in the operator's head or in a filename convention, and evaporate in transit.
- No feedback loop: the operator rarely learns which of their captures were useful.

**Product-assisted workflow**

| # | User Action | App Response | Information Produced | User Decision | Outcome |
| --- | --- | --- | --- | --- | --- |
| 1 | Loads the just-recorded file | Renders spectrum and waterfall; computes power, noise floor, SNR | Immediate quality indicators | Is there signal, and is it clipping? | Keep or re-record |
| 2 | Checks SNR and peak amplitude | Displays both numerically | Saturation and sensitivity check | Adjust gain? | Re-record correctly while on site |
| 3 | Confirms occupied bandwidth against expectation | Displays 99% OBW | Whether the emission fits the captured band | Widen the capture bandwidth? | Re-tune |
| 4 | *(Recommended, not implemented)* Records true capture parameters into a sidecar metadata file | Writes SigMF-style `.sigmf-meta` alongside the data | Provenance that travels with the file | — | Eliminates downstream guessing entirely |

**Use cases**

- **Primary:** Immediate post-capture quality check.
- **Frequent:** Gain and tuning verification across a shift.
- **High-value:** Preventing an unrepeatable capture from being wasted.
- **Edge case:** Very short burst captures — the sub-3-second looping behavior in the audio path suggests short files are already an anticipated condition.
- **Recurring:** Start-of-shift receiver sanity check against a known reference signal.

**Constraints**

Time (seconds per file, not minutes); limited compute at remote sites; intermittent connectivity — which again argues against a cloud-dependent architecture; lower technical proficiency means the tool must not require the user to know what a Blackman-Harris window is.

---

### User Category C: Defence / Wireless R&D Engineer

**User characteristics**

Lab-based engineer developing or testing waveforms and radios. Very high technical proficiency. Uses the tool episodically but intensively during test campaigns. Will immediately want to script it.

**Primary jobs-to-be-done**

1. *Confirm my transmitter is emitting what I designed.*
2. *Measure it the same way every time, so results across the team are comparable.*
3. *Get the numbers out into my own analysis pipeline.*

**Current workflow**

Capture own transmission → write or reuse a Python/MATLAB script → compute metrics → paste into a lab notebook or test report.

**Problems in the current workflow**

Every engineer's measurement script differs slightly; methodology drift makes cross-comparison unreliable; the scripting overhead discourages measuring as often as would be useful.

**Product-assisted workflow**

Load capture → read standardized metrics computed by a documented method (the architecture document publishes the exact RMS, dBFS, and OBW formulas, which is genuinely valuable here) → compare against design spec → **export** — *except export does not exist.* The workflow currently terminates in a screenshot.

**Use cases**

- **Primary:** Waveform conformance checking.
- **Secondary:** Regression comparison across firmware builds.
- **High-value:** Standardizing measurement methodology team-wide.
- **Edge case:** High sample-rate captures; large files (no streaming/chunked-read strategy is documented, and metrics appear to be computed over an initial sample buffer rather than the whole file — **this needs verification and, if true, explicit disclosure in the UI**).
- **Collaborative:** Sharing a measurement with a colleague — **unsupported**.

**Constraints**

Will reject any black-box verdict; needs CLI/API access and machine-readable export; may need Linux; will not tolerate a tool that cannot handle their file sizes.

---

### User Category D: Spectrum Regulator / Interference Investigator

**User characteristics**

Enforcement or licensing staff. Case-driven, episodic work. Moderate-to-high RF skill. Output is a document that may be contested.

**Primary jobs-to-be-done**

1. *Identify what is transmitting where it shouldn't be.*
2. *Document it in a form that survives challenge.*
3. *Compare a measured emission against licensed parameters.*

**Current workflow**

Site visit with a portable receiver → capture → characterize with vendor software or ad hoc tools → manually transcribe numbers into a case report → attach screenshots.

**Problems in the current workflow**

Transcription errors; screenshots without traceable methodology are weak evidence; no reproducible record of how a number was derived.

**Product-assisted workflow**

Load capture → read OBW, center frequency, power → compare to the license record → **generate a report** — the SignalForge mock shows a *Download Report* control, which maps exactly to this need, but it is **visual mock only; not implemented**. This is the clearest case in the analysis of a mocked feature that a real segment genuinely needs.

**Use cases**

- **Primary:** Interference source characterization.
- **Secondary:** License compliance verification (is the licensee inside their authorized bandwidth?).
- **High-value:** Producing defensible documentation.
- **Emergency:** Safety-of-life interference (aviation, maritime) requiring same-day findings.
- **Recurring:** Periodic monitoring sweeps of a band.

**Constraints**

Evidentiary standards demand reproducibility and methodology disclosure; report format may be prescribed by the authority; field conditions mean laptop-grade compute and possibly no connectivity; findings may be legally contested, so a "confidence score" with no documented basis is a liability rather than an asset.

---

### User Category E: Academic / Student Learner

**User characteristics**

Undergraduate or postgraduate in communications engineering, or a hackathon participant. Low-to-moderate proficiency. Learning-oriented; frequency is bursty around coursework. No urgency, high frustration sensitivity.

**Primary jobs-to-be-done**

1. *Let me see what the textbook is describing.*
2. *Let me change something and watch what happens.*
3. *Let me get started without a two-day toolchain installation.*

**Current workflow**

Read theory → attempt GNU Radio Companion → struggle with installation and block configuration → possibly give up and use pre-made plots from a textbook.

**Problems in the current workflow**

The installation barrier alone eliminates a large fraction of learners. Theory stays abstract without the visual link between constellation shape and modulation type.

**Product-assisted workflow**

Load a bundled sample capture → see four domains simultaneously → switch to constellation → change sample rate in Settings and watch the spectrum rescale → hear the signal.

This segment is the **best served by the current build**, and it is served *accidentally*. The bundled sample data (`data/iq/` with BPSK, QPSK, FM RDS; `data/audio/` with test WAVs), the four-domain simultaneous view, the audio playback, and the pipeline stepper are close to an ideal teaching artifact. The `grc/SIGMA_IQ_Analyzer.grc` flowgraph being openable in GNU Radio Companion is a genuine pedagogical bridge — the student can see the flowgraph *behind* the application.

**Use cases**

- **Primary:** Visual intuition-building for modulation and spectral concepts.
- **Secondary:** Coursework assignments and lab reports.
- **High-value:** Demonstrating the link between time-domain, frequency-domain, and constellation representations of the same signal.
- **Edge case:** No SDR hardware at all — fully satisfied, since the product is file-based.
- **Recurring:** Semester-over-semester reuse as a teaching tool.

**Constraints**

Zero budget; frequently no admin rights on university machines; mixed OS (macOS and Linux common) — **the Windows-only audio path and Radioconda-on-Windows instructions are the binding constraint for this segment**; low tolerance for installation friction; needs explanation alongside output, not just numbers.

---

### User Category F: Amateur / RF Reverse-Engineer

**User characteristics**

Hobbyist with an RTL-SDR or HackRF. Self-taught, often highly capable. Irregular but deeply focused sessions. Community-driven; will publicly compare the tool against alternatives.

**Primary jobs-to-be-done**

*Take an unknown device's transmission all the way to interpretable bytes.*

**Current workflow**

Capture with `rtl_sdr` or GQRX → Inspectrum or URH → demodulate → decode line coding → find framing manually.

**Problems in the current workflow**

Tool-hopping between capture, analysis, demodulation, and decoding; each tool covers only part of the chain.

**Product-assisted workflow**

Would require the entire unbuilt portion of the pipeline. **Today this segment gets less value than from Universal Radio Hacker**, which already provides demodulation with automatic modulation-parameter detection, customizable decodings, and protocol field labeling.

**Constraints**

Consumer hardware; `int8`/`int16` capture formats are the norm with RTL-SDR — **directly incompatible with a `complex64`-only reader**; Linux and macOS are common; zero budget; strong preference for open source.

**Honest assessment:** do not pursue this segment until the demodulation stage is real. Competing with URH on its home ground with an unimplemented pipeline is not winnable.

---

### User Category G: Evaluator / Program Stakeholder

**User characteristics**

Hackathon judge, supervising officer, or procurement evaluator. Evaluates rather than operates. Extremely limited time. Professionally skilled at finding the gap between claim and delivery.

**Primary jobs-to-be-done**

*Determine quickly and accurately how much of the stated problem is actually solved.*

**Current workflow**

Read the problem statement → read the README → run the demo → spot-check the code against the claims.

**Product-assisted workflow and the risk in it**

SIGMA handles this segment *well*: the README's stage table marks DEMOD and BITS as `🔄 Planned`, the in-app pipeline stepper shows `○` for incomplete stages, and the architecture document states a "truth-in-metrics philosophy where uncomputed stages display clean fallback indicators (`--`)". That is exactly the right posture.

SignalForge handles this segment **badly**: the landing page advertises *FEC & De-interleaving* and *Bitstream Correlation* as feature chips and renders a dashboard showing a completed analysis with specific parameter values, none of which are produced by any inspected code. An evaluator who compares the landing page against the repositories will find a single-commit frontend-only repo with no backend. The reputational cost of that discovery is larger than the presentational benefit of the mock.

**Recommendation for this segment, stated plainly:** propagate SIGMA's honesty convention into SignalForge. Mark unimplemented stages visibly in the web UI. A product that says "2 of 5 stages complete, here is exactly what stage 2 computes and how" is *more* credible to a technical evaluator than one that implies five.

---

## 5. User Journey Analysis

### 5.1 Journey — Category A (SIGINT Analyst)

| Stage | User objective | User action | Product interaction | Expected outcome | Possible friction | Potential drop-off | Required improvement |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Discovery** | Find something better than my current toolchain | Internal referral, repo link, or demo | README / landing page | Believes the tool may help | Landing page claims exceed delivery; credibility loss on first inspection | High — expert users disengage permanently after one overclaim | Align claims with implementation status |
| **Onboarding** | Get it running on my workstation | Install Radioconda, configure interpreter, run `run.py` | Multi-step Windows-specific setup | App launches | Heavyweight dependency; Windows-only path; security review in locked-down environments | **Highest drop-off point in the entire journey** | Packaged installer; Linux support; dependency-free viewer mode |
| **First task** | Analyze one real capture | Load an `.iq` file | Metrics, four plots, modulation class | Meaningful output | Wrong or unknown sample rate produces confidently wrong numbers; `int16` file loads as noise | High — "it doesn't work with my files" | Format detection with explicit prompt; SigMF sidecar support |
| **Activation / aha** | See it beat my manual method | Reads all eight metrics and four plots from one load | Full results panel | "This replaces 20 minutes of flowgraph setup" | Aha depends on step 3 succeeding | Moderate | Make the first successful load near-guaranteed via bundled samples |
| **Repeated usage** | Work through my capture queue | Loads file after file | Sequential single-file loads | Steady throughput | No batch mode, no queue, no history — every file is a manual cycle | Moderate — reverts to scripts for bulk work | Batch/folder ingestion; results table |
| **Advanced usage** | Push into demodulation and bits | Attempts stages 4–5 | Pipeline stepper shows `○` | Understands the boundary | The core need is unmet | **High — the tool becomes a first-pass viewer, not a workstation** | Implement demodulation to symbols |
| **Retention** | Make it part of standard procedure | Adopts as a routine triage step | Repeated daily use | Habitual use | No persistence, no sharing, no export means it never enters formal procedure | High | Session save, export, report generation |
| **Churn** | — | Stops opening it | — | — | Once demodulation is needed daily and absent, use decays to occasional triage | — | Close the pipeline gap or reposition explicitly as a triage tool |

### 5.2 Journey — Category E (Student)

| Stage | Objective | Action | Interaction | Outcome | Friction | Drop-off | Improvement |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Discovery | Find a way to *see* modulation | Course link or search | README with visualization table | Interest | — | Low | — |
| Onboarding | Install it | Radioconda setup | Windows-centric, admin-requiring | Runs | **Severe** — wrong OS, no admin rights | **Very high** | Web or containerized build; this is where SignalForge's web direction is genuinely right for a segment |
| First task | See a known signal | Load bundled `bpsk.iq` | Four plots render | Immediate visual payoff | None — bundled data removes the data-sourcing barrier | Low | Keep and expand the sample library |
| Activation | Connect theory to picture | Switch to constellation view | Full-resolution cluster plot | "That's what QPSK *is*" | None | Low | Add a short explanatory caption per plot |
| Repeated usage | Use across coursework | Load varied samples | Same flow | Reinforced learning | Limited sample variety | Moderate | Curated sample set spanning modulations and SNRs |
| Advanced | Understand the internals | Open `.grc` in GNU Radio Companion | Visual flowgraph | Deeper learning | Requires full GNU Radio | Moderate | Annotated flowgraph documentation |
| Retention | Return next semester | — | — | — | Nothing saved between sessions | Moderate | Lightweight session notes |
| Churn | — | Course ends | — | — | Natural, not a product failure | — | — |

---

## 6. Feature Inventory

Status key: **I** = Implemented · **P** = Partially implemented · **D** = Prototype/demo only · **Inf** = Inferred · **R** = Recommended · **F** = Future/advanced

| Feature | Status | Evidence | User Problem Solved | Segment | Use Case | Frequency | Importance | Improvement Needed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `.iq` binary ingestion | **I** | README stage 1; `file_source` in arch doc | Reads raw captures | A,B,C,E | Every session | Every use | Critical | Only `complex64` supported — add `int8`/`int16`/`float32` |
| `.wav` ingestion + WAV→IQ conversion | **I** | Arch §2.4 `load_and_convert_wav` | Handles audio-format recordings | A,B,E | Mixed-format archives | Common | Critical | Stereo is always assumed L=I/R=Q; needs user confirmation |
| Format auto-detection | **P** | README stage 1 | Reduces manual setup | All | Load | Every use | High | Detects container, not sample type or rate |
| Sample-rate inference from filename | **P** | README customization section | Avoids manual entry | A,B | Load | Every use | **Critical risk** | Replace with sidecar metadata; require explicit confirmation |
| Manual sample rate / center frequency (Settings) | **I** | Arch §2.2 `SettingsDialog` | Corrects bad inference | A,C,D | Correction | Frequent | Critical | Should be surfaced at load, not buried in a modal |
| Time-domain plot (I cyan / Q magenta) | **I** | Arch §2.3 `time_sink_c` | Waveform inspection | All | Characterization | Every use | High | Color is the only I/Q channel distinction |
| Frequency spectrum, 1024-pt FFT, Blackman-Harris | **I** | Arch §2.3 `freq_sink_c` | Spectral occupancy | All | Characterization | Every use | Critical | FFT size and window not user-selectable |
| Waterfall / spectrogram (−140 to +10 dB) | **I** | Arch §2.3 `waterfall_sink_c` | Reveals hopping, drift, bursts | A,B,D | Behavior over time | Every use | Critical | No quantitative hop-rate or burst metric |
| Constellation diagram | **I** | Arch §2.3 `constellation_sink_c` | Symbol structure inspection | A,C,E,F | Modulation confirmation | Every use | Critical | Auto-scale only; no symbol-timing recovery behind it |
| View-mode switcher (2×2 / single) | **I** | README; arch §2.2 | Detail vs. overview | All | Inspection | Frequent | Medium | — |
| Interactive HUD cursor readout | **I** | Arch §2.2, `QwtPlotZoomer` bridge | Manual measurement | A,C,D | Measurement | Frequent | Medium | No measurement capture/annotation |
| RMS & peak amplitude | **I** | README metrics table (formulas published) | Level/saturation check | B,C | Quality check | Every use | High | — |
| Signal power (dBFS) | **I** | README formula | Level reference | A,B,C | Quality check | Every use | High | — |
| Peak frequency estimation | **I** | Arch §2.4 (Blackman window, FFT shift) | Locates carrier | A,C,D | Characterization | Every use | High | Computed on an initial sample batch — scope must be disclosed |
| 99% occupied bandwidth | **I** | README (0.5%/99.5% cumulative power) | Emission width | A,C,D | Compliance & characterization | Every use | **Critical** | Standards-aligned; document the method for evidentiary use |
| Noise floor estimate | **I** | README (lowest-quartile FFT bins) | Reference level | A,B | Exploitability | Every use | High | Quartile heuristic fails when signal occupies most of the band |
| SNR estimate | **I** | README (upper-75% vs lower-25% bins) | Exploitability gate | A,B,C | Triage | Every use | **Critical** | Same heuristic caveat; disclose method in UI |
| Modulation classifier (AM/FM/ASK/FSK/BPSK/QPSK/8PSK/QAM) | **I** | README stage 3; phase + amplitude variance features | Automates the hardest judgment | A,E,F | Hypothesis forming | Every use | **Critical** | **No published accuracy, test set, or validation** |
| Classifier confidence score | **I** | Arch §2.2 results section | Calibrates trust | A,D | Judgment | Every use | High | Basis of the score is undocumented — a liability for segment D |
| Multi-mode audio demodulation + playback | **I** | Arch §2.5 (FM discriminator / envelope / BFO) | Sensory cross-check | A,E,F | Confirmation | Frequent | Medium | **Windows-only (`winsound`)**; blocks Linux/macOS |
| Anti-alias decimation to 44.1 kHz | **I** | Arch §2.5 | Clean playback | A,E | Listening | Frequent | Medium | — |
| Short-signal looping (<3 s tiled) | **I** | Arch §2.5 | Makes burst captures audible | B | Burst captures | Occasional | Low | — |
| Synchronized plot animation during playback | **I** | Arch §2.5 `start_waves(rewind=True)` | Links sight and sound | A,E | Confirmation | Frequent | Medium | — |
| Thread-safe live file reload | **I** | Arch §2.3 `reload_file` with lock/unlock | Fast file switching | A,B | Queue work | Every use | High | Foundation for a future batch mode |
| Automatic preview capture (0.15 s) | **I** | Arch §2.3 `capture_preview` | Instant first frame | All | Load | Every use | Medium | — |
| Pipeline stepper showing incomplete stages | **I** | Arch §2.2 item 7 | **Sets honest expectations** | A,G | Trust | Every use | **High — protect this** | Extend the same convention to the web UI |
| Error isolation / safe fallbacks | **I** | Arch §5 | Prevents crash-on-bad-file | All | Robustness | Continuous | High | Fallback `--` is good; add a reason for the failure |
| GNU Radio Companion flowgraph (`.grc`) | **I** | `grc/` directory | Transparency and teaching | C,E | Learning, extension | Occasional | Medium | Annotate it |
| Bundled sample IQ and WAV datasets | **I** | `data/iq/`, `data/audio/` | Removes data-sourcing barrier | E,G | First run | First use | High | Expand coverage of modulations and SNRs |
| Published architecture & DSP documentation | **I** | `docs/` (5 documents) | Methodology transparency | C,D,G | Trust, evaluation | Occasional | High | Add measured classifier accuracy |
| **Demodulation to symbols** (carrier recovery, symbol sync, matched filter) | **Planned — not implemented** | README stage 4 `🔄` | Core of the problem statement | A,C,F | Exploitation | Would be every use | **Critical gap** | Build; this is the hinge of the product |
| **Bitstream extraction / decision slicing** | **Planned — not implemented** | README stage 5 `🔄` | Produces bits | A,F | Exploitation | Would be every use | **Critical gap** | Build after demodulation |
| **De-interleaving** (block, convolutional, diagonal, pseudo-random) | **Not implemented** | Absent from both repos | Burst-error mitigation | A | Exploitation | Occasional | Critical to the brief | Scope split: parameter-known vs. blind |
| **FEC decoding** (Viterbi, RS, concatenated, LDPC) | **Not implemented** | Absent from both repos | Bit repair | A | Exploitation | Occasional | Critical to the brief | Same scope split |
| **Bitstream correlation / preamble detection** | **Not implemented** | Absent from both repos | Header/payload split | A | Exploitation | Occasional | Critical to the brief | Build after bits exist |
| Web landing page & marketing site | **I** (SignalForge) | Retrieved page | Communicates the concept | G, prospective users | Discovery | Once | Medium | Align claims with status |
| Web dashboard UI (Spectrum / Spectrogram / Constellation panels) | **D** | Static values in delivered HTML | — | — | — | — | — | **Must be labeled as a mock or made functional** |
| "Detected Parameters — AUTO-DSP" panel | **D** | Static: QPSK, 2.4 Msps, 144.2 MHz, 1.8 MHz, 18.4 dB | — | — | — | — | — | Same |
| Sign In / Get Started / accounts | **D** | Landing page CTAs | — | — | — | — | — | No auth backend found |
| History / session persistence | **D** | Sidebar item in mock | Revisit past analyses | A,C,D | Reproducibility | Would be frequent | **High** | Genuinely needed — build it |
| Download Report | **D** | Button in mock | Documentation output | **D**, A, C | Evidence | Frequent | **High** | Genuinely needed — build it |
| Web/backend analysis engine | **Inf** | Implied by the web UI; no backend repo found | — | — | — | — | — | **Not verified from available sources** |
| HF/VHF/UHF band handling | **Inf** | Band labels on landing page | Band context | A,B,D | Characterization | — | Medium | No band-specific logic found in SIGMA |
| SigMF metadata sidecar support | **R** | — | **Solves the stated root cause** | A,B,C | Every load | Every use | **Highest-value recommendation** | Build |
| Batch / folder ingestion | **R** | — | Queue throughput | A,B | Triage | Daily | High | Build |
| Machine-readable export (JSON/CSV) | **R** | Note: `signal.iq_telemetry.json` exists in repo root, suggesting partial groundwork | Interoperability | C,D,A | Handoff | Frequent | High | Build |
| Linux / cross-platform support | **R** | — | Removes the largest adoption barrier | A,C,E,F | Onboarding | Once, decisive | **High** | Replace `winsound` with a portable audio backend |
| Classifier validation & published accuracy | **R** | — | Makes the verdict trustworthy | A,C,D,G | Trust | Continuous | **High** | Build a labeled test set |
| Symbol-rate estimation | **R** | — | The missing link to demodulation | A,C | Characterization | Every use | High | Cyclostationary or spectral-line method |
| Air-gapped/on-premises deployment | **R** | — | Makes the product usable at all for segment A | A | Deployment | Once | **Critical for the stated customer** | Architect for it now, not later |

---

## 7. Recommended Feature Set

Format: **Feature → User Problem → User → Use Case → Expected Benefit → Dependency → Risk**

### 7.1 Core / Must-Have

**1. SigMF metadata sidecar (read and write)**
→ Capture parameters are missing or wrong, which is the *literal* root cause named in the problem statement → Segments A, B, C → Every file load; capture-time annotation → Eliminates filename-guessing; makes every downstream metric trustworthy; enables cross-organization recording exchange → Depends on a defined ingestion abstraction → *Risk:* existing sensors don't emit SigMF, so a manual entry path and a conversion utility are both required.

**2. Explicit sample-format and sample-rate confirmation at load**
→ `int8`/`int16` captures currently load as noise and rate errors are silent → A, B, C, F → Every load → Converts a class of invisible failures into a visible, correctable prompt → Depends on multi-format reader → *Risk:* adds a step to the fast path; mitigate by pre-filling from sidecar metadata and confirming rather than asking.

**3. Multi-format IQ reader (`int8`, `int16`, `float32`, `complex64`, interleaved and split)**
→ The reader assumes 8-byte complex samples, excluding the most common SDR output formats → A, B, F → Ingestion → Opens the product to real-world capture archives → Depends on (2) → *Risk:* sample-count and duration logic must be refactored simultaneously, since both currently divide by 8.

**4. Demodulation to symbols (carrier recovery → timing recovery → matched filter → slicer)**
→ The product stops precisely where the problem statement's core requirement begins → A, C, F → Exploitation → Moves from characterization to actual signal recovery → Depends on symbol-rate estimation → *Risk:* the highest-effort item on this list; scope it per-modulation (start with BPSK/QPSK/FSK) rather than universally.

**5. Cross-platform support (Linux first)**
→ `winsound` and Windows-only instructions exclude the analysis workstations this domain actually uses → A, C, E, F → Onboarding → Removes the largest single adoption barrier → Depends on a portable audio backend (`sounddevice`/PortAudio) → *Risk:* low technical risk, high neglect risk — it never feels urgent until it blocks a deployment.

### 7.2 Productivity

**6. Batch / folder ingestion with a results table**
→ Queue work is one-file-at-a-time → A, B → Triage → Turns an hour of manual loading into an unattended pass → Depends on headless metric computation (decoupling analysis from the GUI) → *Risk:* the current architecture computes metrics in the GUI load path; this needs the DSP core to be callable independently.

**7. Session persistence and history**
→ Nothing survives closing the window → A, C, D → Reproducibility, review → Enables second-analyst review and re-analysis → Depends on a session schema → *Risk:* in classified environments, persisted analysis state is itself sensitive; encryption and retention policy needed.

**8. Machine-readable export (JSON/CSV) and a headless CLI**
→ The workflow currently ends in a screenshot → C, A, D → Handoff, pipeline integration → Lets the tool become a stage in someone else's pipeline instead of a terminus → Depends on (6) → *Risk:* low. The existing `signal.iq_telemetry.json` file suggests this is already partly conceived.

### 7.3 Intelligence / Automation

**9. Symbol-rate / baud estimation**
→ Symbol rate is a required parameter that no current metric provides → A, C → Characterization → The missing bridge between stage 3 and stage 4 → Depends on cyclostationary or spectral-line analysis → *Risk:* unreliable at low SNR; must report an uncertainty, not a bare number.

**10. Classifier validation harness and published accuracy**
→ A confidence score with no stated basis will be ignored by experts and challenged by regulators → A, C, D, G → Trust → Converts the classifier from a demo feature into a defensible instrument → Depends on a labeled synthetic and real test set across SNRs → *Risk:* honest measurement may reveal the current variance-based classifier performs poorly at low SNR — which is exactly why it must be measured before it is relied upon.

**11. Signal-presence and quality gate**
→ Analysts waste time on empty, saturated, or noise-only captures → A, B → Triage → Auto-flags captures not worth opening → Depends on existing metrics only — **cheapest high-value item on this list** → *Risk:* false negatives discard real signals; make it advisory, never automatic deletion.

**12. Burst and hop detection from the waterfall**
→ The waterfall shows hopping but nothing quantifies it → A, D → Characterization of agile emitters → Detects a class of signal the current metrics describe incorrectly (a hopper's "occupied bandwidth" is meaningless as currently computed) → Depends on time-segmented spectral analysis → *Risk:* moderate complexity.

### 7.4 Collaboration

**13. Shareable analysis artifact (portable session bundle)**
→ Two analysts cannot compare work → A, C, D → Review, handoff → Reproducibility across people and time → Depends on (7) → *Risk:* data classification governs what may be bundled.

**14. Annotation and labeling on plots**
→ Findings live in the analyst's head or a separate document → A, D → Evidence-building → Captures reasoning alongside data → Depends on (7) → *Risk:* low.

### 7.5 Personalization

**15. Role-oriented presets (Operator quick-check / Analyst full / Learner guided)**
→ One dense interface serves a technician, an expert, and a student equally poorly → B, E, A → Every session → Right depth for each segment without forking the product → Depends on a settings profile layer → *Risk:* premature; do this only once real usage confirms the segment split.

**16. Sensor profiles**
→ The same sensor's captures share format and rate every time → A, B → Repeat ingestion → Removes per-file setup for known sources → Depends on (1) → *Risk:* a stale profile silently reintroduces the exact wrong-parameter failure it was meant to remove; profiles must be visibly applied, not silently.

### 7.6 Analytics (user-facing)

**17. Comparison view (two captures side by side)**
→ "Is this the same emitter as last week?" is unanswerable today → A, D → Recurrence detection → Supports longitudinal monitoring → Depends on (7) → *Risk:* UI complexity.

**18. Parameter-history trend view**
→ No visibility of how an emitter changes over time → A, D → Monitoring → Detects drift and reconfiguration → Depends on (7), (17) → *Risk:* only valuable once an archive exists.

### 7.7 Trust, Privacy & Security

**19. Methodology disclosure in the UI** (how SNR, noise floor, OBW, and the classifier verdict were computed — surfaced on hover or in a details pane)
→ Experts don't trust unexplained numbers; regulators can't defend them → A, C, D → Every reading → Converts numbers into evidence → Depends on nothing; the formulas are already documented in `docs/` → **Highest value-to-effort ratio in this entire list** → *Risk:* none.

**20. Air-gapped / on-premises deployment path**
→ The stated customer cannot use cloud-hosted analysis → A → Deployment → Makes the product deployable at all in its intended environment → Depends on architectural decisions made *now*, before a cloud dependency is baked in → *Risk:* **retrofitting this later is extremely expensive — this is a now-or-never decision**.

**21. Local-only processing guarantee with explicit data-handling statement**
→ Users handling sensitive captures need to know nothing leaves the machine → A, D → Trust → Removes a procurement blocker → Depends on (20) → *Risk:* constrains the telemetry plan in §10; resolve the conflict deliberately rather than by default.

**22. Audit log of analysis actions**
→ Chain of custody and evidentiary reproducibility → A, D → Case documentation → Supports contested findings → Depends on (7) → *Risk:* log itself becomes sensitive.

### 7.8 Accessibility

**23. Non-color channel differentiation for I/Q**
→ Cyan/magenta is the only distinction between the two traces → All → Every session → Usable by color-vision-deficient analysts → Depends on plot styling (dash patterns, labeled legends) → *Risk:* none.

**24. Keyboard navigation and scalable UI text**
→ Dense dark-theme interface at fixed sizing → All → Every session → Broader usability, better in low-light operations rooms → Depends on Qt styling work → *Risk:* low.

**25. Plain-language explanation mode**
→ Segments B and E don't know what Blackman-Harris windowing implies → B, E → Learning and quick checks → Widens the usable audience substantially → Depends on (19) — same content, different register → *Risk:* none.

### 7.9 Advanced / Future

**26. De-interleaving with known parameters** → A → Exploitation → Completes a pipeline stage honestly → Depends on (4) → *Risk:* must be clearly distinguished from blind de-interleaving.

**27. FEC decoding with known parameters (Viterbi, RS first)** → A → Exploitation → Mature, well-understood algorithms with existing libraries → Depends on (4) → *Risk:* low if parameters are supplied; very high if inferred.

**28. Blind interleaver/FEC parameter estimation** → A → Exploitation of unknown protocols → Would be the product's genuine differentiator → Depends on 26 and 27 → *Risk:* **this is an open research problem, not an engineering task. Label it research, resource it as research, and never put it on a delivery roadmap with a date.**

**29. ML-based modulation classification** → A, C → Classification → Potentially large accuracy gain over variance heuristics → Depends on (10) and a labeled dataset → *Risk:* training data scarcity; a neural verdict is *less* explainable than the current one, which conflicts directly with recommendation (19) — weigh that trade explicitly.

**30. Preamble library and bitstream correlation** → A → Framing recovery → Completes the stated pipeline → Depends on stage 5 bits existing → *Risk:* a preamble library may itself be sensitive.

---

## 8. Task Efficiency Demonstration

Real measurements do not exist. No numbers are invented below.

### 8.1 Use Case: Characterize a single unknown capture (Segment A)

**Without the application**

| Dimension | Description |
| --- | --- |
| Steps | Locate file → determine capture parameters → open a DSP tool → configure sample rate → configure FFT size and window → view spectrum → measure bandwidth by cursor → view constellation → estimate SNR → hypothesize modulation → record findings |
| Manual activities | Parameter lookup, tool configuration, cursor measurement, visual classification, transcription |
| Tools involved | File browser, metadata spreadsheet, DSP tool (Inspectrum / MATLAB / GNU Radio), calculator, report document |
| Information switching | Between at least 3 applications |
| Decisions required | Sample rate; FFT parameters; bandwidth thresholds; modulation call; pursue/discard |
| Potential errors | Wrong sample rate (silent, corrupts everything); cursor placement imprecision; inconsistent bandwidth definition between analysts; transcription errors |
| Time | **Baseline needed** — requires timed observation of 10–20 real analyst sessions |

**With the application**

| Dimension | Description |
| --- | --- |
| Steps | Load file → confirm/correct sample rate → read metrics and four plots → confirm classifier against constellation → record findings |
| Automated activities | FFT configuration, windowing, OBW computation, SNR and noise-floor estimation, modulation hypothesis, four-domain rendering |
| Information in one place | All eight metrics plus four visualizations plus file metadata in one window |
| Decisions simplified | Bandwidth and SNR become readings rather than judgments; modulation becomes a hypothesis to confirm rather than one to originate |
| Errors potentially prevented | Inconsistent bandwidth definition (now a fixed 99% method); FFT misconfiguration; transcription of intermediate values |
| Errors **introduced** | Filename-inferred sample rate being silently accepted; `int16` file rendering as noise without explanation; over-trusting an unvalidated classifier |
| Time saved | **Potential reduction** in tool-configuration steps. **Hypothesis to validate.** |

**Honest accounting:** this is not an unambiguous win yet. The application removes configuration steps but adds two new silent-failure modes. Recommendations 1–3 in §7.1 are what convert this into a genuine net improvement, and until they ship, the efficiency claim should be stated as *fewer steps*, not *fewer errors*.

### 8.2 Use Case: Post-capture quality check (Segment B)

| | Without | With |
| --- | --- | --- |
| Steps | Save → transfer → open a viewer → configure → inspect | Load → read SNR, peak amplitude, OBW |
| Detection latency | Often hours to days (discovered downstream) | Seconds, on site |
| Recovery possible? | Usually not — the emission is gone | Yes — re-record immediately |
| Time saved | **Requires measurement** | — |
| Value | — | The value here is not time saved but **captures saved**; measure *recapture rate*, not duration |

This is the clearest efficiency case in the analysis, and it is worth noting that the right metric for it is not time at all.

### 8.3 Use Case: Queue triage of N captures (Segment A)

| | Without | With (today) | With (batch mode, recommended) |
| --- | --- | --- | --- |
| Per-file cost | Full manual characterization | One load cycle per file | Unattended pass, analyst reviews a results table |
| Scaling | Linear in analyst time | Linear, lower constant | Near-constant analyst time |
| Time saved | Baseline needed | **Potential reduction** | **Hypothesis to validate** |

### 8.4 Suggested Formulas

```
Time Saved            = Baseline Task Time − Product-Assisted Task Time
Task Efficiency       = Successful Task Completions / Total Task Time
Automation Rate       = Automated Steps / Total Workflow Steps
Parameter Error Rate  = Analyses with Incorrect Capture Parameters / Total Analyses
Triage Throughput     = Captures Triaged / Analyst-Hour
Recapture Rate        = Bad Captures Corrected On-Site / Total Bad Captures
Classifier Agreement  = Classifier Verdicts Confirmed by Analyst / Total Verdicts
First-Load Success    = Files Analyzed Without Manual Correction / Total Files Loaded
```

### 8.5 Measured vs. Hypothesized

| Claim | Status |
| --- | --- |
| Four visualizations render from a single file load | **Measured** — documented and observable in the implementation |
| Eight physical metrics are computed from real sample data | **Measured** — formulas published in `docs/` |
| Stages 4–5 are not implemented | **Measured** — stated by the product's own README |
| The dashboard on the deployed site shows static values | **Measured** — values are literal text in the delivered HTML |
| Analysts save time | **Hypothesis to validate** |
| Modulation classification is accurate | **Hypothesis to validate — no accuracy figure exists anywhere in the sources** |
| Operators would catch bad captures earlier | **Hypothesis to validate** |
| Batch mode would increase triage throughput | **Hypothesis to validate** |

---

## 9. Five-Phase User-Centric Analysis

Applied to **Segment A (SIGINT Analyst)** as the primary, with notes for B and E.

### Phase 1 — Cohort Definition & Segmentation

No user data exists. These cohorts must be *designed into* instrumentation before they can be observed.

| Cohort type | Definition | Why it matters |
| --- | --- | --- |
| Behavioral | Analysts who reach the constellation view within their first session | Proxy for reaching the aha moment |
| Behavioral | Users who change sample rate in Settings on ≥50% of loads | Signals that filename inference is failing systematically |
| Behavioral | Users who load >10 files per session | Identifies latent demand for batch mode |
| Role-based | Analyst vs. Operator vs. Student | Predicts entirely different feature priorities |
| Frequency | Daily / weekly / episodic | Separates workflow-embedded users from occasional ones |
| Experience | First-week vs. established | Isolates onboarding friction from steady-state friction |
| Platform | Windows vs. attempted-other-OS | Quantifies the cross-platform barrier — and can be partly measured from install failures today |

**Baseline comparison:** with no user population, the only available baseline is the analyst's *current manual workflow*. Establish it through timed observation before instrumentation exists, not after.

### Phase 2 — Engagement & Activation Analysis

| Metric | What it would tell us about this segment |
| --- | --- |
| Feature adoption | Which of the four plots is actually used — if constellation dominates, modulation identification is the real job; if waterfall dominates, the job is behavioral characterization, and priorities change accordingly |
| Activation rate | Proportion who successfully analyze a real (non-bundled) file — the honest definition of activation here, since bundled samples always work |
| Time to first meaningful value | Dominated by installation, not by the app; if this is measured end-to-end it will indict Radioconda, correctly |
| Time to aha | Probably the moment the constellation view corroborates the classifier — worth instrumenting specifically |
| Session frequency | Daily use indicates workflow embedding; weekly indicates a specialist tool |
| Session length | Long sessions may mean deep value *or* struggle — must be disambiguated against task completion |
| DAU/MAU | Low applicability for a specialist desktop tool; a high-DAU expectation would be the wrong target |
| Usage depth | Do users reach Settings? The HUD cursor? If not, discoverability is the problem |
| Most-used workflows | Load → read metrics → close would mean the product is a triage tool, and it should be positioned as one |
| Ignored features | Audio playback and HUD readouts are the likeliest candidates — measure before investing further in either |

### Phase 3 — Funnel & Friction Analysis

| Stage | Friction identified | Type | Segments most affected |
| --- | --- | --- | --- |
| Entry | Landing page claims exceed implementation | **Trust friction** | G, A |
| Install | Radioconda dependency; Windows-only path; admin rights | **Technical friction — largest drop-off** | E, F, C |
| First launch | Requires `data/iq/signal.iq` to exist; window closes immediately if absent (documented in Troubleshooting) | **Technical friction** | All first-time users |
| First load | Unknown sample rate; unsupported sample format | **Correctness friction** | A, B, F |
| Interpretation | Blank or flat plots from rate mismatch (documented) | **Cognitive friction** | A, B |
| Core task | Classifier verdict with undocumented basis | **Trust friction** | A, C, D |
| Completion | No export, no save, no report | **Workflow friction** | A, C, D |
| Advanced | Stages 4–5 absent | **Capability ceiling** | A, C, F |

**Disproportionate effects, stated explicitly:** installation friction falls almost entirely on Students and Hobbyists (non-Windows, no admin rights) — the segments the product currently serves best in every other respect. Trust friction falls almost entirely on Analysts and Regulators — the segments that matter most commercially. The friction map and the value map are misaligned.

### Phase 4 — Retention & Churn Analysis

No retention data exists and none is fabricated here. Required instrumentation:

| Metric | Instrumentation required |
| --- | --- |
| D1 / D7 / D30 retention | Anonymous install identifier + session start events, with explicit opt-in |
| Cohort retention | Cohort assignment at first launch, persisted locally |
| Repeat usage | Local session counter |
| Churn indicators | Declining session frequency; rising Settings-correction rate; sessions ending immediately after load failure |
| Pre-churn activity decline | Rolling session-frequency comparison |
| Features associated with retention | Correlate retained vs. churned cohorts against feature-usage events |

**Hard constraint, and it must be resolved deliberately:** Segment A's security posture may prohibit any telemetry whatsoever. The instrumentation plan below is therefore **conditional**. For classified deployments, substitute structured user interviews and voluntary local log export. Do not assume analytics will be permitted; design the research plan to work without it.

### Phase 5 — Feedback & Sentiment Analysis

| Channel | Recommended approach for this product |
| --- | --- |
| CSAT | In-app, post-analysis, single question: "Was this analysis useful?" — segmented by user role |
| NPS | Low value for a mandated-tool context; deprioritize |
| User interviews | **The highest-value channel here.** 8–12 contextual interviews with real analysts, observing actual capture sessions. This substitutes effectively for all quantitative analytics in a secure environment |
| Support tickets | Categorize by pipeline stage; expect a heavy concentration at install and first-load |
| Feature requests | Tag by segment; watch specifically for demodulation requests as a share of total |
| Bug reports | Prioritize any report of *wrong numbers* over any report of crashes — a crash is visible, a wrong metric is not |
| Qualitative feedback | Capture verbatim analyst reasoning about whether they trusted the classifier |
| Abandonment reasons | Exit survey on uninstall where permitted; otherwise ask directly in interviews |

**Combining qualitative and quantitative:** quantitative data tells you *that* users correct the sample rate on 60% of loads; only an interview tells you *that they had to check the sensor log to know the right value* — which is the finding that produces the SigMF recommendation. For this product, in this environment, **qualitative evidence should lead and quantitative should confirm** — the inverse of the usual consumer-product order, because the user population is small, expert, and partly unobservable.

---

## 10. Analytics Instrumentation Plan

**Applicable to non-classified deployments only.** For secure deployments, treat this as a local-log specification that the user may voluntarily export, not as transmitted telemetry.

| Event | User Segment | Trigger | Properties | Why Track It |
| --- | --- | --- | --- | --- |
| `app_launched` | All | Process start | version, OS, GNU Radio version | Platform mix; validates the cross-platform investment case |
| `install_failed` | All | Startup exception | error class, missing dependency | Quantifies the biggest funnel drop |
| `file_load_started` | All | Load dialog confirmed | file extension, file size | Ingestion volume and format mix |
| `file_load_succeeded` | All | Metrics computed | format, sample count, duration, inferred-vs-manual rate | **First-load success rate** |
| `file_load_failed` | All | Load exception | failure reason | Format coverage gaps |
| `sample_rate_overridden` | A, B, C | Settings applied after load | inferred value, corrected value | **Directly measures the filename-inference failure rate — the single most decision-relevant event in this plan** |
| `metrics_computed` | All | Analysis completes | SNR, OBW, noise floor (values or buckets) | Real-world signal-condition distribution; informs algorithm tuning |
| `modulation_classified` | A, E, F | Classifier returns | class, confidence | Class distribution; confidence calibration |
| `classifier_verdict_reviewed` | A, C | User opens constellation view after classification | class, confidence, time-to-review | **Proxy for trust in automation** |
| `view_mode_changed` | All | Switcher clicked | target view | Which domain matters most |
| `hud_readout_used` | A, C, D | Cursor interaction | plot type | Whether manual measurement is still needed |
| `audio_played` | A, E, F | Play clicked | demod mode selected | Is the audio path actually used? |
| `settings_opened` | All | Modal opened | — | Discoverability of correction path |
| `session_ended` | All | App close | duration, files analyzed | Session depth |
| `pipeline_stage_blocked` | A, C, F | User interacts with DEMOD/BITS stepper | stage | **Quantifies demand for the unbuilt stages — the key roadmap input** |
| `export_attempted` | A, C, D | User seeks an export path | — | Demand for a feature that doesn't exist yet |
| `batch_intent` | A, B | >5 files loaded in one session | file count | Demand signal for batch mode |
| `error_shown` | All | Fallback `--` or alert displayed | error type, stage | Reliability hotspots |
| `sample_file_used` | E, G | Bundled file loaded | filename | Distinguishes evaluation from real use |

### Event Taxonomy Coverage

| Category | Applicability here |
| --- | --- |
| Signup / Login | **Not applicable** to the desktop product; applicable only if the web direction is pursued |
| Onboarding | `app_launched`, `install_failed`, `sample_file_used` |
| Feature discovery | `settings_opened`, `view_mode_changed`, `hud_readout_used` |
| Feature usage | `metrics_computed`, `modulation_classified`, `audio_played` |
| Core task started/completed | `file_load_started` / `file_load_succeeded` |
| Errors | `file_load_failed`, `error_shown` |
| Abandonment | `session_ended` with zero successful loads |
| Collaboration | Not applicable until session sharing exists |
| Search | Not applicable |
| Automation | `sample_rate_overridden` (inverse indicator), `batch_intent` |
| Export / share | `export_attempted` |
| Return visits | `app_launched` with a persisted local identifier |
| Conversion | Not applicable — no commercial model identified |

### Minimum Analytics Infrastructure

1. **Local structured event log** (JSONL), written by default, transmitted never without explicit opt-in. This is the only design compatible with the primary segment.
2. **Anonymous install identifier**, locally generated, user-clearable.
3. **Explicit opt-in consent** at first launch, with a plain-language description of exactly what is recorded.
4. **Voluntary export** — a "send diagnostics" action the user invokes deliberately, which is the only viable channel in a secure environment.
5. **Aggregation backend** — required only if opt-in telemetry is pursued; not required for the local-log-plus-interviews approach, which is the recommended starting point.

---

## 11. Essential Graphs & Visualizations

| Analytical Goal | Visualization | Required Data | Metric | Segment | Question It Answers | Decision It Supports |
| --- | --- | --- | --- | --- | --- | --- |
| Retention & longevity | Cohort retention heatmap | Install date, session dates | D1/D7/D30 retention | A, C | Does the tool become habitual? | Whether to invest in workflow embedding vs. capability |
| Drop-offs & conversion | Funnel chart: install → launch → first load → first success → repeat use | Funnel events | Stage conversion rates | All | Where do users disappear? | Whether install or first-load is the priority fix |
| Feature popularity | Grouped bar by role cohort | `view_mode_changed`, feature events | Usage share | All | Which capability is the real product? | What to deepen vs. deprecate |
| **Parameter correction rate** | **Bar chart: inferred vs. overridden sample rate, over time** | `file_load_succeeded`, `sample_rate_overridden` | Override rate | A, B | **Is filename inference failing?** | **Whether SigMF support is urgent — expected to be the single most decisive chart** |
| Usage frequency | Box plot of files-per-session by role | Session events | Distribution and outliers | A, B | Is there a heavy-user tail? | Batch mode prioritization |
| User flow | Sankey: load → view → settings → classify → close | Sequenced events | Path frequency | All | What is the actual sequence of work? | UI layout and default view |
| Feature value vs. adoption | 2×2 scatter: usage frequency vs. stated importance | Events + survey | Value/adoption quadrant | All | What's important but unused? | Discoverability fixes |
| Task efficiency | Before/after bar, manual vs. assisted | Timed observation | Task duration | A, B | Does it actually save time? | The core value claim |
| **Classifier trust** | **Confusion matrix: classifier verdict vs. analyst-confirmed truth** | `modulation_classified` + analyst label | Accuracy, per-class recall | A, C, D | **Is the classifier right?** | **Whether to publish, retrain, or demote the classifier** |
| Classifier calibration | Reliability diagram: confidence vs. observed accuracy | Same | Calibration error | A, D | Does confidence mean anything? | Whether to show the score at all |
| Signal conditions | Histogram of SNR and OBW across real captures | `metrics_computed` | Distribution | A, B | What conditions must algorithms survive? | Algorithm tuning targets |
| Churn | Retention curve | Session history | Retention over time | A, C | When do users leave? | Intervention timing |
| Satisfaction | CSAT distribution by role | In-app CSAT | Score distribution | All | Who is underserved? | Segment prioritization |
| **Pipeline demand** | **Bar: interactions with blocked DEMOD/BITS stages** | `pipeline_stage_blocked` | Interaction count | A, C, F | **How badly is the missing half wanted?** | **Roadmap sequencing** |

The three bolded charts are the ones that would change a decision. The rest are context.

---

## 12. Data Requirements & Measurement Gaps

| Required Insight | Data Available? | Data Source | Measurement Method | Priority |
| --- | --- | --- | --- | --- |
| What the product currently does | **Yes** | SIGMA README + `docs/` | Source and documentation review | — |
| SIGMA architecture and data flow | **Yes** | `docs/ARCHITECTURE.md` | Document review | — |
| SIGMA DSP method definitions | **Yes** | README metrics table, arch §2.4 | Document review | — |
| Implementation status per stage | **Yes** | README stage table, pipeline stepper | Document review | — |
| SignalForge frontend implementation | **No — robots-blocked** | `SignalForge/frontend/` | Local clone and code review | High |
| SignalForge backend existence | **No — Not verified from available sources** | No backend repo found | Direct confirmation from the team | **Critical** |
| Whether the web dashboard is functional | **No — appears static** | Deployed page | Load a real file against the deployment | **Critical** |
| Relationship between the two repos | **No** | — | Team clarification | High |
| Which Vercel deployment is current | **No — two URLs conflict** | Repo About vs. brief | Team clarification | Medium |
| Modulation classifier accuracy | **No** | — | Labeled test set across modulations and SNRs | **Critical** |
| Whether metrics use whole file or initial buffer | **Unclear** | Arch §2.4 implies an initial batch | Code inspection | **High — affects correctness of every published number** |
| Large-file performance | **No** | — | Benchmark across file sizes | High |
| Real-world capture format distribution | **No** | — | Audit a real sensor archive | **Critical — determines reader priorities** |
| Baseline manual task time | **No** | — | Timed observation of 10–20 analyst sessions | **Critical — without it, no efficiency claim is defensible** |
| Actual user segment mix | **No** | — | Interviews + opt-in telemetry | High |
| Sample-rate override frequency | **No** | — | `sample_rate_overridden` instrumentation | **Critical** |
| Retention and engagement | **No** | — | Instrumentation per §10 | Medium |
| User satisfaction | **No** | — | CSAT + interviews | Medium |
| Security/deployment constraints of the target org | **No** | — | Stakeholder interview | **Critical — gates the entire architecture decision** |

### Evidence Classification Ladder

| Level | Examples from this analysis |
| --- | --- |
| **Known** (directly stated by a source) | Stages 4–5 are planned; `file_source` reads 8-byte complex samples; audio uses `winsound`; SignalForge has one commit and one directory |
| **Observed** (directly inspected) | The deployed dashboard's parameter values are static HTML text; SignalForge has no README; the SIGMA repo contains `signal.iq_telemetry.json` and `ui_screenshot.png` |
| **Inferred** (reasoned from evidence) | The web product targets a multi-user SaaS model; the two products have divergent user assumptions; `int16` captures will currently fail |
| **Hypothesized** (plausible, untested) | Analysts will adopt this for triage; operators would catch more bad captures; batch mode would raise throughput |
| **Requires validation** | Classifier accuracy; all time savings; segment mix; whether the target organization would permit any telemetry at all |

---

## 13. Constraints & Risks

### 13.1 User Constraints

| Constraint | Affected segments | Effect on adoption and value |
| --- | --- | --- |
| **Time** | B (seconds), A (minutes) | A tool needing setup per file fails the operator entirely |
| **Money** | E, F | Must remain free/open for these segments; A and D have budget but long procurement cycles |
| **Skills** | B, E | Undefined terms and unexplained metrics limit the addressable audience |
| **Accessibility** | All | Color-only I/Q distinction; dense fixed-size dark UI |
| **Connectivity** | B, A | Field sites and air-gapped facilities — **cloud dependency is disqualifying** |
| **Device / OS** | A, C, E, F | Windows-only audio and setup path excludes Linux workstations, which dominate this domain |
| **Privacy** | A, D | Captures may be classified; telemetry may be prohibited outright |
| **Security** | A | Air-gap requirements; software must pass security review; heavyweight dependencies are a liability |
| **Trust** | A, C, D | Unvalidated automated verdicts will be ignored or challenged |
| **Data availability** | All | **Missing capture metadata is the defining constraint of the entire problem domain** |
| **Organizational** | A, D | Installation approval; mandated tools; formal procedure change is slow |
| **Existing workflows** | A, C, D, F | Established toolchains (MATLAB, GNU Radio, URH); the product must interoperate rather than demand replacement |
| **Learning curve** | B, E | Steep for B and E; trivially shallow for A, who will hit the ceiling within an hour |
| **Switching costs** | A, C, D | Retraining, revalidation of methodology, re-documentation of procedure |

### 13.2 Product Constraints

| Constraint | Current state | Effect |
| --- | --- | --- |
| **Prototype maturity** | SIGMA: functional, 12 commits, 2 of 5 stages. SignalForge: 1 commit, frontend only | Neither is production-ready; SignalForge is pre-implementation |
| **Architecture** | Desktop, GNU Radio + PyQt5, tightly coupled GUI and analysis | Blocks headless, batch, and API use; blocks the web direction without substantial rework |
| **Scalability** | Single file, single user, GUI-bound | No path to queue or archive-scale processing today |
| **Format support** | `complex64` only, filename-based rate inference | **The most significant correctness constraint in the product** |
| **Analysis scope** | Metrics appear to be computed on an initial sample buffer | If confirmed, every metric describes a portion of the file while presenting as a property of the whole — **must be verified and disclosed** |
| **API limitations** | No API, no CLI, no export | Cannot integrate with any existing pipeline |
| **Data quality** | Depends entirely on unavailable capture metadata | The product inherits the problem it exists to solve |
| **Integration** | GNU Radio `.grc` interoperability only | Narrow but genuine |
| **Authentication** | None in SIGMA; mocked in SignalForge | Multi-user use unsupported |
| **Security** | No encryption, audit, or access control | Blocks sensitive deployment |
| **Reliability** | Documented error isolation and safe fallbacks | **A genuine strength** — the fault-isolation design in arch §5 is better than typical at this maturity |
| **Maintainability** | Clean modular separation (`core` / `flowgraph` / `window` / `theme`), thorough documentation | **A genuine strength** — the codebase is positioned well for the recommended refactors |
| **Cost** | Open-source stack, no licensing | Low barrier |
| **UX complexity** | Eight metrics, four plots, five view modes, HUD overlay, settings modal on one screen | Appropriate for A, overwhelming for B and E |
| **Platform lock-in** | `winsound`, Radioconda-on-Windows | The most easily fixed serious constraint on this list |

### 13.3 Top Risks, Ranked

| # | Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| 1 | **Claim-delivery gap** — marketing five stages, delivering two | **Occurring now** | Severe (credibility with the decisive segment) | Propagate SIGMA's honesty convention to SignalForge immediately; it costs nothing |
| 2 | **Silent wrong answers** from filename-inferred sample rate | High | Severe (wrong parameters reach operational sensors) | SigMF sidecar; explicit confirmation at load |
| 3 | **Unvalidated classifier** presented with a confidence score | High | High (expert rejection; evidentiary liability for regulators) | Build a labeled test set; publish per-class accuracy by SNR |
| 4 | **Blind FEC/de-interleaving treated as a delivery item** | High | High (guaranteed roadmap failure) | Split parameter-known from blind; resource blind work as research with no delivery date |
| 5 | **Format incompatibility** with real-world `int8`/`int16` captures | High | High (tool fails on the archive it was built for) | Multi-format reader |
| 6 | **Cloud architecture incompatible with the stated customer** | Medium | Severe (product unusable in its intended environment) | Decide the deployment model now, before dependencies harden |
| 7 | **Windows-only lock** | Certain | Medium-High (excludes core segments) | Portable audio backend; Linux packaging |
| 8 | **Two divergent products** with different user models and no stated relationship | **Occurring now** | Medium-High (split effort, incoherent story) | Decide explicitly: one product, or two with distinct audiences |
| 9 | **No export or persistence** | Certain | Medium (caps the workflow, prevents procedure adoption) | JSON export first — it is cheap |
| 10 | **Metrics computed on a partial buffer while presented as whole-file** | Unverified | Medium-High if true | Verify in code; disclose or fix |

---

## 14. Prioritized Product Roadmap

### NOW — make the core correct, honest, and measurable

| Item | Evidence / reasoning |
| --- | --- |
| **Align all public claims with implementation status** | Evidence: the landing page advertises FEC, de-interleaving, and bitstream correlation that no inspected code implements. SIGMA's own README and pipeline stepper already model the right behavior. Zero engineering cost, immediate credibility protection with the decisive segment. |
| **Multi-format IQ reader with explicit format and rate confirmation** | Evidence: reader assumes `complex64`; rate is inferred from filename. These are the two silent-failure modes that make every other number untrustworthy. |
| **SigMF sidecar read/write** | Evidence: the problem statement names missing cross-sensor metadata as the root cause. This addresses the cause rather than the symptom. |
| **Methodology disclosure in the UI** | Evidence: formulas are already written in `docs/` — this is a surfacing task, not a computation task. Highest value-to-effort ratio identified. |
| **Cross-platform support (replace `winsound`; Linux packaging)** | Evidence: `winsound` and Radioconda-on-Windows instructions exclude the workstations this domain uses, and the segments best served today. |
| **Verify the metric computation scope** (whole file vs. initial buffer) | Evidence: architecture §2.4 describes reading a sample buffer; if metrics describe a portion while presenting as whole-file properties, that is a correctness defect ahead of any new feature. |
| **Classifier validation harness** | Evidence: a confidence score is displayed with no documented basis. Measure before anyone relies on it. |
| **Basic JSON/CSV export** | Evidence: the workflow currently terminates in a screenshot; `signal.iq_telemetry.json` suggests groundwork exists. |
| **Baseline task-time observation with real analysts** | Evidence: every efficiency claim in §8 is currently unmeasurable. Without a baseline, no improvement can be demonstrated. |

**Assumption being made:** that correctness and credibility matter more than feature count to the evaluating and operating audience. This is well-supported for expert technical users but should be confirmed with the actual stakeholder.

### NEXT — strengthen the validated core

| Item | Evidence / reasoning |
| --- | --- |
| **Demodulation to symbols** (BPSK/QPSK/FSK first) | Evidence: stage 4 is the product's own stated next step and the hinge of the problem statement. Scope per-modulation, not universally. |
| **Symbol-rate estimation** | Evidence: it is the required input to demodulation and no current metric provides it. |
| **Batch / folder ingestion** | Evidence: queue triage is Segment A's highest-frequency job; validate with the `batch_intent` event first. |
| **Session persistence and history** | Evidence: reproducibility and second-analyst review are stated jobs-to-be-done with no current support; History already appears in the concept UI. |
| **Report generation** | Evidence: Segment D's core need; already mocked as *Download Report*. Build the mocked feature rather than removing it. |
| **Headless CLI / API** | Evidence: Segment C will not adopt a GUI-only measurement tool; also a prerequisite for batch. |
| **Signal-presence / quality gate** | Evidence: uses only metrics that already exist; cheapest meaningful automation available. |
| **Accessibility pass** (non-color I/Q, keyboard nav, scalable text) | Evidence: color is currently the sole I/Q channel distinction. |
| **Deployment-model decision** (air-gapped desktop vs. on-prem web vs. cloud) | Evidence: the stated customer cannot use cloud analysis. Deciding late is far more expensive than deciding now. |

### LATER — requires evidence, infrastructure, or scale

| Item | Evidence / reasoning |
| --- | --- |
| **De-interleaving and FEC with known parameters** | Mature algorithms; genuinely deliverable — but only meaningful once bits exist. |
| **Bitstream correlation and preamble detection** | Depends on the entire preceding chain. |
| **Multi-user collaboration and shared sessions** | Requires a validated multi-user need; the current evidence for it is a mocked UI, not a stated requirement. |
| **Comparison and trend views** | Requires an accumulated analysis archive. |
| **ML-based classification** | Requires the labeled dataset from the validation harness, and an explicit decision about the explainability trade-off against recommendation 19. |
| **Blind interleaver / FEC parameter estimation** | **Research, not development.** Evidence: even mature specialist tools in this space rely on operator knowledge or rule-based inference rather than solved blind identification. Fund it as research; never schedule it as a feature. |

**Explicitly not prioritized, and why:** multi-user collaboration and account systems appear prominently in the SignalForge concept but rest on no evidence of user need — only on a default SaaS product template. Segment A's actual collaboration need is *reproducibility and handoff*, which session export satisfies at a fraction of the cost.

---

## 15. Final End-Consumer Use-Case Matrix

| User Category | Characteristic | Problem | Job-to-be-Done | Use Case | Current Workflow | Product Workflow | Features Used | Expected Benefit | Constraints | Metric |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **A. SIGINT Analyst** | Expert; air-gapped; daily; results feed operations | Captures arrive unlabeled from heterogeneous sensors | Characterize an unknown emission defensibly | Unknown-signal characterization | Guess params → build flowgraph → eyeball → hypothesize | Load → confirm rate → read 8 metrics + 4 plots → confirm classifier | Ingestion, metrics, all 4 plots, classifier, stepper | Minutes instead of a session; consistent method | Security, air-gap, trust, existing tools, Windows-only | Time-to-characterization; sample-rate override rate |
| **A. SIGINT Analyst** | Same | Queue backlog | Decide what deserves attention | Triage | Open each file manually | Load → read SNR/OBW → keep or discard | Metrics, waterfall, spectrum | Higher throughput | No batch mode today | Captures triaged per analyst-hour |
| **A. SIGINT Analyst** | Same | Another analyst can't reproduce my result | Hand off defensibly | Review & handoff | Screenshots into a document | **Unsupported** | — | Reproducibility | No persistence or export | Reproduction agreement rate |
| **B. Sensor Operator** | Technician; field; dozens/shift; seconds per task | Bad captures found too late | Verify the capture now | Post-capture quality check | Save → transfer → check later | Load → read SNR/peak/OBW → re-record if needed | Metrics, spectrum, waterfall | Recovers otherwise-lost captures | Time, site compute, connectivity, lower proficiency | Recapture rate; bad captures reaching the analyst |
| **B. Sensor Operator** | Same | True capture params never travel with the file | Record provenance at source | Capture annotation | Filename convention or nothing | **Recommended: SigMF sidecar write** | (recommended) | Removes downstream guessing entirely | Requires new feature | % files arriving with valid metadata |
| **C. R&D Engineer** | Lab; very high skill; campaign-based | Ad hoc scripts; methodology drift | Verify waveform against design | Conformance measurement | Custom script per engineer | Load → read standardized metrics → compare | Metrics, constellation, spectrum, published formulas | Comparable results across the team | Needs export/CLI; may need Linux; rejects black boxes | Measurement variance across engineers |
| **D. Regulator / Investigator** | Enforcement; episodic; contested output | Evidence must survive challenge | Document an interfering emission | Interference case-building | Vendor tool → manual transcription | Load → read OBW/center/power → **report (unbuilt)** | Metrics, spectrum, waterfall | Defensible, reproducible documentation | Evidentiary standards; field conditions; methodology must be disclosed | Cases with complete measurement records |
| **E. Student / Learner** | Coursework; low-moderate skill; bursty | Theory stays abstract; GNU Radio is a wall | See what modulation looks like | Visual intuition-building | Textbook figures; abandoned GRC install | Load bundled sample → 4 domains → constellation → listen | Bundled data, all plots, view switcher, audio, `.grc` | Concept-to-picture link | **OS and admin rights are the binding constraint**; zero budget | First-run success rate |
| **F. Hobbyist / Reverse-Engineer** | Self-taught; consumer SDR; intense sessions | Tool-hopping across the chain | Get to interpretable bytes | Device protocol reverse-engineering | rtl_sdr → Inspectrum → URH | **Blocked at stage 3**; `int8` captures unreadable | Plots only | Currently below URH's offering | Consumer formats, Linux/macOS, no budget | Stage reached before leaving the tool |
| **G. Evaluator / Stakeholder** | Judge or procurement; minutes of attention; finds gaps | Can't separate built from mocked | Assess real coverage of the brief | Solution evaluation | README → demo → code spot-check | SIGMA: stepper and stage table tell the truth. SignalForge: mock implies more than exists | Stepper, stage table, docs | Accurate assessment | Very limited time; tests the weakest claim first | Claim-to-implementation consistency |

---

## 16. Final Synthesis

**1. Who the product serves.** Primarily a government SIGINT or spectrum-monitoring analyst working from archived off-air captures, with a high-frequency secondary user in the sensor operator, strong latent fit for students and defence R&D engineers, and a real but unserved opportunity in spectrum regulators. It does not currently serve hobbyists better than existing free tools, and should not target them yet.

**2. The most important end-consumer problems identified.** Capture metadata is missing or untrustworthy across a heterogeneous sensor fleet, making every downstream measurement uncertain. Characterization requires assembling a toolchain per file. Results are not reproducible between analysts. Bad captures are discovered long after the emission has passed. And the hardest determinations — modulation, coding, interleaving — are exactly the ones least supported by automation today.

**3. The primary use cases.** Unknown-signal characterization; queue triage; post-capture quality verification; waveform conformance measurement; interference documentation; and DSP concept learning.

**4. How the current prototype addresses those problems.** SIGMA genuinely consolidates characterization: four synchronized visualizations and eight computed physical metrics from a single file load, with a modulation hypothesis the analyst can immediately corroborate against a full-resolution constellation view. Its documented DSP methodology, thread-safe file reloading, error isolation, and — notably — its honest in-UI marking of unfinished pipeline stages are real assets. SignalForge contributes a clear articulation of the product vision and an accessible entry point, but contributes no verified analysis capability.

**5. Major gaps between prototype and production.** Three of five pipeline stages are absent, including the demodulation stage that the entire premise depends on. The reader supports one sample format and infers sample rate from filenames. There is no export, no persistence, no batch processing, no report generation, no API, and no cross-platform support. The modulation classifier — the product's most differentiated feature — has no published accuracy figure. And the public presentation claims substantially more than the implementation delivers.

**6. Features that should be considered.** In order: SigMF metadata support and explicit format/rate confirmation; multi-format ingestion; methodology disclosure in the UI; cross-platform support; classifier validation; JSON export; then demodulation to symbols, symbol-rate estimation, batch ingestion, session persistence, and report generation. De-interleaving and FEC belong after bits exist, split cleanly between the parameter-known case (engineering) and the blind case (research).

**7. What needs to be measured before making product decisions.** Baseline manual task time with real analysts. The real-world distribution of capture formats and sample rates in the target archive. Classifier accuracy per modulation class per SNR. The frequency with which users must override the inferred sample rate. Whether metrics are computed over whole files or partial buffers. And whether the target organization will permit any telemetry at all — because the answer determines the entire research approach.

**8. The most important user constraints.** Security and air-gap requirements, which likely disqualify a cloud architecture for the primary segment and constrain all instrumentation. Missing capture metadata, which is simultaneously the product's reason for existing and its hardest input dependency. Platform lock to Windows, which excludes the workstations this domain actually uses. And expert users' refusal to trust automated verdicts they cannot audit.

**9. The analytics instrumentation required.** A local-first, opt-in, structured event log covering ingestion success and failure, sample-rate override frequency, feature and view usage, classifier verdicts alongside analyst confirmation, interactions with blocked pipeline stages, and session depth — with voluntary export rather than automatic transmission. For classified deployments, structured contextual interviews substitute for telemetry entirely, and should be treated as the primary research channel rather than a fallback.

**10. Key hypotheses to validate with real users.**

- That analysts will adopt this for triage even without demodulation. *(If false, the roadmap must lead with stage 4 rather than with correctness work.)*
- That the variance-based modulation classifier is accurate enough to be trusted at operational SNRs. *(If false, it should be demoted from a verdict to an advisory hint.)*
- That sample-rate inference fails often enough in practice to justify the SigMF investment. *(The `sample_rate_overridden` event answers this within one week of instrumentation.)*
- That operators would act on an on-site quality check rather than defer to the analyst. *(Determines whether Segment B is a real segment or a theoretical one.)*
- That the target organization would deploy a tool with this dependency footprint. *(A single stakeholder conversation resolves this and should happen before further engineering.)*
- That reproducibility and handoff matter more to these users than real-time collaboration. *(Determines whether session export or multi-user infrastructure gets built.)*

---

### Closing note on evidence discipline

Every capability claim in this report is traceable to the README, the architecture document, the repository file listing, or the delivered HTML of the deployed page. No time savings, retention figures, adoption rates, accuracy numbers, or user statistics have been invented. Where a number would ordinarily appear, the measurement method required to obtain it is specified instead. Two material questions — whether a SignalForge backend exists, and whether SIGMA's metrics describe whole files or sample buffers — remain **Not verified from available sources** and should be resolved by the team before this report is used to make roadmap commitments.
