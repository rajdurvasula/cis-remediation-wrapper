#!/bin/bash -x
aws cloudformation create-stack --stack-name sh-ops --template-url https://org-sh-ops.s3.amazonaws.com/sh-remediation-ops.yaml --on-failure DO_NOTHING --capabilities CAPABILITY_NAMED_IAM
