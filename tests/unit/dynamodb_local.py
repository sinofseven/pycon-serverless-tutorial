import json

import boto3

import pathlib


class DynamoDBLocal(object):
    def __init__(self, table_name):
        self.dynamodb = boto3.resource('dynamodb', endpoint_url='http://localhost:4569')
        self.dynamodb_table = self.dynamodb.Table(table_name)

    def abs_path(self, fixture_type):
        rel_path = f'fixtures/dynamodb/{fixture_type}/{self.dynamodb_table.table_name}.json'

        return str(pathlib.Path(__file__).parent.joinpath(rel_path).resolve())

    def table(self):
        definition = json.load(open(self.abs_path('tables')))
        definition['TableName'] = self.dynamodb_table.table_name
        return definition

    def create_table(self):
        return self.dynamodb.create_table(**self.table())

    def items(self, item_type):
        with open(self.abs_path('items'), mode='r') as fp:
            return json.load(fp).get(item_type)

    def put_items(self, item_type):
        with self.dynamodb_table.batch_writer() as batch:
            for item in self.items(item_type):
                batch.put_item(item)
