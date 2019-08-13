import json
import os
from datetime import datetime, timezone
from io import BytesIO
from typing import Tuple

import boto3
from boto3.dynamodb.conditions import Key
from boto3.resources.base import ServiceResource
from botocore.client import BaseClient
from PIL import Image

from logger.get_logger import get_logger

logger = get_logger(__name__)


def main(
        event: dict,
        s3_client: BaseClient = boto3.client('s3'),
        dynamodb_resouce: ServiceResource = boto3.resource('dynamodb')):
    """
    アップロードされた画像を読み込んでmetadataを更新する
    """
    body = get_sns_message_json(event)
    logger.info('MessageJson', body)

    bucket = get_bucket(body)
    key = get_key(body)
    size = get_size(body)
    id = get_id(key)
    raw_bytes = get_image_bytes(bucket, key, s3_client)
    width, height = get_image_resolution(raw_bytes)
    update_option = create_update_option(id, size, width, height)
    update_metadata(update_option, dynamodb_resouce)


def get_sns_message_json(event: dict) -> dict:
    """
    EventからSNSのMessageを取得し、JSONをパースする
    """
    return json.loads(event['Records'][0]['Sns']['Message'])


def get_bucket(event: dict) -> str:
    """
    S3 Bucket名を取得する
    """
    return event['Records'][0]['s3']['bucket']['name']


def get_key(event: dict) -> str:
    """
    S3のKeyを取得する
    """
    return event['Records'][0]['s3']['object']['key']


def get_size(event: dict) -> int:
    """
    S3のObjectの容量を取得する
    """
    return event['Records'][0]['s3']['object']['size']


def get_id(key: str) -> str:
    """
    Keyからid(uuid)を取得する
    """
    return key[7:43]


def get_image_bytes(bucket: str, key: str, s3_client: BaseClient) -> bytes:
    """
    S3から画像のbytesを取得する
    """
    resp = s3_client.get_object(
        Bucket=bucket,
        Key=key
    )
    return resp['Body'].read()


def get_image_resolution(raw_bytes: bytes) -> Tuple[int, int]:
    """
    画像のbytesを読み込んで、画像の横幅と縦幅を取得する
    """
    image = Image.open(BytesIO(raw_bytes))
    return image.size


def create_update_option(
        id: str,
        size: int,
        width: int,
        height: int) -> dict:
    """
    metadataを更新するためのDynamoDBのOptionを生成する
    """
    option = {
        'Key': {
            'id': id
        },
        'ConditionExpression': Key('id').eq(id),
        'ReturnValues': 'ALL_NEW'
    }
    update_attributes = {
        'size': size,
        'width': width,
        'height': height,
        'updatedAt': int(datetime.now(timezone.utc).timestamp() * 1000),
        'isUploaded': True
    }
    update_expression_array = [f'#{x} = :{x}' for x in update_attributes.keys()]
    option['UpdateExpression'] = f'SET {", ".join(update_expression_array)}'
    option['ExpressionAttributeNames'] = {f'#{x}': x for x in update_attributes.keys()}
    option['ExpressionAttributeValues'] = {f':{k}': v for k, v in update_attributes.items()}

    return option


def get_table_name():
    return os.environ['DATA_TABLE_NAME']


def update_metadata(option: dict, dynamodb_resource: ServiceResource) -> dict:
    """
    metadataを更新する
    """
    table = dynamodb_resource.Table(get_table_name())
    resp = table.update_item(**option)
    return resp
