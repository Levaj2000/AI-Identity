#!/usr/bin/env bash
# Audit that the default VPC does NOT have internet-exposed SSH / RDP rules.
#
# GCP projects are sometimes provisioned with auto-generated rules that open
# tcp:22 (default-allow-ssh) and tcp:3389 (default-allow-rdp) to 0.0.0.0/0.
# These rules target any VM in the default network and can silently expose
# future workloads. They were verified removed on 2026-04-15 as part of
# sprint item #245.
#
# This script exits non-zero if either rule reappears, so it can be wired
# into CI or run manually before audits.
#
# Usage:
#   scripts/audit-default-vpc.sh [PROJECT_ID]

set -euo pipefail

PROJECT_ID="${1:-project-8bbb04f8-fda8-462e-bc2}"
FORBIDDEN=(default-allow-ssh default-allow-rdp)

echo "→ project: $PROJECT_ID"
echo "→ checking forbidden default VPC firewall rules..."

failed=0
for rule in "${FORBIDDEN[@]}"; do
  if gcloud compute firewall-rules describe "$rule" --project="$PROJECT_ID" >/dev/null 2>&1; then
    echo "✗ FAIL: $rule exists and is forbidden (0.0.0.0/0 exposure)"
    echo "        remove with: gcloud compute firewall-rules delete $rule --project=$PROJECT_ID --quiet"
    failed=1
  else
    echo "✓ $rule absent"
  fi
done

if [[ $failed -ne 0 ]]; then
  echo
  echo "✗ default VPC audit failed"
  exit 1
fi

echo
echo "✓ default VPC audit passed"
