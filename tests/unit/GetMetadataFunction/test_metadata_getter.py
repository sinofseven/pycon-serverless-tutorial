import pytest

import metadata_getter


class TestFetchAMetadata(object):
    @pytest.mark.parametrize(
        'set_environ, dynamodb, id, expected', [
            (
                {
                    'DATA_TABLE_NAME': 'data_table'
                },
                [
                    ['data_table']
                ],
                '4b1ec5d8-bff0-47ce-a42d-f70643abca27',
                None
            ),
            (
                {
                    'DATA_TABLE_NAME': 'data_table'
                },
                [
                    ['data_table', 'single data']
                ],
                '4b1ec5d8-bff0-47ce-a42d-f70643abca27',
                None
            ),
            (
                {
                    'DATA_TABLE_NAME': 'data_table'
                },
                [
                    ['data_table', 'single data']
                ],
                '34d4b1ab-edfb-4b21-83e9-642e2f623345',
                {
                    'id': '34d4b1ab-edfb-4b21-83e9-642e2f623345',
                    'filename': 'dog.png',
                    'isUploaded': True,
                    'createdAt': 1566868362512
                }
            )
        ], indirect=['set_environ', 'dynamodb']
    )
    @pytest.mark.usefixtures('set_environ')
    def test_normal(self, dynamodb, id, expected):
        actual = metadata_getter.fetch_a_metadata(id, dynamodb_resource=dynamodb)
        assert actual == expected
