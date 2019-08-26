import json

import pytest
import requests
from freezegun import freeze_time

import metadata_creator


class TestValidateContentJson(object):
    @pytest.mark.parametrize(
        'event', [
            (None),
            ({}),
            ({'headers': {'Content-Type': 'text/plain'}})
        ]
    )
    def test_exception(self, event):
        with pytest.raises(metadata_creator.ValidationError):
            metadata_creator.validate_content_json(event)

    @pytest.mark.parametrize(
        'event', [
            ({'headers': {'Content-Type': 'application/json'}})
        ]
    )
    def test_normal(self, event):
        metadata_creator.validate_content_json(event)


class TestGetJsonRequestBody(object):
    @pytest.mark.parametrize(
        'event', [
            ({}),
            ({'body': None}),
            ({'body': 'hoge'})
        ]
    )
    def test_exception(self, event):
        with pytest.raises(metadata_creator.ValidationError):
            metadata_creator.get_json_request_body(event)

    @pytest.mark.parametrize(
        'event, expected', [
            (
                {
                    'body': json.dumps({
                        'test': True,
                        'value': 1
                    })
                },
                {
                    'test': True,
                    'value': 1
                }
            )
        ]
    )
    def test_normal(self, event, expected):
        actual = metadata_creator.get_json_request_body(event)
        assert actual == expected


class TestGetAndValidateFileName(object):
    @pytest.mark.parametrize(
        'body', [
            ({}),
            ({'filename': 1}),
            ({'filename': '画像.png'})
        ]
    )
    def test_exception(self, body):
        with pytest.raises(metadata_creator.ValidationError):
            metadata_creator.get_and_validate_file_name(body)

    @pytest.mark.parametrize(
        'body, expected', [
            (
                {'filename': 'test.png'},
                'test.png'
            ),
            (
                {'filename': 'foo.jpg'},
                'foo.jpg'
            )
        ]
    )
    def test_normal(self, body, expected):
        actual = metadata_creator.get_and_validate_file_name(body)
        assert actual == expected


class TestCreateMetadataItem(object):
    @pytest.mark.parametrize(
        'id, filename, expected', [
            (
                'test_id',
                'test.png',
                {
                    'id': 'test_id',
                    'filename': 'test.png',
                    'isUploaded': False,
                    'createdAt': 1554120000000
                }
            )
        ]
    )
    @freeze_time('2019/04/01 12:00:00+00:00')
    def test_normal(self, id, filename, expected):
        actual = metadata_creator.create_metadata_item(id, filename)
        assert actual == expected


class TestGetTableName(object):
    @pytest.mark.parametrize(
        'set_environ, expected', [
            (
                {'DATA_TABLE_NAME': 'data_table'},
                'data_table'
            )
        ], indirect=['set_environ']
    )
    @pytest.mark.usefixtures('set_environ')
    def test_normal(self, expected):
        actual = metadata_creator.get_table_name()
        assert actual == expected


class TestGetBucketName(object):
    @pytest.mark.parametrize(
        'set_environ, expected', [
            (
                {'DATA_BUCKET_NAME': 'data_bucket'},
                'data_bucket'
            )
        ], indirect=['set_environ']
    )
    @pytest.mark.usefixtures('set_environ')
    def test_normal(self, expected):
        actual = metadata_creator.get_bucket_name()
        assert actual == expected


class TestPutMetadataItem(object):
    @pytest.mark.parametrize(
        'dynamodb, set_environ, table_name, metadata', [
            (
                [
                    ['data_table']
                ],
                {
                    'DATA_TABLE_NAME': 'data_table'
                },
                'data_table',
                {
                    'id': 'test_id',
                    'filename': 'test.png',
                    'isUploaded': False,
                    'createdAt': 1234567890
                }
            ),
            (
                [
                    ['data_table']
                ],
                {
                    'DATA_TABLE_NAME': 'data_table'
                },
                'data_table',
                {
                    'id': 'test_id_02',
                    'filename': 'test_02.png',
                    'isUploaded': False,
                    'createdAt': 1234567890
                }
            )
        ], indirect=['dynamodb', 'set_environ']
    )
    @pytest.mark.usefixtures('set_environ')
    def test_normal(self, dynamodb, table_name, metadata):
        metadata_creator.put_metadata_item(metadata, dynamodb)

        table = dynamodb.Table(table_name)
        resp = table.scan()
        assert resp['Items'] == [metadata]


class TestPreSignedUrlForPut(object):
    @pytest.mark.parametrize(
        'create_s3_bucket, set_environ, bucket_name, id, filename', [
            (
                'data_bucket',
                {'DATA_BUCKET_NAME': 'data_bucket'},
                'data_bucket',
                'test_id',
                'test.png'
            )
        ], indirect=['create_s3_bucket', 'set_environ']
    )
    @pytest.mark.usefixtures('create_s3_bucket', 'set_environ')
    def test_normal(self, s3_client, bucket_name, id, filename):
        actual = metadata_creator.create_pre_signed_url_for_put(id, filename, s3_client)
        assert set(actual.keys()) == {'id', 'url', 'method', 'expiresIn'}
        assert actual['id'] == id
        assert actual['method'] == 'PUT'
        assert actual['expiresIn'] == 3600
        assert actual['url'].find(f'http://localhost:4572/{bucket_name}/images/{id}/{filename}?') == 0

        resp = requests.put(actual['url'], data='test data'.encode())
        assert resp.status_code == 200


class TestMain(object):
    @pytest.mark.parametrize(
        'dynamodb, create_s3_bucket, set_environ, bucket_name, id, filename, event, expected_metadata', [
            (
                [
                    ['data_table']
                ],
                'data_bucket',
                {
                    'DATA_TABLE_NAME': 'data_table',
                    'DATA_BUCKET_NAME': 'data_bucket'
                },
                'data_bucket',
                'test_id',
                'test.png',
                {
                    'headers': {
                        'Content-Type': 'application/json'
                    },
                    'body': json.dumps({'filename': 'test.png'})
                },
                {
                    'id': 'test_id',
                    'filename': 'test.png',
                    'isUploaded': False,
                    'createdAt': 1554120000000
                }
            )
        ], indirect=['dynamodb', 'create_s3_bucket', 'set_environ']
    )
    @pytest.mark.usefixtures('create_s3_bucket', 'set_environ')
    @freeze_time('2019/04/01 12:00:00+00:00')
    def test_normal(self, monkeypatch, s3_client, dynamodb, bucket_name, id, filename, event, expected_metadata):
        monkeypatch.setattr(metadata_creator, 'uuid4', lambda: id)
        status_code, raw_actual = metadata_creator.main(event, dynamodb_resouce=dynamodb, s3_client=s3_client)
        actual = json.loads(raw_actual)
        assert status_code == 200
        assert set(actual.keys()) == {'metadata', 'preSignedUrl'}
        assert actual['metadata'] == expected_metadata
        assert actual['preSignedUrl']['id'] == id
        assert actual['preSignedUrl']['url'].find(f'http://localhost:4572/{bucket_name}/images/{id}/{filename}?') == 0
