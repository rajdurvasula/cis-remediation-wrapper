#!/bin/bash -x
aws s3 rm s3://org-sh-ops/sh-remediation-ops.yaml
aws s3 rm s3://org-sh-ops/sh-remediation-sm.json
aws s3 rm s3://org-sh-ops/sh_remediator.zip
aws s3 rm s3://org-sh-ops/sh_remediator_sm_launcher.zip
aws s3 rm s3://org-sh-ops/sh_ops_bucket.zip
