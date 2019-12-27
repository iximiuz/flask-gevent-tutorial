import os

import requests
from flask import Flask, request

api_port = os.environ['PORT_API']
api_url = f'http://slow_api:{api_port}/'

app = Flask(__name__)

@app.route('/')
def index():
    delay = int(request.args.get('delay') or 1)
    resp = requests.get(f'{api_url}?delay={delay}')
    return 'Hi there! ' + resp.text

