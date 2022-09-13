#!/bin/bash -x
aws s3 cp sh-remediation-ops.yaml s3://org-sh-ops/
aws s3 cp sh-remediation-sm.json s3://org-sh-ops/
aws s3 cp src/sh_remediator.zip s3://org-sh-ops/
aws s3 cp src/sh_remediator_sm_launcher.zip s3://org-sh-ops/
aws s3 cp src/sh_ops_bucket.zip s3://org-sh-ops/
