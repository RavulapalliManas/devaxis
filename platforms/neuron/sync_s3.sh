#!/usr/bin/env bash
# One-writer rule: ONLY this script (via the systemd timer / guard) writes the devaxis S3
# prefix from the box.  Runs, gates, logs every cycle; compile cache too (cheap, saves hours
# on any relaunch).
set -uo pipefail
S3=s3://pythia-fork-experiments-434457397267/devaxis
W=${DEVAXIS_WORK:-/home/ubuntu/devaxis-work}
cd "$W" || exit 1
aws s3 sync runs/  "$S3/runs/"  --only-show-errors
aws s3 sync gates/ "$S3/gates/" --only-show-errors
aws s3 sync logs/  "$S3/boxlogs/" --only-show-errors
aws s3 sync /home/ubuntu/neuron-cache/ "$S3/compile-cache/" --only-show-errors
