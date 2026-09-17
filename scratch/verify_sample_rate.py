"""Verify sample-rate resolution: filename parsing, protocol matching,
provenance labelling, and the SPS sanity check."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from sigma_sample_rate import (parse_rate_from_filename, match_known_protocol,
                               estimate_sample_rate, format_sample_rate,
                               format_sample_rate_source, check_inconsistency)

fails = 0
def check(label, got, want):
    global fails
    ok = got == want
    if not ok: fails += 1
    print(f"{'ok  ' if ok else 'FAIL'} {label:52s} got={got!r} want={want!r}")

print("=== 1. filename parsing ===")
check("bpsk_100ksps_1msps.iq -> prefer longest token",
      round(parse_rate_from_filename("demo_bpsk_100ksps_1msps.iq")[0]), 1_000_000)
check("fm_rds_250k_1Msamples.iq",
      round(parse_rate_from_filename("fm_rds_250k_1Msamples.iq")[0]), 250_000)
check("recording_2msps.bin",
      round(parse_rate_from_filename("recording_2msps.bin")[0]), 2_000_000)
check("plain signal.iq -> None",
      parse_rate_from_filename("signal.iq"), None)
check("random_data.iq -> None",
      parse_rate_from_filename("random_data.iq"), None)

print("\n=== 2. protocol matching (tight tolerance) ===")
h = match_known_protocol(270_833.0)
check("GSM 270.833k matches", h[0] if h else None, "GSM / GMSK")
h = match_known_protocol(9_600.0)
check("9.6k is VDL2/AIS", h[0] if h else None, "VDL2 / AIS")
check("9.6k +0.4% still matches",
      bool(match_known_protocol(9_638.0)), True)
check("96k (10x the 9.6k standard) declines",
      match_known_protocol(96_000.0), None)
check("271.5k (0.25% off) still matches",
      bool(match_known_protocol(271_500.0)), True)
check("280k (3.4% off) declines", match_known_protocol(280_000.0), None)
check("100k (no standard) declines", match_known_protocol(100_000.0), None)

print("\n=== 3. provenance ranking ===")
r = estimate_sample_rate(None, filepath="signal.iq", user_rate=2e6, user_is_explicit=True)
check("explicit user rate wins", round(r.samp_rate), 2_000_000)
check("  labelled MEASURED", r.confidence, "MEASURED")
check("  source user", r.source, "user")

r = estimate_sample_rate(None, filepath="demo_bpsk_100ksps_1msps.iq")
check("filename token used when no user rate", round(r.samp_rate), 1_000_000)
check("  labelled INFERRED (not measured)", r.confidence, "INFERRED")
check("  source filename", r.source, "filename")

r = estimate_sample_rate(None, filepath="anonymous.iq")
check("nothing available -> ASSUMED", r.confidence, "ASSUMED")

print("\n=== 4. protocol-derived correction ===")
# A GSM capture assumed to be 1 MSps reports R_s=270833 -> matches GSM exactly,
# so f_s stays 1 MSps. Simulate a WRONG assumption of 2 MSps: R_s would then
# read 541666, which matches no standard -> no correction, honest.
sr_wrong = {"locked": True, "symbol_rate_hz": 270_833.0, "samp_rate": 1_000_000.0,
            "samples_per_symbol": 3.69}
r = estimate_sample_rate(None, symbol_rate_result=sr_wrong, filepath="gsm_1msps.iq")
check("GSM match -> source protocol", r.source, "protocol")
check("  computed f_s", round(r.samp_rate), 1_000_000)
check("  labelled MEASURED", r.confidence, "MEASURED")
print(f"       detail: {r.detail}")

# Wrong assumed rate: if f_s were really 500k but we assumed 1M, R_s would read
# 541666 (double). That is not a standard, so we must NOT correct.
sr_dbl = {"locked": True, "symbol_rate_hz": 541_666.0, "samp_rate": 1_000_000.0,
          "samples_per_symbol": 1.85}
r = estimate_sample_rate(None, symbol_rate_result=sr_dbl, filepath="gsm_1msps.iq")
check("non-standard R_s -> falls back to filename", r.source, "filename")

print("\n=== 5. SPS sanity check (catches a renamed file) ===")
ok, msg = check_inconsistency(None, {"locked": True, "samples_per_symbol": 10.0})
check("SPS 10 is fine", ok, True)
ok, msg = check_inconsistency(None, {"locked": True, "samples_per_symbol": 0.5})
check("SPS 0.5 flagged", ok, False)
ok, msg = check_inconsistency(None, {"locked": True, "samples_per_symbol": 9000.0})
check("SPS 9000 flagged", ok, False)

print("\n=== 6. display strings ===")
for rate in (1_000_000, 250_000, 2_500_000_000, 9_600):
    r2 = estimate_sample_rate(None, filepath="x.iq", user_rate=rate, user_is_explicit=True)
    print(f"       {rate:>15,} -> {format_sample_rate(r2):>12s}  |  {format_sample_rate_source(r2)}")

print(f"\n{'ALL PASSED' if fails == 0 else str(fails) + ' FAILURES'}")
sys.exit(1 if fails else 0)
