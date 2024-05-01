import json

with open('config/private.json') as config_file:
    config = json.load(config_file)


def get(key):
    return config[key]
