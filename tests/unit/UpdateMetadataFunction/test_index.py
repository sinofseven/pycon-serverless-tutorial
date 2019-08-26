import pytest

import index


class TestHandler(object):
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
