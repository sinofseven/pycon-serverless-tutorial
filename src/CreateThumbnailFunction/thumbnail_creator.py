import json
import os
from datetime import datetime, timezone
from io import BytesIO

import boto3
from boto3.dynamodb.conditions import Key
from boto3.resources.base import ServiceResource
from botocore.client import BaseClient
from PIL import Image


def main(
        event: dict,
        s3_client: BaseClient = boto3.client('s3'),
        dynamodb_resouce: ServiceResource = boto3.resource('dynamodb')) -> None:
    """
    Lambdaから呼ぶ処理
    :param event: Lambdaで受け取ったevent
    :param s3_client: S3のClient
    :param dynamodb_resouce: DynamoDBのServiceResource。
    """
    body = get_sns_message_json(event)

    bucket = get_bucket(body)
    key = get_key(body)
    id = get_id(key)
    filename = os.path.basename(key)
    name, ext = os.path.splitext(filename)

    update_db_option = create_update_db_option(id)

    image = get_image(bucket, key, s3_client)
    thumbnail = create_thumbnail(image)
    upload_thumbnail(id, name, bucket, thumbnail, s3_client)

    update_db(update_db_option, dynamodb_resouce)


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


def get_id(key: str) -> str:
    """
    Keyからid(uuid)を取得する
    """
    return key[7:43]


def get_image(bucket: str, key: str, s3_client: BaseClient) -> Image:
    """
    S3から画像を取得する
    """
    resp = s3_client.get_object(
        Bucket=bucket,
        Key=key
    )
    raw_bytes = resp['Body'].read()
    image = Image.open(BytesIO(raw_bytes))
    return image


def get_thumbnail_size() -> int:
    return int(os.environ['THUMBNAIL_SIZE'])


def expand_to_square(image: Image) -> Image:
    """
    余白を追加して正方形にする
    """
    width, height = image.size
    background_color = (0, 0, 0)
    if width == height:
        return image
    elif width > height:
        result = Image.new(image.mode, (width, width), background_color)
        result.paste(image, (0, (width - height) // 2))
        return result
    else:
        result = Image.new(image.mode, (height, height), background_color)
        result.paste(image, ((height - width) // 2, 0))
        return result


def create_thumbnail(image: Image) -> Image:
    """
    サムネイルを生成する
    """
    size = get_thumbnail_size()
    square_image = expand_to_square(image)
    thumbnail = square_image.resize((size, size), Image.LANCZOS)
    return thumbnail


def convert_image_to_bytes(image: Image) -> bytes:
    """
    Imageをbytesに変換する
    """
    io = BytesIO()
    image.save(io, format='PNG')
    return io.getvalue()


def upload_thumbnail(id: str, name: str, bucket: str, thumbnail: Image, s3_client: BaseClient) -> None:
    """
    サムネイルをアップロードする
    """
    raw_bytes = convert_image_to_bytes(thumbnail)
    key = f'thumbnails/{id}/{name}.png'
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=raw_bytes,
        ContentType='image/png'
    )


def create_update_db_option(id: str) -> dict:
    """
    metadataを更新するためのOptionを生成する。ここではサムネイルを持っているかを示すattributeを追加している。
    """
    update_attributes = {
        'hasThumbnail': True,
        'updatedAt': int(datetime.now(timezone.utc).timestamp() * 1000)
    }

    option = {
        'Key': {
            'id': id
        },
        'ConditionExpression': Key('id').eq(id),
        'ReturnValues': 'ALL_NEW'
    }

    update_expression_array = [f'#{x} = :{x}' for x in update_attributes.keys()]
    option['UpdateExpression'] = f'SET {", ".join(update_expression_array)}'
    option['ExpressionAttributeNames'] = {f'#{x}': x for x in update_attributes.keys()}
    option['ExpressionAttributeValues'] = {f':{k}': v for k, v in update_attributes.items()}

    return option


def get_table_name():
    """
    環境変数からDynamoDBのTable名を取得する
    """
    return os.environ['DATA_TABLE_NAME']


def update_db(option: dict, dynamodb_resource: ServiceResource) -> dict:
    """
    metadataを更新する
    """
    table = dynamodb_resource.Table(get_table_name())
    resp = table.update_item(**option)
    return resp
