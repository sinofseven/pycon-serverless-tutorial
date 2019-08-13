import json
import os
from decimal import Decimal
from typing import List, Optional, Tuple
from uuid import UUID

import boto3
from boto3.resources.base import ServiceResource
from botocore.client import BaseClient

from logger.get_logger import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """ValidationでErrorが起きたことを示す自作Errorクラス"""
    pass


def default(obj):
    """objがDecimalの場合、intに変換する"""
    if isinstance(obj, Decimal):
        return int(obj)
    return obj


def main(
        event: dict,
        dynamodb_resource: ServiceResource = boto3.resource('dynamodb'),
        s3_client: BaseClient = boto3.client('s3')) -> Tuple[int, str]:
    """
    metadataを取得する処理
    """
    id = get_id(event)
    if id is None:
        return get_all_metadata(dynamodb_resource, s3_client)
    else:
        return get_a_metadata(id, dynamodb_resource, s3_client)


def get_id(event: dict) -> Optional[str]:
    """
    PathParameterからIDを取得する。PathParameterがなければnullを返す(全件取得とみなす)
    """
    try:
        return event['pathParameters']['id']
    except Exception as e:
        logger.warning(f'Exception occurred: {e}', exc_info=True)
        return None


def validate_id(id: str) -> None:
    """
    IDの形式がUUIDかチェックする
    """
    try:
        UUID(id)
    except Exception as e:
        logger.warning(f'Exception occurred: {e}', exc_info=True)
        raise ValidationError('id is invalid.')


def get_table_name():
    """
    環境変数からDynamoDBのTable名を取得する
    """
    return os.environ['DATA_TABLE_NAME']


def get_bucket_name():
    """
    環境変数からS3のBucket名を取得する
    """
    return os.environ['DATA_BUCKET_NAME']


def get_all_metadata(dynamodb_resource: ServiceResource, s3_client: BaseClient) -> Tuple[int, str]:
    """
    metadata全件取得のレスポンスを作成する
    """
    all_metadata = scan_metadata(dynamodb_resource)
    pre_signed_urls = [
        create_pre_signed_url_for_get(x['id'], x['filename'], s3_client)
        # isUploadedがfalseの場合、アップロードされたファイルがないのでPreSignedUrlを生成しない
        for x in all_metadata if x['isUploaded']
    ]
    result = {
        'metadata': all_metadata,
        'preSignedUrls': pre_signed_urls
    }
    return (200, json.dumps(result, default=default))


def scan_metadata(dynamodb_resource: ServiceResource, last_evaluated_key: Optional[dict] = None) -> List[dict]:
    """
    DynamoDBからmetadataを全件取得する。
    scanではデータ量が多いと一度で取得できない場合があるので、再帰的に処理を行い全件取得するようにしている。
    """
    table = dynamodb_resource.Table(get_table_name())
    option = {}
    if last_evaluated_key is not None:
        option['ExclusiveStartKey'] = last_evaluated_key
    resp = table.scan(**option)
    result = resp.get('Items', [])
    if 'LastEvaluatedKey' in resp:
        result += scan_metadata(dynamodb_resource, last_evaluated_key=resp['LastEvaluatedKey'])
    return result


def create_pre_signed_url_for_get(id: str, filename: str, s3_client: BaseClient) -> dict:
    bucket = get_bucket_name()
    expire = 3600
    method = 'GET'
    url = s3_client.generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': bucket,
            'Key': f'images/{id}/{filename}'
        },
        ExpiresIn=expire,
        HttpMethod=method
    )
    return {
        'id': id,
        'url': url,
        'method': method,
        'expiresIn': expire
    }


def fetch_a_metadata(id: str, dynamodb_resource: ServiceResource) -> Optional[dict]:
    """
    DynamoDBからmetadataを単件取得する。該当するmetadataがなければnullを返す(not found)。
    """
    table = table = dynamodb_resource.Table(get_table_name())
    resp = table.get_item(
        Key={
            'id': id
        }
    )
    return resp.get('Item')


def get_a_metadata(id: str, dynamodb_resource: ServiceResource, s3_client: BaseClient) -> Tuple[int, str]:
    """
    metadataを単件取得する場合のレスポンスを作成する
    """
    try:
        validate_id(id)
        metadata = fetch_a_metadata(id, dynamodb_resource)
        if metadata is None:
            return (404, json.dumps({'message': 'not found'}))
        pre_signed_url = None
        if metadata['isUploaded']:
            pre_signed_url = create_pre_signed_url_for_get(id, metadata['filename'], s3_client)
        result = {
            'metadata': metadata,
            'preSignedUrl': pre_signed_url
        }
        return (200, json.dumps(result, default=default))
    except ValidationError as e:
        return (400, json.dumps({'message': str(e)}))
