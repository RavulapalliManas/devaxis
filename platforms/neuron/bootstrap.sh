#!/usr/bin/env bash
# Run ON the trn1 box as ubuntu.  Idempotent.  Pattern follows the proven H100 playbook
# (s3://pythia-fork-experiments-434457397267/staging/ops/): code from S3 tarball, provenance
# stamp before anything else, timers from first boot.
set -euo pipefail
S3=s3://pythia-fork-experiments-434457397267/devaxis
END_UTC=${END_UTC:-2026-08-23T11:30:00Z}             # capacity-block termination — box is DESTROYED

echo "=== provenance stamp ==="
IID=$(ec2-metadata --instance-id 2>/dev/null | awk '{print $2}' || curl -s http://169.254.169.254/latest/meta-data/instance-id)
mkdir -p ~/devaxis-work/{runs,gates,logs}
{ date -u; echo "instance=$IID"; uname -a; ls /opt | grep -i neuron || true; } | tee ~/devaxis-work/logs/provenance_boot.txt
aws s3 cp ~/devaxis-work/logs/provenance_boot.txt "$S3/boxlogs/provenance_${IID}_$(date -u +%s).txt"

echo "=== venv (DLAMI-provided; never pip install torch here) ==="
# Prefer the PLAIN torch-neuronx venv; the *_nxd_* variants sort AFTER it and are for
# neuronx-distributed workloads.  Measured on this AMI: aws_neuronx_venv_pytorch_2_8 (torch 2.8).
if [ -d /opt/aws_neuronx_venv_pytorch_2_8 ]; then
  VENV=/opt/aws_neuronx_venv_pytorch_2_8
else
  VENV=$(ls -d /opt/aws_neuronx_venv_pytorch_2* 2>/dev/null | grep -v nxd | sort | tail -1)
fi
test -n "$VENV" || { echo "FATAL: no neuron venv under /opt"; exit 1; }
source "$VENV/bin/activate"
python - <<'EOF'
import torch, torch_neuronx, torch_xla
print("torch", torch.__version__, "| torch-neuronx", torch_neuronx.__version__,
      "| torch-xla", torch_xla.__version__)
EOF

echo "=== code from S3 (pinned tarball built by sync of the git commit) ==="
aws s3 cp "$S3/staging/devaxis.tar.gz" /tmp/devaxis.tar.gz
rm -rf ~/devaxis && mkdir ~/devaxis && tar xzf /tmp/devaxis.tar.gz -C ~/devaxis --strip-components=1
pip -q install -e ~/devaxis
pip freeze | aws s3 cp - "$S3/boxlogs/pipfreeze_${IID}.txt"

echo "=== Neuron env pins (precision + determinism contract) ==="
# Canonical env lives in env.sh — every SSM command sources it (non-interactive shells never
# read .bashrc, and this DLAMI ships /home/ubuntu/.bashrc owned by root anyway).
mkdir -p ~/neuron-cache
cat > ~/devaxis-work/env.sh <<ENV
source $VENV/bin/activate
export NEURON_CC_FLAGS="--auto-cast=none --cache_dir=/home/ubuntu/neuron-cache"
export NEURON_RT_STOCHASTIC_ROUNDING_EN=0
export XLA_NO_SPECIAL_SCALARS=1
export END_UTC=$END_UTC
ENV
sudo chown ubuntu:ubuntu /home/ubuntu/.bashrc 2>/dev/null || true
grep -q devaxis-work/env.sh ~/.bashrc 2>/dev/null || echo "source ~/devaxis-work/env.sh" >> ~/.bashrc || true
aws s3 sync "$S3/compile-cache/" ~/neuron-cache/ --only-show-errors || true

echo "=== timers: 10-min result sync + deadline guard ==="
sudo tee /etc/systemd/system/devaxis-sync.service > /dev/null <<UNIT
[Unit]
Description=devaxis S3 sync
[Service]
Type=oneshot
User=ubuntu
ExecStart=/home/ubuntu/devaxis/platforms/neuron/sync_s3.sh
UNIT
sudo tee /etc/systemd/system/devaxis-sync.timer > /dev/null <<UNIT
[Unit]
Description=devaxis S3 sync every 10 min
[Timer]
OnBootSec=5min
OnUnitActiveSec=10min
[Install]
WantedBy=timers.target
UNIT
sudo tee /etc/systemd/system/devaxis-guard.service > /dev/null <<UNIT
[Unit]
Description=devaxis deadline guard
[Service]
User=ubuntu
Environment=END_UTC=$END_UTC
ExecStart=$VENV/bin/python /home/ubuntu/devaxis/platforms/neuron/deadline_guard.py
Restart=always
[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now devaxis-sync.timer devaxis-guard.service

echo "BOOTSTRAP_COMPLETE $(date -u)"
