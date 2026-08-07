# Morning checklist — devaxis

## 1. Read the report (one command, everything in it)

```bash
aws s3 cp s3://pythia-fork-experiments-434457397267/devaxis/MORNING_REPORT.md - --region us-east-1
```

Contains: platform gates, factorial per-cell Kaplan-Meier medians + Holm-corrected log-rank vs
baseline, branch-matrix deprivation/rescue table, tau dose-response, DD10, and every failed run.
Comparisons are SUPPRESSED for anything not fully terminal — a table is read, a caveat is not.

## 2. If the report is missing or thin, check the program

```bash
aws ssm send-command --region us-east-1 --instance-ids i-0c6939e339ff4192e \
  --document-name AWS-RunShellScript \
  --parameters 'commands=["systemctl is-active devaxis-overnight devaxis-wave devaxis-branch devaxis-guard","tail -20 /home/ubuntu/devaxis-work/logs/overnight.log"]' \
  --query Command.CommandId --output text
# then: aws ssm get-command-invocation --region us-east-1 --command-id <ID> \
#   --instance-id i-0c6939e339ff4192e --query StandardOutputContent --output text
```

## 3. Raw artifacts

- run records: `s3://pythia-fork-experiments-434457397267/devaxis/runs/{factorial,branch,tau,dd10}/`
- gates: `.../devaxis/gates/` (q0_preflight, q2_q3, dd_result)
- code: github.com/RavulapalliManas/devaxis (LEDGER.md is the running record)

## 4. Deadline that matters

The capacity block TERMINATES **2026-08-23 11:30 UTC** and destroys local disk. Only S3
survives. `devaxis-guard` force-syncs at T-2h and T-30m; nothing else is needed.
