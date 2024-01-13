import os
import json

with open('config/public.json') as config_file:
    config = json.load(config_file)
    
def get(key):
    return config[key]

def get_keys():
    return config.keys()

def change(key, value):
    config[key] = value
    with open('config.json', 'w') as config_file:
        json.dump(config, config_file, indent=4)
        
        
def load(file):
    file = os.path.join(os.path.dirname(__file__), 'json', file)
    with open(file) as f:
        return json.load(f)
    
def dump(file, data):
    file = os.path.join(os.path.dirname(__file__), 'json', file)
    with open(file, 'w') as f:
        json.dump(data, f, indent=4)