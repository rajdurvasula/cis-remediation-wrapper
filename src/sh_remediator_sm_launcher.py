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
    LOGGER.info(f"Assumed region_session for Account {aws_account_number}")
    return sts_session

def start_workflow(input):
    sm_name = os.environ['sm_name']
    try:
        sfn_client = session.client('stepfunctions')
        paginator = sfn_client.get_paginator('list_state_machines')
        iterator = paginator.paginate()
        sm_arn = ''
        exec_id = date.strftime(datetime.now(), '%Y%m%d%I%M%S')
        for page in iterator:
            for sm in page['stateMachines']:
                if sm['name'] == sm_name:
                    sm_arn = sm['stateMachineArn']
                    break
        LOGGER.info("Invoking StateMachine {} ..".format(sm_name))
        response = sfn_client.start_execution(
            stateMachineArn=sm_arn,
            name=exec_id,
            input=json.dumps(input)
        )
        execArn = response['executionArn']
        LOGGER.info('StateMachine: {} started with Execution ARN: {}'.format(sm_name, execArn))
    except Exception as e:
        print(f'failed in start_execution(..): {e}')
        print(str(e))
    
def get_sh_enabler_event(event):
    if 'detail' in event:
        if 'EventName' in event['detail']:
            if event['detail']['EventName'] == 'SecurityHubEnabled':
                service_detail = event['detail']['serviceEventDetails']
                member_data = service_detail['securityHubEnabledAccount']
                member_account = member_data['member_account']
                member_email = member_data['member_email']
                print('Member Account: %s, Member Email: %s' % (member_account, member_email))
                return  {
                    'member_account': member_account,
                    'member_email': member_email
                }
            else:
                print('Event: \'SecurityHubEnabled\' NOT FOUND')

def prepare_input(event, member_data):
    org_id = os.environ['org_id']
    assume_role_name = os.environ['assume_role']
    master_account = os.environ['master_account']
    home_region = os.environ['home_region']
    master_bucket = os.environ['master_bucket']
    # get member data from event
    member_account = member_data['member_account']
    member_email = member_data['member_email']
    sh_admin_account = os.environ['sh_admin_account']
    member_bucket = os.environ['member_bucket']
    cfn_template_name = os.environ['cfn_template_name']
    return {
        'org_id': org_id,
        'assume_role': assume_role_name,
        'master_account': master_account,
        'home_region': home_region,
        'master_bucket': master_bucket,
        'member_account': member_account,
        'member_email': member_email,
        'sh_admin_account': sh_admin_account,
        'member_bucket': member_bucket,
        'cfn_template_name': cfn_template_name
    }

def lambda_handler(event, context):
    LOGGER.info(f"REQUEST RECEIVED: {json.dumps(event, default=str)}")
    # get member data from event
    # member_account
    # member_email
    member_data = get_sh_enabler_event(event)
    input = prepare_input(event, member_data)
    start_workflow(input)


