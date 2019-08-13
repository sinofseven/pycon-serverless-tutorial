import metadata_creator
import pytest
import json


class TestMakeErrorMessage(object):
    @pytest.mark.parametrize(
        'error, expected', [
            (
                Exception('test'),
                json.dumps({'message': 'test'})
            ),
            (
                ValueError('value error'),
                json.dumps({'message': 'value error'})
            )
        ]
    )
    def test_normal(self, error, expected):
        actual = metadata_creator.make_error_message(error)
        assert actual == expected
