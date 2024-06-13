import json

with open('config/private.json') as config_file:
    config = json.load(config_file)


def exists(key):
    return key in config

def get(key):
    return config[key]
