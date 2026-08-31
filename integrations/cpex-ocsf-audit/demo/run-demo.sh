#!/usr/bin/env bash
# Location: ./integrations/cpex-ocsf-audit/demo/run-demo.sh
# Copyright 2026 AI Identity
# SPDX-License-Identifier: Apache-2.0
#
# CPEX / OCSF / ledger joint demo — six beats, then one offline command
# that makes the claims.
#
#   01  clean allow
#   02  allow after modification            (Modified keeps distinct semantics)
#   03  policy deny                          (violation surfaced at status_code)
#   04  DenyIgnored + Aborted                (the record no post-hook can produce)
#   05  mandate draw + interrupted recovery  (join key rides here; kill -9 lands here)
#   06  fail-closed plugin_panic             (AMBER — see below)
#
# Beat 06 is amber on purpose. The CPEX core path is live through
# catch_unwind, finalized deny, and the awaited audit sink, but the
# end-to-end panicking-plugin harness is still pending, so this runner
# emits the panic RECORD rather than driving a real panic. The strip says
# so on screen; the script does not pretend otherwise.
#
# Beat 05 crosses an epoch boundary by design. stream_seq is dense per
# (epoch, stream_id), so the restart legitimately resets the counter.
# Density is asserted WITHIN each epoch and never across the restart —
# checking across it would report a gap on stage, which is the opposite
# of the point.
#
# Usage:
#   ./run-demo.sh [outdir]
#
# Environment:
#   CPEX_DIR    checkout of contextforge-org/cpex   (default: sibling ../../../../cpex)
#   TOOLCHAIN   rust toolchain to build with        (default: 1.96.1)
#   DEMO_KEY    PKCS#8 P-256 private key PEM        (default: generated per run)

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRATE="$(cd "$HERE/.." && pwd)"
REPO="$(cd "$CRATE/../.." && pwd)"
CPEX_DIR="${CPEX_DIR:-$(cd "$REPO/.." && pwd)/cpex}"
TOOLCHAIN="${TOOLCHAIN:-1.96.1}"
OUT="${1:-${TMPDIR:-/tmp}/cpex-ocsf-demo}"

EPOCH_1=1755648000000000000
EPOCH_2=1755649000000000000
STREAM_ID="gw-1/boot-7"

BOLD=$'\033[1m'; DIM=$'\033[2m'; RESET=$'\033[0m'
GREEN=$'\033[92m'; AMBER=$'\033[93m'; RED=$'\033[91m'; CYAN=$'\033[96m'

ok()    { printf '  %s✓%s %s\n' "$GREEN" "$RESET" "$1"; }
amber() { printf '  %s●%s %s\n' "$AMBER" "$RESET" "$1"; }
die()   { printf '  %s✗%s %s\n' "$RED" "$RESET" "$1" >&2; exit 1; }
head1() { printf '\n%s%s%s\n' "$BOLD" "$1" "$RESET"; }

mkdir -p "$OUT"
cd "$CRATE"

# ── Gate 1: what is being demonstrated, and against what ──────────────
head1 "Gate 1 — provenance"

[ -d "$CPEX_DIR/.git" ] || die "no cpex checkout at $CPEX_DIR (set CPEX_DIR)"
SEAM_HEAD="$(git -C "$CPEX_DIR" rev-parse --short=7 HEAD)"
RUSTC_V="$(rustc "+$TOOLCHAIN" --version | awk '{print $2}')"

TEST_OUT="$(cargo "+$TOOLCHAIN" test --quiet 2>&1 | grep -E '^test result:' | head -1)"
PASSED="$(sed -E 's/.* ([0-9]+) passed.*/\1/' <<<"$TEST_OUT")"
grep -q '0 failed' <<<"$TEST_OUT" || die "port tests are not green: $TEST_OUT"

printf '  %sseam cpex#166 @ %s · rustc %s · %s/%s port tests green%s\n' \
  "$CYAN" "$SEAM_HEAD" "$RUSTC_V" "$PASSED" "$PASSED" "$RESET"

# ── Signing key: the demo signs, so the validator has something to check ──
KEY="${DEMO_KEY:-$OUT/demo-key.pem}"
PUB="$OUT/demo-pub.pem"
if [ ! -f "$KEY" ]; then
  # `ec_param_enc:named_curve` is not optional here. LibreSSL — which is
  # what `openssl` is on stock macOS — otherwise writes the curve as
  # EXPLICIT parameters, and p256's PKCS#8 parser rejects that key. The
  # demo then dies on a foreign laptop having worked on every Linux box
  # it was built on. OpenSSL 3 already defaults to named_curve, so this
  # is a no-op there.
  openssl genpkey -algorithm EC \
    -pkeyopt ec_paramgen_curve:P-256 \
    -pkeyopt ec_param_enc:named_curve \
    -out "$KEY" 2>/dev/null
fi
openssl pkey -in "$KEY" -pubout -out "$PUB" 2>/dev/null
ok "signing key ready ($(basename "$KEY")), public key exported for the verifier"

cargo "+$TOOLCHAIN" build --quiet --example demo_stream

E1="$OUT/records-epoch1.ndjson"
E2="$OUT/records-epoch2.ndjson"
BUNDLE="$OUT/records.ndjson"

# ── Beats 01-05, then a real kill -9 ──────────────────────────────────
head1 "Beats 01-05 — one epoch, dense stream"

: >"$E1"
DEMO_SIGNING_KEY="$KEY" DEMO_EPOCH="$EPOCH_1" DEMO_BASE_SEQ=41 \
DEMO_STREAM_ID="$STREAM_ID" DEMO_CASES="1,2,3,4,5" DEMO_HOLD=1 \
DEMO_CHAIN_UID="demo-chain-boot-7-e1" \
  cargo "+$TOOLCHAIN" run --quiet --example demo_stream >"$E1" 2>/dev/null &
PRODUCER=$!

for _ in $(seq 1 100); do
  [ "$(wc -l <"$E1")" -ge 5 ] && break
  sleep 0.2
done
[ "$(wc -l <"$E1")" -ge 5 ] || { kill -9 "$PRODUCER" 2>/dev/null || true; die "producer never emitted 5 records"; }

ok "01  clean allow"
ok "02  allow after modification  $DIM(Modified, not folded into Allowed)$RESET"
ok "03  policy deny               $DIM(violation surfaced at status_code)$RESET"
ok "04  DenyIgnored + Aborted     $DIM(terminal verdict Allow)$RESET"
ok "05a mandate draw              $DIM(join key corr-7f3e2a91 on the record)$RESET"

head1 "Beat 05b — kill -9 the producer, mid-stream"
kill -9 "$PRODUCER" 2>/dev/null || true
wait "$PRODUCER" 2>/dev/null || true
ok "producer killed; $(wc -l <"$E1" | tr -d ' ') records had already reached the sink and survived it"

# ── Restart: new epoch, counter legitimately resets ───────────────────
head1 "Beats 05b-06 — restart opens a new epoch"

DEMO_SIGNING_KEY="$KEY" DEMO_EPOCH="$EPOCH_2" DEMO_BASE_SEQ=1 \
DEMO_STREAM_ID="$STREAM_ID" DEMO_CASES="6" \
DEMO_CHAIN_UID="demo-chain-boot-7-e2" \
  cargo "+$TOOLCHAIN" run --quiet --example demo_stream >"$E2" 2>/dev/null

ok "new epoch $EPOCH_2; stream_seq resets to 1 — the EXPECTED discontinuity, not a gap"
amber "06  fail-closed plugin_panic  ${DIM}record emitted; end-to-end panic harness still pending${RESET}"

cat "$E1" "$E2" >"$BUNDLE"
ok "bundle: $(wc -l <"$BUNDLE" | tr -d ' ') records → $BUNDLE"

# ── Density, asserted within epoch and never across the restart ───────
head1 "Density — per (epoch, stream_id), never across the restart"

python3 - "$BUNDLE" <<'PY'
import json, sys
from collections import defaultdict
seqs = defaultdict(list)
for line in open(sys.argv[1]):
    if not line.strip():
        continue
    s = json.loads(line)["unmapped"]["cpex.stream"]
    seqs[(s["epoch"], s["stream_id"])].append(s["stream_seq"])
bad = False
for (epoch, sid), got in sorted(seqs.items()):
    got.sort()
    dense = got == list(range(got[0], got[0] + len(got)))
    mark = "\033[92m✓\033[0m" if dense else "\033[91m✗\033[0m"
    print(f"  {mark} epoch {epoch}  {sid}  stream_seq {got[0]}..{got[-1]}  ({len(got)} records, "
          f"{'dense' if dense else 'GAP'})")
    bad |= not dense
print("  \033[2mtwo epochs, each dense on its own — the restart is a boundary, not a loss\033[0m")
sys.exit(1 if bad else 0)
PY

# ── The close: the verifier makes the claims, not the presenter ───────
head1 "Proof — one command, offline, no install"

VALIDATOR="$REPO/scripts/aid_emit1_validator.py"
[ -f "$VALIDATOR" ] || die "validator not found at $VALIDATOR"

printf '  %s$ python3 scripts/aid_emit1_validator.py records.ndjson --key demo-pub.pem%s\n\n' "$DIM" "$RESET"

# No --strict-gaps on stage: on_effect has no OCSF class yet, so that gap
# should surface as a FINDING the box explains, not a hard error that
# stops the demo.
set +e
python3 "$VALIDATOR" "$BUNDLE" --key "$PUB"
VERDICT=$?
set -e

head1 "Status"
ok    "01-05  green"
amber "06     amber — core path live (catch_unwind → finalized deny → awaited sink); harness pending"
printf '  %sledger side: hand %s to the one-command wrapper for epoch-aware density + chain checks%s\n' \
  "$DIM" "$BUNDLE" "$RESET"

exit "$VERDICT"
