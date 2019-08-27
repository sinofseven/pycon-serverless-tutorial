import json
import os
import re
from datetime import datetime, timezone
from typing import Tuple
from uuid import uuid4

import boto3
from boto3.resources.base import ServiceResource
from botocore.client import BaseClient

from logger.get_logger import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """ValidationでErrorが起きたことを示す自作Errorクラス"""
    pass


def main(event: dict,
         dynamodb_resouce: ServiceResource = boto3.resource('dynamodb'),
         s3_client: BaseClient = boto3.client('s3')) -> Tuple[int, str]:
    """
    Lambdaから呼ぶ処理。
    :param event: Lambdaで受け取ったevent
    :param dynamodb_resouce: DynamoDBのServiceResource。
    :param s3_client: S3のClient
    :return: API Gatewayの統合Proxy用のHTTP Status CodeとBody
    """
    try:
        validate_content_json(event)
        body = get_json_request_body(event)
        filename = get_and_validate_file_name(body)
        id = str(uuid4())
        metadata_item = create_metadata_item(id, filename)
        put_metadata_item(metadata_item, dynamodb_resouce)
        signed_url_info = create_pre_signed_url_for_put(id, filename, s3_client)
        result = {
            'metadata': metadata_item,
            'preSignedUrl': signed_url_info
        }
        return (200, json.dumps(result))
    except ValidationError as e:
        return (400, json.dumps({'message': str(e)}))


def validate_content_json(event: dict) -> None:
    """
    ContentTypeが"application/json"か確かめる
    :param event: Lambdaから渡されたEvent
    """
    try:
        if 'application/json' in event['headers']['Content-Type']:
            return
    except Exception as e:
        logger.warning(f'Exception occurred: {e}', exc_info=True)

    raise ValidationError('ContentType of body is not "application/json".')


def get_json_request_body(event: dict) -> dict:
    """
    eventからRequestBody (JSON)を取得する
    :param event: Lambdaから渡されたEvent
    :return: Parsed Request Body
    """
    try:
        return json.loads(event['body'])
    except Exception as e:
        logger.warning(f'Exception occurred: {e}', exc_info=True)
        raise ValidationError('Request body is not json format.')


def get_and_validate_file_name(body: dict) -> str:
    """
    RequestBodyからfilenameを取得しつつValidationを行う。
    :param body: Parsed Request Body
    :return: filename
    """
    name = body.get('filename')
    if not isinstance(name, str):
        raise ValidationError('filename is not string.')
    if len(re.findall(r'[^a-zA-Z0-9_\-.]', name)) > 0:
        raise ValidationError('filename can use next chars. regex [a-zA-Z0-9_\\-.]')
    return name


def create_metadata_item(id: str, filename: str) -> dict:
    """
    DynamoDBに保存するmetadataを生成する
    :param id: metadataのID
    :param filename: ファイル名
    :return: metadata
    """
    return {
        'id': id,
        'createdAt': int(datetime.now(timezone.utc).timestamp() * 1000),
        'filename': filename,
        'isUploaded': False
    }


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


def put_metadata_item(metadata, dynamodb_resouece):
    """
    metadataをDynamoDBに保存する
    """
    table_name = get_table_name()
    table = dynamodb_resouece.Table(table_name)
    table.put_item(Item=metadata)


def create_pre_signed_url_for_put(id: str, filename: str, s3_client: BaseClient) -> dict:
    """
    アップロード用のPreSignedUrlを生成する
    """
    bucket = get_bucket_name()
    expire = 3600
    method = 'PUT'
    url = s3_client.generate_presigned_url(
        ClientMethod='put_object',
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
