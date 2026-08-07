#!/usr/bin/env bash
# Launch the devaxis trn1.32xlarge into Sam's idle capacity block.
# Dry-run VERIFIED 2026-08-07 ("Request would have succeeded") with exactly these parameters;
# the one non-obvious flag is --instance-market-options MarketType=capacity-block, without which
# AWS rejects any launch into a capacity-block reservation.
#
# Usage:  DRY=0 bash launch_trn1.sh          (DRY=1 default: dry-run only)
set -euo pipefail

REGION=us-east-1
CR_ID=${CR_ID:-cr-0d45dc9efdb38c384}                 # Sam's idle block, dies 2026-08-23 11:30Z
AMI=${AMI:-ami-0fd664467b3cf8dfd}                    # Deep Learning AMI Neuron (Ubuntu 22.04) 20260227
SUBNET=${SUBNET:-subnet-05702a0e006064b84}           # default-VPC us-east-1c (use1-az4 = CR AZ)
KEY=${KEY:-perseus-trainium-dev-20260717}
PROFILE=${PROFILE:-perseus-eval-worker}              # S3 role for pythia-fork-experiments bucket
DRY=${DRY:-1}

FLAGS=()
[ "$DRY" = "1" ] && FLAGS+=(--dry-run)

aws ec2 run-instances "${FLAGS[@]}" --region "$REGION" \
  --image-id "$AMI" --instance-type trn1.32xlarge --count 1 \
  --instance-market-options MarketType=capacity-block \
  --capacity-reservation-specification "CapacityReservationTarget={CapacityReservationId=$CR_ID}" \
  --subnet-id "$SUBNET" \
  --iam-instance-profile "Name=$PROFILE" \
  --key-name "$KEY" \
  --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=200,VolumeType=gp3}' \
  --tag-specifications \
    'ResourceType=instance,Tags=[{Key=Name,Value=devaxis-trn1},{Key=Project,Value=devaxis},{Key=Owner,Value=Manas},{Key=perseus:production-authority,Value=false}]' \
  --query 'Instances[0].[InstanceId,PrivateIpAddress]' --output text
