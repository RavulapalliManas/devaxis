#!/usr/bin/env bash
# Launch the devaxis trn1.32xlarge into Sam's idle capacity block.
# Dry-run VERIFIED 2026-08-07 ("Request would have succeeded") with exactly these parameters;
# the one non-obvious flag is --instance-market-options MarketType=capacity-block, without which
# AWS rejects any launch into a capacity-block reservation.
#
# Usage:  DRY=0 bash launch_trn1.sh          (DRY=1 default: dry-run only)
# ACCESS MODEL (verified 2026-08-07): primary ops path is SSM send-command — the instance
# profile perseus-eval-worker carries AmazonSSMManagedInstanceCore, so no SSH key or SG rule is
# required for scripted operation (same pattern as the H100 playbook):
#   aws ssm send-command --region us-east-1 --instance-ids "$IID" \
#     --document-name AWS-RunShellScript --parameters commands='["sudo -u ubuntu bash /home/ubuntu/devaxis/platforms/neuron/bootstrap.sh"]'
#   aws ssm get-command-invocation --region us-east-1 --command-id ... --instance-id "$IID"
# A fresh key pair devaxis-trn1 is created at launch as interactive backup (the pre-existing
# perseus-trainium-dev-20260717 key pair's private half is NOT held here — it is not usable).
set -euo pipefail

REGION=us-east-1
CR_ID=${CR_ID:-cr-0d45dc9efdb38c384}                 # Sam's idle block, dies 2026-08-23 11:30Z
AMI=${AMI:-ami-0fd664467b3cf8dfd}                    # Deep Learning AMI Neuron (Ubuntu 22.04) 20260227
SUBNET=${SUBNET:-subnet-05702a0e006064b84}           # default-VPC us-east-1c (use1-az4 = CR AZ)
KEY=${KEY:-devaxis-trn1}
PROFILE=${PROFILE:-perseus-eval-worker}              # S3 + SSM role
DRY=${DRY:-1}

if [ "$DRY" != "1" ]; then
  aws ec2 describe-key-pairs --region "$REGION" --key-names "$KEY" >/dev/null 2>&1 || {
    aws ec2 create-key-pair --region "$REGION" --key-name "$KEY" \
      --query KeyMaterial --output text > "$HOME/.ssh/${KEY}.pem"
    chmod 600 "$HOME/.ssh/${KEY}.pem"
    echo "created key pair $KEY -> ~/.ssh/${KEY}.pem"
  }
fi

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
