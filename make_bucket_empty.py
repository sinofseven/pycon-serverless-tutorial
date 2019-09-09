import boto3
import os


def get_outputs(stack_name):
    cfn = boto3.client('cloudformation')
    resp = cfn.describe_stacks(StackName=stack_name)
    if 'Stacks' not in resp or len(resp['Stacks']) == 0:
        return {}
    return {
        x['OutputKey']: x['OutputValue']
        for x in resp['Stacks'][0].get('Outputs', [])
    }


def to_empty(bucket_name):
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)
    for file in bucket.objects.all():
        file.delete()


stack_name = os.environ['STACK_NAME']

outpus = get_outputs(stack_name)

bucket_name = outpus['DataBucketName']
to_empty(bucket_name)
