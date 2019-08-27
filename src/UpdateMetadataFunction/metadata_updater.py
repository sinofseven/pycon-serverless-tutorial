import json
import os
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Tuple
from uuid import UUID

import boto3
from boto3.dynamodb.conditions import Key
from boto3.resources.base import ServiceResource
from botocore.client import BaseClient

from logger.get_logger import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    pass


def default(obj):
    """
    objがDecimalだったらintに変換する
    """
    if isinstance(obj, Decimal):
        return int(obj)
    return obj


def main(
        event: dict,
        dynamodb_resource: ServiceResource = boto3.resource('dynamodb'),
        s3_client: BaseClient = boto3.client('s3')) -> Tuple[int, str]:
    """
    metadataを更新し、画像アップロード用のPreSignedUrlを発行する
    """
    try:
        id = get_id(event)
        validate_id(id)
        metadata = get_a_metadata(id, dynamodb_resource)
        if metadata is None:
            return (404, json.dumps({'message': 'not found'}))
        filename = get_filename(metadata)
        body = get_json_request_body(event)
        if body is not None:
            latest_filename = get_and_validate_file_name(body)
            if latest_filename is not None:
                filename = latest_filename
                option = create_update_option(id, latest_filename)
                metadata = update_metadata(option, dynamodb_resource)
        pre_signed_url = create_pre_signed_url_for_put(id, filename, s3_client)
        result = {
            'metadata': metadata,
            'preSignedUrl': pre_signed_url
        }
        return (200, json.dumps(result, default=default))
    except ValidationError as e:
        return (400, json.dumps({'message': str(e)}))


def get_id(event: dict) -> str:
    """
    PathParameterからIDを取得する
    """
    return event['pathParameters']['id']


def validate_id(id: str) -> None:
    """
    IDの形式がUUIDかどうか確かめる
    """
    try:
        UUID(id)
    except Exception as e:
        logger.warning(f'Exception occurred: {e}', exc_info=True)
        raise ValidationError('id is invalid.')


def get_table_name():
    return os.environ['DATA_TABLE_NAME']


def get_bucket_name():
    return os.environ['DATA_BUCKET_NAME']


def get_a_metadata(id: str, dynamodb_resource: ServiceResource) -> Optional[dict]:
    """
    IDを使って、metadataを取得する
    """
    table = dynamodb_resource.Table(get_table_name())
    resp = table.get_item(
        Key={
            'id': id
        }
    )
    return resp.get('Item')


def get_filename(metadata: dict) -> str:
    """
    metadataからfilenameを取得する
    """
    return metadata['filename']


def get_json_request_body(event: dict) -> Optional[dict]:
    """
    RequestBodyをJSONでパースする。できなかったらnullを返す
    """
    try:
        return json.loads(event['body'])
    except Exception as e:
        logger.warning(f'Exception occurred: {e}', exc_info=True)
    return None


def get_and_validate_file_name(body: dict) -> Optional[str]:
    """
    RequestBodyからfilenameを取得して、validationを行う
    """
    name = body.get('filename')
    if name is None:
        return None
    if not isinstance(name, str):
        raise ValidationError('filename is not string.')
    if len(re.findall(r'[^a-zA-Z0-9_\-.]', name)) > 0:
        raise ValidationError('filename can use next chars. regex [a-zA-Z0-9_\\-.]')
    return name


def create_update_option(id: str, filename: str) -> dict:
    """
    metadataを更新するためのオプションを生成する
    """
    option = {
        'Key': {
            'id': id
        },
        'ConditionExpression': Key('id').eq(id),
        'ReturnValues': 'ALL_NEW'
    }
    update_attributes = {
        'updatedAt': int(datetime.now(timezone.utc).timestamp() * 1000),
        'isUploaded': False,  # filenameが変更になるので未アップロードとみなす
        'filename': filename
    }
    update_expression_array = [f'#{x} = :{x}' for x in update_attributes.keys()]
    option['UpdateExpression'] = f'SET {", ".join(update_expression_array)}'
    option['ExpressionAttributeNames'] = {f'#{x}': x for x in update_attributes.keys()}
    option['ExpressionAttributeValues'] = {f':{k}': v for k, v in update_attributes.items()}

    return option


def update_metadata(option: dict, dynamodb_resource: ServiceResource) -> dict:
    """
    metadataを更新する
    """
    table = dynamodb_resource.Table(get_table_name())
    resp = table.update_item(**option)
    return resp['Attributes']


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
        'method': 'PUT',
        'expiresIn': expire
    }
