# ct-sh-remediation
This automation project creates automation resources to deploy **cis-benchmark-remediation" CloudFormation Stack on Member Accounts

## Instructions
- Use a S3 Bucket on **Master Account**
  - (default) Master S3 Bucket = `org-sh-ops`
- Upload files to Master S3 Bucket
  - sh-remediation-ops.yaml
  - sh-remediation-sm.json
  - src/sh_ops_bucket.zip
  - src/sh_remediator.zip
  - src/sh_remediator_sm_launcher.zip
  - **cis-benchmark-remediation.yaml** 
    > Available in *assets/security/cis-benchmark-remediation* Git folder
- Launch CloudFormation Stack using *sh-remediation-ops.yaml*

### Result
- Following Resources are created
  - IAM Roles for Lambda Functions
  - IAM Role for StepFunction
  - Lambda Functions
    - SHRemediatorSMLauncher
    - SHRemediator
    - SHOpsBucketCopier
  - StateMachine
    - SHRemediatorSM

## Purpose
- The *State Machine* **SHRemediatorSM** when executed deploys the **cis-benchmark-remediation.yaml** Stack in `Home Region` of Member Account
- Alarms corresponding to *Security Hub - CIS Benchmark Findings* are created
- User-provided Email Address is configured to receive *Alert Notifications*

## Event Trigger
- The Lambda function **SHRemediatorSMLauncher** is *triggered* by custom event `SecurityHubEnabled` originated from **SHEnablerSM**
  - **SHEnablerSM** is launched as part of **Control Tower Account Enrolment** `post-processing` automation
  - The JSON provided below is composed by Lambda **sh_remediator_sm_launcher** and *State Machine* **SHRemediatorSM** is launched

## Steps to Execute CIS Remediation / Alarms / Notifications
- These are the steps to manually execute the *State Machine* **SHRemediatorSM**
- CloudFormation Template **cis-benchmark-remediation.yaml** Must exist in the *Master S3 Bucket*
- Navigate to *Step Functions* -> *SHRemediatorSM*
- Start Execution by passing *Input JSON*
  - Make sure *member_account* is correct
  - Specify a valid value for *member_email* key
  - **sh_admin_account** is the Audit Account Id
  - **member_bucket** value will be appended with Timestamp during execution of StateMachine
  - Use the JSON below and change the values as required:
  ```
    {
        "org_id": "o-a4tlobvmc0",
        "assume_role": "AWSControlTowerExecution",
        "master_account": "538857479523",
        "home_region": "us-east-1",
        "master_bucket": "org-sh-ops",
        "member_account": "172489758104",
        "member_email": "bhupesh.gupta@org.com",
        "sh_admin_account": "413157014023",
        "member_bucket": "sh-172489758104-ops",
        "cfn_template_name": "cis-benchmark-remediation.yaml"
    }
  ```
### Result
- On successful execution of *State Machine* **SHRemediatorSM**, the status shows as **Succeeded**
- Verify Alarms, SNS Topic, Subscription are created in Member Account in all Regions

## State Machine
The diagram below represents the *State Machine* **SHRemediatorSM**:
![sh_remediator.png](./sh_remediator.png?raw=true)

The states in the *State Machine* are: 
- State 1:
  - Create S3 Bucket on Member Account
  - Create S3 Bucket Policy on S3 Bucket
  - Copy *cis-benchmark-remediation.yaml* to Member S3 Bucket
  - Get CT-governed regions
- State 2:
  - In Home Region, in the Member Account, Launch CloudFormation Stack from *cis-benchmark-remediation.yaml*

