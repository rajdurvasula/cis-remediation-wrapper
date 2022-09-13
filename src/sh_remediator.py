import email
import os
import sys
import json
import boto3
import urllib3
import logging
from datetime import date, datetime

LOGGER = logging.getLogger()
if 'log_level' in os.environ:
    LOGGER.setLevel(os.environ['log_level'])
    LOGGER.info('Log level set to %s' % LOGGER.getEffectiveLevel())
else:
    LOGGER.setLevel(logging.ERROR)

session = boto3.Session()

def json_serial(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError('Type %s not serializable' % type(obj))

def assume_role(org_id, aws_account_number, role_name):
    sts_client = boto3.client('sts')
    partition = sts_client.get_caller_identity()['Arn'].split(":")[1]
    response = sts_client.assume_role(
        RoleArn='arn:%s:iam::%s:role/%s' % (
            partition, aws_account_number, role_name
        ),
        RoleSessionName=str(aws_account_number+'-'+role_name),
        ExternalId=org_id
    )
    sts_session = boto3.Session(
        aws_access_key_id=response['Credentials']['AccessKeyId'],
        aws_secret_access_key=response['Credentials']['SecretAccessKey'],
        aws_session_token=response['Credentials']['SessionToken']
    )
    role_arn = response['AssumedRoleUser']['Arn']
    LOGGER.info(f"Assumed region_session for Account {aws_account_number}")
    return sts_session, role_arn

def launch_stack(member_session, event, role_arn):
    try:
        member_account = event['member_account']
        member_email = event['member_email']
        member_region = event['member_region']
        cfn_template_bucket = event['member_bucket']
        cfn_template_file = event['cfn_template_name']
        stack_name = 'SHRemediator-{}'.format(member_account)
        template_url = 'https://{}.s3.amazonaws.com/{}'.format(cfn_template_bucket, cfn_template_file)
        cfn_client = member_session.client('cloudformation',
            endpoint_url=f"https://cloudformation.{member_region}.amazonaws.com", 
            region_name=member_region)
        cfn_params = []
        admin_arn_param = {
            'ParameterKey': 'AdministratorARN',
            'ParameterValue': role_arn
        }
        email_param = {
            'ParameterKey': 'AdminSNSNotificationEmailAddress',
            'ParameterValue': member_email
        }
        cfn_params.append(admin_arn_param)
        cfn_params.append(email_param)
        response = cfn_client.create_stack(
            StackName=stack_name,
            TemplateURL=template_url,
            Parameters=cfn_params,
            Capabilities=[ 'CAPABILITY_NAMED_IAM' ],
            OnFailure='DO_NOTHING'
        )
        print('SecurityHub Remediation Stack launched with Id: {}'.format(response['StackId']))
        return response['StackId']
    except Exception as e:
        print(f'failed in create_stack(..): {e}')
        print(str(e))

def lambda_handler(event, context):
    LOGGER.info(f"REQUEST RECEIVED: {json.dumps(event, default=str)}")
    org_id = event['org_id']
    assume_role_name = event['assume_role']
    member_account = event['member_account']
    member_email = event['member_email']
    member_region = event['member_region']
    cfn_template_bucket = event['member_bucket']
    cfn_template_name = event['cfn_template_name']
    member_session, role_arn = assume_role(org_id, member_account, assume_role_name)
    stack_id = launch_stack(member_session, event, role_arn)
    remediator_response = {
        'org_id': org_id,
        'assume_role': assume_role_name,
        'member_account': member_account,
        'member_email': member_email,
        'member_region': member_region,
        'member_bucket': cfn_template_bucket,
        'cfn_template_name': cfn_template_name,
        'stack_id': stack_id
    }
    return remediator_response

