"""
SIGMA - Signal Intelligence & Generalized Modulation Analyzer
Sample Rate Resolution (Stage 1)

Determines the sample rate `f_s` for a capture, and reports **how** it was
determined. This matters more than the number itself.

Why this module exists
----------------------
Every frequency-domain result in the pipeline is a fraction of `f_s`:

    R_s = f_s / SPS          SPS is measurable with no knowledge of f_s
    OBW = f_s * (occupied fraction)
    f_c = f_s * (normalised offset)

Samples carry no absolute time reference. A capture of 1000 samples with a
symbol clock every 10 samples is *identical* to one recorded at twice the
rate with a clock every 20 samples -- the bits on disk are the same, and the
only difference is the label someone wrote on the file. Consequently:

    **The sample rate cannot be measured from the samples alone.**

It must come from outside the data. This module therefore does not pretend to
"detect" a rate it cannot observe. It resolves `f_s` from the most trustworthy
available source and labels it:

    1. USER       - the operator set it explicitly. Highest trust; they have
                    the datasheet or the SDR's config.
    2. PROTOCOL   - a recognised standard symbol rate was measured. GSM at
                    270.833 ksps, for example, implies f_s = SPS * 270833.
                    Only accepted on a close, unambiguous match.
    3. FILENAME   - a rate token in the filename ("250k", "1msps"). A hint,
                    not a measurement. Wrong if the file was renamed.
    4. DEFAULT    - nothing available; fall back and say so.

Honest reporting
----------------
`SampleRateResult.confidence` distinguishes MEASURED / INFERRED / ASSUMED, and
`source` names the origin. A rate that came from a filename substring is never
presented as if it had been measured. Downstream stages can (and should) warn
when they are running on an ASSUMED rate, because `R_s = f_s / SPS` means a
wrong `f_s` scales every reported symbol rate by the same factor.

Protocol matching is deliberately conservative: it requires the measured
symbol rate to be within a tight tolerance of the standard AND to be the only
plausible candidate. A near-miss returns no match rather than a guess.
"""

import os
import re

import numpy as np

# ---------------------------------------------------------------------------
# Known standard symbol rates.
#
# Each entry: (name, symbol_rate_hz, tolerance_fraction).
# Tolerance is tight on purpose -- we would rather decline than mis-identify a
# signal as a standard and thereby compute a badly wrong sample rate.
# ---------------------------------------------------------------------------
KNOWN_SYMBOL_RATES = (
    ("GSM / GMSK",            270_833.3,   0.005),
    ("VDL2 / AIS",            9_600.0,     0.005),
    ("DVB-S (QPSK)",          27_500_000.0, 0.005),
    ("DAB / Eureka 147",      1_200_000.0, 0.005),
    ("DECT",                  1_152_000.0, 0.005),
    ("Bluetooth (BR/EDR)",    1_000_000.0, 0.005),
    ("ZigBee (802.15.4)",     62_500.0,    0.005),
    ("Inmarsat STD-C",        1_200.0,     0.005),
    ("Morse / CW (20 wpm)",   25.0,        0.02),
)

# Filename tokens.
#
# Ordered by PRIORITY, highest first -- not by which match is longest.
#
# Two traps, both found by testing against real filenames in this project:
#
# 1. "demo_bpsk_100ksps_1msps.iq" names two rates. 100 ksps is the *symbol*
#    rate, 1 msps is the *sample* rate. Longest-token does not separate them
#    ("100ksps" is longer), and neither does magnitude. What separates them is
#    the explicit "S/s" suffix: "msps" means samples per second, so it wins.
#
# 2. "fm_rds_250k_1Msamples.iq" also names two. Here "250k" is the *sample*
#    rate and "1Msamples" is just prose describing the file ("1M samples").
#    So "msamp" must rank BELOW a bare multiplier suffix, not above it.
#
# Hence: explicit S/s forms first, then bare multiplier suffixes, then the
# weaker "...samples" prose forms last.
#
# Every pattern consumes the multiplier letter as part of the match, and uses
# `(?![a-z])` as the lookahead -- NOT `\b`. A word boundary between a digit and
# a letter matches *inside* "250k" (0..k is a boundary), so `(\d+)\s*k\b`
# silently matched just "250", produced 250 Hz, and was then thrown away by the
# sanity floor. The lookahead prevents the letter being swallowed while still
# allowing the token to end at a delimiter or end-of-string.
_END = r"(?![a-z])"

_PRIORITY_PATTERNS = (
    # Explicit samples-per-second.
    (re.compile(r"(\d+(?:\.\d+)?)\s*(?:gsps|gs/s)" + _END, re.I), 1e9),
    (re.compile(r"(\d+(?:\.\d+)?)\s*(?:msps|ms/s)" + _END, re.I), 1e6),
    (re.compile(r"(\d+(?:\.\d+)?)\s*(?:ksps|ks/s)" + _END, re.I), 1e3),
    # An explicit frequency unit.
    (re.compile(r"(\d+(?:\.\d+)?)\s*ghz" + _END, re.I), 1e9),
    (re.compile(r"(\d+(?:\.\d+)?)\s*mhz" + _END, re.I), 1e6),
    (re.compile(r"(\d+(?:\.\d+)?)\s*khz" + _END, re.I), 1e3),
    # Bare multiplier suffix: "250k", "1m".
    (re.compile(r"(\d+(?:\.\d+)?)g" + _END, re.I), 1e9),
    (re.compile(r"(\d+(?:\.\d+)?)m" + _END, re.I), 1e6),
    (re.compile(r"(\d+(?:\.\d+)?)k" + _END, re.I), 1e3),
    # Weakest: prose forms describing the file rather than a rate.
    (re.compile(r"(\d+(?:\.\d+)?)\s*(?:gsamp|msamp|ksamp|samples|samps)" + _END, re.I), None),
)

# Kept for backwards compatibility with the earlier name.
_FILENAME_PATTERNS = tuple(_PRIORITY_PATTERNS)

# Values we are willing to read out of a filename. A bare "1m" in
# "demo_bpsk_100ksps_1msps.iq" must not be mistaken for 1 MHz, and a rate
# token that would produce an absurd SPS is rejected.
_MIN_SANE_RATE = 1e3
_MAX_SANE_RATE = 100e9


def _snap_to_round(value, tolerance=0.005):
    """Snap a computed rate to a nearby round number, else leave it alone.

    A protocol correction divides two nearly-equal floats, so a mathematically
    exact 1e6 can come out as 1000001. Real sample rates are round: 1e6,
    250e3, 2.5e9, 2.048e6. But a genuinely non-round rate (say 999,412) must
    NOT be forced to a round one -- that would be inventing precision we do
    not have.

    So we only snap when a candidate round value is within `tolerance`
    (0.5%) of the computed one, and we prefer the candidate requiring the
    smallest relative change.
    """
    if not value or value <= 0:
        return float(value)

    candidates = set()
    # Powers of ten times 1, 2, 2.5, 4, 5.
    for exp in range(3, 12):
        base = 10.0 ** exp
        for mult in (1.0, 2.0, 2.5, 4.0, 5.0):
            candidates.add(base * mult)
    # Some common SDR rates that are not powers of ten.
    candidates.update({2.048e6, 4.096e6, 8.192e6, 1.024e6, 3.072e6, 1.536e6,
                       9.6e3, 19.2e3, 38.4e3, 76.8e3, 153.6e3, 307.2e3,
                       614.4e3, 1.2288e6, 2.4576e6, 4.9152e6, 270.833e3})

    best = None
    for c in candidates:
        rel = abs(c - value) / value
        if rel <= tolerance:
            if best is None or rel < best[0]:
                best = (rel, c)
    if best is None:
        return float(value)
    return float(best[1])


def resolve_sample_rate_file(filepath, fallback=None):
    """Return just the rate (Hz) parsed from a filename, or `fallback`.

    Convenience wrapper for callers that only want to update a number -- the
    full `SampleRateResult` (used by the metadata layer) carries the
    provenance, but the file-open path needs a plain value and must not
    clobber the current rate when the filename says nothing.
    """
    parsed = parse_rate_from_filename(filepath)
    if parsed is None:
        return fallback
    return parsed[0]


class SampleRateResult:
    """Outcome of sample-rate resolution."""

    # Source ranks, most trustworthy first.
    USER = "user"
    PROTOCOL = "protocol"
    FILENAME = "filename"
    DEFAULT = "default"

    # Confidence labels.
    MEASURED = "MEASURED"     # operator supplied it, or derived from a standard
    INFERRED = "INFERRED"     # read from a filename token
    ASSUMED = "ASSUMED"       # nothing was available

    def __init__(self):
        self.samp_rate = 1_000_000.0
        self.source = self.DEFAULT
        self.confidence = self.ASSUMED
        self.detail = ""
        self.matched_protocol = None
        self.user_supplied = False

    def __repr__(self):
        return (f"SampleRateResult({self.samp_rate:g} S/s, "
                f"source={self.source}, {self.confidence})")


def parse_rate_from_filename(filepath):
    """Extract a sample rate from a filename, or None.

    Returns (rate_hz, matched_text) so the caller can report exactly which
    token was used -- a renamed file must be visibly traceable.

    Higher-priority patterns are tried first and a match there wins outright.
    Within one priority level the longest match is preferred, so "250k" is not
    truncated to "250".
    """
    if not filepath:
        return None
    name = os.path.basename(filepath).lower()

    for pattern, scale in _PRIORITY_PATTERNS:
        if scale is None:
            # Prose forms ("1Msamples") describe the file, not a rate. They
            # are listed only so a later pattern does not misread them.
            continue
        best = None
        for m in pattern.finditer(name):
            try:
                value = float(m.group(1))
            except (TypeError, ValueError):
                continue
            rate = value * scale
            if not (_MIN_SANE_RATE <= rate <= _MAX_SANE_RATE):
                continue
            if best is None or len(m.group(0)) > len(best[1]):
                best = (rate, m.group(0))
        if best is not None:
            return best[0], best[1]
    return None


def match_known_protocol(symbol_rate_hz, tolerance_scale=1.0):
    """Match a measured symbol rate against known standards.

    Returns (name, rate_hz, relative_error) or None. Requires a close match;
    a near-miss returns None rather than a guess, because a mis-identified
    protocol yields a confidently wrong sample rate.
    """
    if not symbol_rate_hz or symbol_rate_hz <= 0:
        return None

    hits = []
    for name, rate, tol in KNOWN_SYMBOL_RATES:
        rel = abs(symbol_rate_hz - rate) / rate
        if rel <= tol * tolerance_scale:
            hits.append((name, rate, rel))

    if not hits:
        return None
    hits.sort(key=lambda h: h[2])

    # Several standards genuinely share a symbol rate (AIS and VDL2 are both
    # 9600; DVB-S and DVB-S2 are both 27.5 M). That is not ambiguity about the
    # *rate*, only about the label -- and the rate is what we need. So accept
    # the best hit; the name is reported as a family, not a firm identification.
    best = hits[0]
    same_rate = [h for h in hits if h[1] == best[1]]
    if len(same_rate) > 1:
        family = " / ".join(sorted({h[0].split(" (")[0] for h in same_rate}))
        return (family, best[1], best[2])

    # Different *rates* matching means real ambiguity -> decline.
    others = [h for h in hits if h[1] != best[1]]
    if others and others[0][2] < best[2] * 3:
        return None
    return best


def estimate_sample_rate(x, symbol_rate_result=None, filepath=None,
                         user_rate=None, user_is_explicit=False):
    """Resolve the sample rate for a capture and say where it came from.

    Parameters
    ----------
    x : array_like of complex, optional
        Samples, used only for sanity checks (not for measuring f_s -- see the
        module docstring: that is not possible from samples alone).
    symbol_rate_result : dict, optional
        Output of `estimate_symbol_rate`. If it locked, its symbol rate may
        let us recognise a standard and derive f_s from it.
    filepath : str, optional
        Used for the filename hint.
    user_rate : float, optional
        Rate supplied by the operator via Settings.
    user_is_explicit : bool
        True when the operator actively set it (vs the app's default value
        simply being carried through).

    Returns
    -------
    SampleRateResult
    """
    res = SampleRateResult()

    # 1. Operator-supplied rate wins outright.
    if user_rate and user_is_explicit:
        res.samp_rate = float(user_rate)
        res.source = res.USER
        res.confidence = res.MEASURED
        res.user_supplied = True
        res.detail = "set by the operator"
        return res

    # 2. A recognised standard symbol rate gives an absolute reference.
    #    R_s is measured in Hz using the *current* assumed f_s, so a match
    #    lets us correct f_s to whatever makes the standard line up.
    if symbol_rate_result and symbol_rate_result.get("locked"):
        meas_rs = symbol_rate_result.get("symbol_rate_hz")
        hit = match_known_protocol(meas_rs) if meas_rs else None
        if hit is not None:
            name, std_rate, rel = hit
            # R_s is measured in Hz using the assumed f_s, so it scales
            # linearly with it: if the true rate is k times the assumed one,
            # the measured symbol rate is k times the standard. Hence
            #
            #     k = standard / measured        f_s_true = k * f_s_assumed
            #
            assumed = symbol_rate_result.get("samp_rate",
                                             symbol_rate_result.get("assumed_samp_rate"))
            if assumed and meas_rs:
                corrected = float(assumed) * (std_rate / meas_rs)
                # Sample rates in this domain are round numbers. Snap to the
                # nearest "nice" value so accumulated float noise does not
                # turn exactly 1_000_000 into 1000001 and then get displayed
                # or reported as an arbitrary-looking figure.
                res.samp_rate = _snap_to_round(corrected)
                res.source = res.PROTOCOL
                res.confidence = res.MEASURED
                res.matched_protocol = name
                res.detail = (f"matched {name} at {std_rate:,.0f} sym/s "
                              f"({rel * 100:.2f}% off)")
                return res

    # 3. Filename token. A hint, never a measurement.
    parsed = parse_rate_from_filename(filepath)
    if parsed is not None:
        rate, token = parsed
        res.samp_rate = rate
        res.source = res.FILENAME
        res.confidence = res.INFERRED
        res.detail = f'filename token "{token}"'
        return res

    # 4. Nothing usable.
    if user_rate:
        res.samp_rate = float(user_rate)
        res.source = res.DEFAULT
        res.confidence = res.ASSUMED
        res.detail = "no rate in the filename; using the app default"
        return res

    res.source = res.DEFAULT
    res.confidence = res.ASSUMED
    res.detail = "no rate available; using 1 MSps"
    return res


def format_sample_rate(res):
    """Short display string for the sample rate."""
    if not res or not res.samp_rate:
        return "--"
    r = res.samp_rate
    if r >= 1e9:
        return f"{r / 1e9:.3f} GSps"
    if r >= 1e6:
        return f"{r / 1e6:.2f} MSps"
    if r >= 1e3:
        return f"{r / 1e3:.2f} kSps"
    return f"{r:.0f} Sps"


def format_sample_rate_source(res):
    """One-line provenance string, for display beside the rate."""
    if not res:
        return "--"
    if res.source == res.USER:
        return "MEASURED - operator set"
    if res.source == res.PROTOCOL:
        return f"MEASURED - {res.matched_protocol}"
    if res.source == res.FILENAME:
        return f"INFERRED - {res.detail}"
    return "ASSUMED - no rate found"


def check_inconsistency(samp_rate_result, symbol_rate_result,
                        min_sps=2.0, max_sps=4096.0):
    """Flag a likely-wrong sample rate from an implausible samples-per-symbol.

    A measured SPS outside [min_sps, max_sps] almost always means the assumed
    f_s is wrong rather than that the signal is exotic: real systems sit in
    single digits to low hundreds. This is cheap, needs no extra measurement,
    and catches the exact failure mode of a renamed file -- an order-of-
    magnitude SPS error.

    Returns (ok, message).
    """
    if not symbol_rate_result or not symbol_rate_result.get("locked"):
        return True, ""
    sps = symbol_rate_result.get("samples_per_symbol")
    if not sps:
        return True, ""

    if sps < min_sps:
        return False, (f"SPS {sps:.2f} is implausibly low; the assumed sample "
                       f"rate is probably too low")
    if sps > max_sps:
        return False, (f"SPS {sps:.0f} is implausibly high; the assumed sample "
                       f"rate is probably too high")
    return True, ""
