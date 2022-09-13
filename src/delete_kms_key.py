import os
import sys
import json
import boto3
import urllib3
import logging
import argparse
from datetime import date, datetime

LOGGER = logging.getLogger()
if 'log_level' in os.environ:
    LOGGER.setLevel(os.environ['log_level'])
    LOGGER.info('Log level set to %s' % LOGGER.getEffectiveLevel())
else:
    LOGGER.setLevel(logging.ERROR)

parser = argparse.ArgumentParser()
parser.add_argument('account_id', help='Member account id')
parser.add_argument('kms_key_alias', help='KMS key alias')

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

def list_kms_keys(member_session):
    try:
        kms_client = member_session.client('kms')
        paginator = kms_client.get_paginator('list_aliases')
        iterator = paginator.paginate()
        for page in iterator:
            for alias in page['Aliases']:
                print(json.dumps(alias, default=json_serial, indent=2))
    except Exception as e:
        print(f'failed in list_aliases(..): {e}')
        print(str(e))

def delete_kms_key(member_session, key_alias):
    try:
        kms_client = member_session.client('kms')
        paginator = kms_client.get_paginator('list_aliases')
        iterator = paginator.paginate()
        for page in iterator:
            for alias in page['Aliases']:
                if alias['AliasName'] == key_alias:
                    key_id = alias['TargetKeyId']
                    print('Key Alias: {} with Key Id: {} found.'.format(key_alias, key_id))
                    response = kms_client.delete_alias(
                        AliasName=key_alias
                    )
                    print(json.dumps(response, default=json_serial, indent=2))
                    response = kms_client.schedule_key_deletion(
                        KeyId=key_id,
                        PendingWindowInDays=7
                    )
                    print(json.dumps(response, default=json_serial, indent=2))
                    break
    except Exception as e:
        print(f'failed in schedule_key_deletion(..): {e}')
        print(str(e))

def main():
    args = parser.parse_args()
    org_id = 'o-a4tlobvmc0'
    role_name = 'AWSControlTowerExecution'
    member_account = args.account_id
    key_alias = args.kms_key_alias
    member_session = assume_role(org_id, member_account, role_name)
    delete_kms_key(member_session, key_alias)

if __name__ == '__main__':
    main()

