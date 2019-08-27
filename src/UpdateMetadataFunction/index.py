import json
from typing import Any

from logger.get_logger import get_logger
from metadata_updater import main

logger = get_logger(__name__)


def handler(event: dict, context: Any) -> dict:
    """
    Lambdaで実行される関数
    :param event: 渡されたEvent。ここから色々な情報を取得する
    :param context: Lambdaの実行に関する情報が入ったインスタンス。今回の処理では使用しない
    :return: API GatewayのLambda統合Proxy用のレスポンス
    """
    result = {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': '{}'
    }
    try:
        logger.info('event', event)
        status_code, body = main(event)
        result['statusCode'] = status_code
        result['body'] = body
    except Exception as e:
        logger.error(f'Exception occurred: {e}', exc_info=True)
        result['statusCode'] = 500
        result['body'] = json.dumps(
            {
                'message': 'InternalServerError'
            }
        )
    return result
