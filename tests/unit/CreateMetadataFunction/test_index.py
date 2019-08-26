import json

import pytest

import index


class TestHandler(object):
    @pytest.mark.parametrize(
        'error, expected', [
            (
                ValueError,
                {
                    'statusCode': 500,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'message': 'InternalServerError'})
                }
            )
        ]
    )
    def test_exception(self, monkeypatch, error, expected):
        def dummy(*_, **__):
            raise error()
        monkeypatch.setattr(index, 'main', dummy)
        actual = index.handler({}, None)
        assert actual == expected

    @pytest.mark.parametrize(
        'status_code, body, expected', [
            (
                200,
                'test result',
                {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json'
                    },
                    'body': 'test result'
                }
            ),
            (
                400,
                'test result error',
                {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json'
                    },
                    'body': 'test result error'
                }
            )
        ]
    )
    def test_normal(self, monkeypatch, status_code, body, expected):
        monkeypatch.setattr(index, 'main', lambda *_, **__: (status_code, body))
        actual = index.handler({}, None)
        assert actual == expected
