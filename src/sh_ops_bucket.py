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

def create_bucket_if_not_exists(member_session, bucket_name):
    bucket_found = False
    try:
        s3_client = member_session.client('s3')
        response = s3_client.list_buckets()
        for bucket in response['Buckets']:
            if bucket['Name'] == bucket_name:
                bucket_found = True
                break
    except Exception as e:
        print(f'failed in list_buckets(..): {e}')
        print(str(e))
        raise e
    if not bucket_found:
        print('Bucket: {} not found. Create it.'.format(bucket_name))
        public_access_block = {
            'BlockPublicAcls': True,
            'IgnorePublicAcls': True,
            'BlockPublicPolicy': True,
            'RestrictPublicBuckets': True
        }
        try:
            s3_client = member_session.client('s3')
            response = s3_client.create_bucket(
                ACL='private',
                Bucket=bucket_name,
                ObjectOwnership='BucketOwnerPreferred')
            print('Bucket: {} created at Location: {}'.format(bucket_name, response['Location']))
            s3_client.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration=public_access_block
            )
            print('Public Access Blocked for Bucket: {}.'.format(bucket_name))
            bucket_found = True
            print('Bucket: {} created.'.format(bucket_name))
        except Exception as e:
            print(f'failed in create_bucket(..): {e}')
            print(str(e))
            raise e
    return bucket_found

def create_cross_account_bucket_policy(member_session, member_account, master_account, sh_role_name, bucket_name):
    bucket_policy = {
        'Version': '2012-10-17',
        'Id': 'bucket-policy-'+member_account,
        'Statement': [
            {
                'Sid': 'stmt-put-bucket-objects',
                'Effect': 'Allow',
                'Principal': {
                    'AWS': 'arn:aws:iam::'+master_account+':role/'+sh_role_name
                },
                'Action': [
                    's3:PutObject'
                ],
                'Resource': [
                    'arn:aws:s3:::'+bucket_name+'/*'
                ],
                'Condition': {
                    'StringEquals': {
                        's3:x-amz-acl': 'bucket-owner-full-control'
                    }
                }
            },
            {
                'Sid': 'stmt-list-bucket',
                'Effect': 'Allow',
                'Principal': {
                    'AWS': 'arn:aws:iam::'+master_account+':role/'+sh_role_name
                },
                'Action': [
                    's3:ListBucket'
                ],
                'Resource': [
                    'arn:aws:s3:::'+bucket_name
                ]
            }
        ]
    }
    try:
        s3_client = member_session.client('s3')
        s3_client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(bucket_policy)
        )
        print('Bucket Policy added')
    except Exception as e:
        print(f'failed in put_bucket_policy(..): {e}')
        print(str(e))
        raise e

def upload_template(master_session, bucket_name, cfn_template_name):
    try:
        s3_client = master_session.client('s3')
        with open('./test.yaml', 'rb') as r:
            s3_client.upload_fileobj(r, bucket_name, cfn_template_name)
        r.close()
    except Exception as e:
        print(f'failed in upload_fileobj(..): {e}')
        print(str(e))
        raise e

def download_template(master_session, cfn_template_name):
    try:
        s3_client = master_session.client('s3')
        with open('test.yaml', 'wb') as t:
            s3_client.download_fileobj('org-sh-ops', cfn_template_name, t)
        t.close()
    except Exception as e:
        print(f'failed in download_fileobj(..): {e}')
        print(str(e))
        raise e

def copy_template(master_session, source_bucket, target_bucket, cfn_template_name):
    try:
        source_bucket = {
            'Bucket': source_bucket,
            'Key': cfn_template_name
        }
        s3_client = master_session.client('s3')
        s3_client.copy_object(
            ACL='bucket-owner-full-control',
            Bucket=target_bucket,
            CopySource=source_bucket,
            Key=cfn_template_name)
        print('CFN Template: {} copied to Bucket: {}'.format(cfn_template_name, target_bucket))
    except Exception as e:
        print(f'failed in copy_object(..): {e}')
        print(str(e))
        raise e

def get_ct_regions(account_id):
    # use CT session
    cf_client = session.client('cloudformation')
    region_set = set()
    try:
        # stack instances are outdated
        paginator = cf_client.get_paginator('list_stack_instances')
        iterator = paginator.paginate(StackSetName='AWSControlTowerBP-BASELINE-CLOUDWATCH',
            StackInstanceAccount=account_id)
        for page in iterator:
            for summary in page['Summaries']:
                region_set.add(summary['Region'])
    except Exception as ex:
        LOGGER.warning("Control Tower StackSet not found in this Region")
        LOGGER.warning(str(ex))
    LOGGER.info(f"Control Tower Regions: {list(region_set)}")
    return list(region_set)

#def main():
#    org_id = 'o-a4tlobvmc0'
#    role_name = 'AWSControlTowerExecution'
#    master_account = '538857479523'
#    member_account = '172489758104'
#    sh_admin_account = '413157014023'
#    bucket_name = 'sh-'+member_account+'-ops'
#    cfn_template_name = 'cis-benchmark-remediation.yaml'
#    sh_regions = get_ct_regions(sh_admin_account)
#    master_session = assume_role(org_id, master_account, role_name)
#    member_session = assume_role(org_id, member_account, role_name)
#    create_bucket_if_not_exists(member_session, bucket_name)
#    create_cross_account_bucket_policy(member_session, member_account, master_account, role_name, bucket_name)
#    copy_template(master_session, bucket_name, cfn_template_name)
    #download_template(master_session, cfn_template_name)
    #upload_template(master_session, bucket_name, cfn_template_name)
    
def lambda_handler(event, context):
    LOGGER.info(f"REQUEST RECEIVED: {json.dumps(event, default=str)}")
    org_id = event['org_id']
    role_name = event['assume_role']
    master_account = event['master_account']
    home_region = event['home_region']
    master_bucket = event['master_bucket']
    member_account = event['member_account']
    member_email = event['member_email']
    sh_admin_account = event['sh_admin_account']
    member_bucket = event['member_bucket']
    member_bucket = '{}-{}'.format(member_bucket, datetime.strftime(datetime.now(), '%Y%m%d%H%M%S'))
    cfn_template_name = event['cfn_template_name']
    # not required to launch CloudFormation stack in all CT-governed regions on Member Account
    # Run in home_region
    # Because aws-controltower/CloudTrailLogs is in Home Region of Member Account
    #sh_regions = get_ct_regions(sh_admin_account)
    master_session = assume_role(org_id, master_account, role_name)
    member_session = assume_role(org_id, member_account, role_name)
    create_bucket_if_not_exists(member_session, member_bucket)
    create_cross_account_bucket_policy(member_session, member_account, master_account, role_name, member_bucket)
    copy_template(master_session, master_bucket, member_bucket, cfn_template_name)
    #sh_ops_regions = []
    #for region in sh_regions:
    #    sh_ops_regions.append({
    return {
        'org_id': org_id,
        'assume_role': role_name,
        'member_account': member_account,
        'master_bucket': master_bucket,
        'member_email': member_email,
        'member_region': home_region,
        'member_bucket': member_bucket,
        'cfn_template_name': cfn_template_name
    }
    #return sh_ops_regions


#if __name__ == '__main__':
#    main()
