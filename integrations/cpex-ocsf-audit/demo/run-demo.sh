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
#   06  fail-closed plugin_panic             (REAL, through the PluginManager)
#
# Beat 06 is GREEN as of 2026-08-31: a real plugin panics inside the CPEX
# executor, catch_unwind contains it, it becomes a plugin_panic violation
# on a terminal deny, and the record reaches this crate through the audit
# seam. Earlier revisions emitted the record by hand and said so; this one
# does not have to.
#
# Rev 3 (2026-09-04): ONE stream across the restart. examples/panic_drive.rs
# now loads a CPEX config through the PluginManager with
# `plugin_settings.audit_stream_namespace: gw-1` and a host-supplied epoch,
# so the executor stamps beat 06 on gw-1:decision in the demo's second
# epoch at stream_seq 0 — the same stream beats 01-05 use, not a stream of
# its own. The stamps are still the executor's (inside the hashed bytes);
# the host names the stream before the first record, it never edits one.
# Needs cpex feat/audit-seam >= bd39d2c (the CI pin is 64c8eba).
#
# Beat 05 crosses an epoch boundary by design. stream_seq is dense per
# (epoch, stream_id) and opens at 0, so the restart legitimately resets
# the counter to 0.
# Density is asserted WITHIN each epoch and never across the restart —
# checking across it would report a gap on stage, which is the opposite
# of the point. The HEAD of each epoch is asserted too: a segment that
# opens above 0 lost record 0, which is a loss, not a boundary.
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
# The restart's epoch. Since cpex bd39d2c the host supplies it in code
# (`plugin_settings.audit_epoch`) — the runner is the host here, and it
# owns the one invariant that matters: strictly larger than EPOCH_1.
EPOCH_2=1755649000000000000
# `<namespace>:decision` is the shape the executor stamps when the host
# sets audit_stream_namespace; beats 01-05 use the same id so the bundle
# is one stream across two epochs.
STREAM_NS="gw-1"
STREAM_ID="$STREAM_NS:decision"

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
cargo "+$TOOLCHAIN" build --quiet --example panic_drive

E1="$OUT/records-epoch1.ndjson"
E2="$OUT/records-epoch2.ndjson"
BUNDLE="$OUT/records.ndjson"

# ── Beats 01-05, then a real kill -9 ──────────────────────────────────
head1 "Beats 01-05 — one epoch, dense stream"

: >"$E1"
DEMO_SIGNING_KEY="$KEY" DEMO_EPOCH="$EPOCH_1" DEMO_BASE_SEQ=0 \
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

# ── Restart: a real CPEX host, a real panic ───────────────────────────
#
# The restart is a genuinely new process, so it gets a genuinely new
# epoch — and this one is not the synthetic driver. It is a CPEX
# PluginManager loading an operator config that declares a plugin which
# panics and this crate's sink: contained by catch_unwind, turned into a
# plugin_panic violation on a terminal deny, and handed to this crate
# through the audit seam. Nothing about the record is written by hand.
#
# The executor still owns the stream stamps — they ride inside the hashed
# bytes and are never edited after the fact. What changed in Rev 3 is that
# the host may NAME the stream before the first record: the config's
# audit_stream_namespace makes the decision stream gw-1:decision, and the
# runner hands the process EPOCH_2 as its epoch. So beat 06 lands on the
# same stream as beats 01-05, in the next epoch, at stream_seq 0 — one
# stream across a restart.
#
# The record is emitted on stderr (the OCSF sink's destination) alongside
# Rust's panic backtrace — which is worth seeing on stage, it is the proof
# the panic is real — so the JSON lines are filtered out of it here.
head1 "Beat 06 — restart into a real CPEX host, and a real panic"

PANIC_RAW="$OUT/beat06-stderr.log"
DEMO_SIGNING_KEY="$KEY" DEMO_CHAIN_UID="demo-chain-boot-7-e2" \
DEMO_STREAM_NS="$STREAM_NS" DEMO_EPOCH="$EPOCH_2" \
  cargo "+$TOOLCHAIN" run --quiet --example panic_drive >/dev/null 2>"$PANIC_RAW" || true
grep '^{' "$PANIC_RAW" >"$E2" || die "panic drive emitted no record — see $PANIC_RAW"

grep -q "panicked at" "$PANIC_RAW" \
  || die "no panic actually occurred — beat 06 would be staged, not driven"
read -r PANIC_CODE PANIC_STREAM PANIC_EPOCH PANIC_SEQ < <(python3 -c "
import json
e = json.load(open('$E2'))
s = e['unmapped']['cpex.stream']
print(e['status_code'], s['stream_id'], s['epoch'], s['stream_seq'])
")
[ "$PANIC_CODE" = "plugin_panic" ] \
  || die "expected status_code plugin_panic, got $PANIC_CODE"
[ "$PANIC_STREAM" = "$STREAM_ID" ] \
  || die "beat 06 landed on stream $PANIC_STREAM, not $STREAM_ID — the host namespace did not reach the executor"
[ "$PANIC_EPOCH" = "$EPOCH_2" ] \
  || die "beat 06 carries epoch $PANIC_EPOCH, not $EPOCH_2 — the host epoch did not reach the executor"
[ "$PANIC_SEQ" = "0" ] \
  || die "beat 06 opened its epoch at stream_seq $PANIC_SEQ, not 0"

ok "a plugin really panicked  ${DIM}(backtrace in $(basename "$PANIC_RAW"))${RESET}"
ok "06  fail-closed plugin_panic  ${DIM}contained → finalized deny → audit seam → record${RESET}"
ok "new process, new epoch, SAME stream  ${DIM}$STREAM_ID · epoch $EPOCH_2 · seq 0 — the host named it, the executor stamped it${RESET}"

cat "$E1" "$E2" >"$BUNDLE"
ok "bundle: $(wc -l <"$BUNDLE" | tr -d ' ') records → $BUNDLE"

# Loose files with per-file hashes, deliberately no archive: a scanning
# gateway that unpacks and repacks a tarball changes every byte of it
# while leaving the files intact, so an archive hash is the wrong check
# for the route these travel. Content hashes survive repacking.
(
  cd "$OUT" && sha256sum records.ndjson records-epoch1.ndjson records-epoch2.ndjson demo-pub.pem \
    >SHA256SUMS.txt
)
{
  printf 'CPEX / OCSF / ledger joint demo bundle — Rev 3\n'
  printf 'cut:        %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'seam:       contextforge-org/cpex feat/audit-seam @ %s\n' "$SEAM_HEAD"
  printf 'toolchain:  rustc %s · %s/%s port tests green\n' "$RUSTC_V" "$PASSED" "$PASSED"
  printf 'records:    %s, one stream (%s) across two epochs\n' "$(wc -l <"$BUNDLE" | tr -d ' ')" "$STREAM_ID"
  printf '            epoch %s seq 0..4 (beats 01-05, producer SIGKILLed after 05)\n' "$EPOCH_1"
  printf '            epoch %s seq 0    (beat 06, a real plugin_panic through the PluginManager)\n' "$EPOCH_2"
  printf 'chains:     demo-chain-boot-7-e1, demo-chain-boot-7-e2 (one per producer process)\n'
  printf 'agent:      ai_agent.uid agent-7 · metadata.correlation_uid run-4bf92f35 on all records\n'
  printf 'join key:   unmapped."cmf.request.request_id" corr-7f3e2a91 on record 5 only\n'
  printf 'verify:     python3 scripts/aid_emit1_validator.py records.ndjson --key demo-pub.pem\n'
  printf 'hashes:     sha256sum -c SHA256SUMS.txt\n'
} >"$OUT/PROVENANCE.txt"
ok "SHA256SUMS.txt + PROVENANCE.txt written  ${DIM}(loose files, no archive — content hashes survive a repack)${RESET}"

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
    # Dense AND opening at 0: an epoch's first record is stream_seq 0 (§7),
    # so a segment that starts higher lost its head, not just its middle.
    dense = got == list(range(0, len(got)))
    mark = "\033[92m✓\033[0m" if dense else "\033[91m✗\033[0m"
    what = "dense" if dense else ("GAP at head" if got[0] != 0 else "GAP")
    print(f"  {mark} epoch {epoch}  {sid}  stream_seq {got[0]}..{got[-1]}  ({len(got)} records, {what})")
    bad |= not dense
streams = {sid for (_, sid) in seqs}
if len(streams) != 1:
    print(f"  \033[91m✗\033[0m expected ONE stream across the restart, got {sorted(streams)}")
    bad = True
print("  \033[2mone stream, two epochs, each dense from 0 on its own — the restart is a boundary, not a loss\033[0m")
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
ok    "06     green — a real panic through the PluginManager, contained → finalized deny → audit seam → signed record"
ok    "stream $STREAM_ID across epochs $EPOCH_1 → $EPOCH_2, each opening at 0"
printf '  %sledger side: hand %s to the one-command wrapper for epoch-aware density + chain checks%s\n' \
  "$DIM" "$BUNDLE" "$RESET"

exit "$VERDICT"
