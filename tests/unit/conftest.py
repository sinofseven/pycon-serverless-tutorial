import boto3
import pytest

from dynamodb_local import DynamoDBLocal


@pytest.fixture(scope='function')
def dynamodb(request):
    dynamodb_objs = []
    dynamodb_resource = None

    for dynamodb_info in request.param:
        dynamodb_local = DynamoDBLocal(dynamodb_info[0])
        dynamodb_resource = dynamodb_local.dynamodb
        dynamodb_local.create_table()

        # item名が存在しない場合はitemを作成しない。
        if len(dynamodb_info) > 1:
            dynamodb_local.put_items(dynamodb_info[1])

        dynamodb_objs.append(dynamodb_local)

    yield dynamodb_resource

    for dynamodb_obj in dynamodb_objs:
        dynamodb_obj.dynamodb_table.delete()


@pytest.fixture(scope='session')
def s3_client():
    return boto3.client('s3', endpoint_url='http://localhost:4572')


@pytest.fixture(scope='session')
def s3_resource():
    return boto3.resource('s3', endpoint_url='http://localhost:4572')


@pytest.fixture(scope='function')
def set_environ(monkeypatch, request):
    for k, v in request.param.items():
        monkeypatch.setenv(k, v)


@pytest.fixture(scope='function')
def create_s3_bucket(s3_resource, request):
    bucket_name = request.param
    bucket = s3_resource.create_bucket(Bucket=bucket_name)
    yield
    for object_summary in bucket.objects.all():
        object_summary.delete()
    bucket.delete()
