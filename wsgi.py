from __future__ import print_function

import os
import csv

from flask import Flask, request
from flask_restful import Resource, Api

from pymongo import MongoClient, GEO2D

DB_HOST = os.environ.get('DB_HOST', 'mongodb')
DB_NAME = os.environ.get('DB_NAME', 'mongodb')

DB_USERNAME = os.environ.get('DB_USERNAME', 'mongodb')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'mongodb')

DB_URI = 'mongodb://%s:%s@%s:27017/%s' % (DB_USERNAME, DB_PASSWORD,
        DB_HOST, DB_NAME)

DATASET_FILE = 'ToiletmapExport_161101_090000.csv'

application = Flask(__name__)

api = Api(application)

class HealthCheck(Resource):
    def get(self):
        return 'OK'

api.add_resource(HealthCheck, '/ws/healthz/')

class Info(Resource):
    description = {
        "id": "aussiedunnies",
        "displayName": "Aussie Dunnies",
        "type": "cluster",
        #"scope": "within",
        "center": {"latitude": "-33.87310577115773", "longitude": "151.19792461395264"},
        "zoom": 15
    }

    def get(self):
        return self.description

api.add_resource(Info, '/ws/info/')

class DataLoad(Resource):
    def get(self):
        client = MongoClient(DB_URI)
        database = client[DB_NAME]
        collection = database.aussiedunnies

        collection.remove({})
        collection.create_index([('Location', GEO2D)])

        with open(DATASET_FILE, 'rb') as csvfile:
            reader = csv.reader(csvfile)

            headers = reader.next()

            entries = []

            for row in reader:
                entry = dict(zip(headers, row))

                loc = [float(entry['Longitude']), float(entry['Latitude'])]
                entry['Location'] = loc

                entries.append(entry)

                if len(entries) >= 1000:
                    collection.insert_many(entries)
                    entries = []

            if entries:
                collection.insert_many(entries)

        return 'Inserted %s items.' % collection.count()

api.add_resource(DataLoad, '/ws/data/load')

def format_result(entries):
    result = []

    for entry in entries:
        data = {}

        data['id'] = entry['ToiletID']
        data['latitude'] = entry['Latitude']
        data['longitude'] = entry['Longitude']
        data['name'] = entry['Name']

        result.append(data)

    return result

class DataAll(Resource):
    def get(self):
        client = MongoClient(DB_URI)
        database = client[DB_NAME]
        collection = database.aussiedunnies

        return format_result(collection.find())

api.add_resource(DataAll, '/ws/data/all')

class DataWithin(Resource):
    def get(self):
        args = request.args

        box = [[float(args['lon1']), float(args['lat1'])],
               [float(args['lon2']), float(args['lat2'])]]

        query = {"Location": {"$within": {"$box": box}}}

        client = MongoClient(DB_URI)
        database = client[DB_NAME]
        collection = database.aussiedunnies

        return format_result(collection.find(query))

api.add_resource(DataWithin, '/ws/data/within')
