from gevent import monkey
monkey.patch_all()

import os

import psycopg2
import requests
from flask import Flask, request

api_port = os.environ['PORT_API']
api_url = f'http://slow_api:{api_port}/'

app = Flask(__name__)

@app.route('/')
def index():
    conn = psycopg2.connect(user="example", password="example", host="postgres")
    delay = float(request.args.get('delay') or 1)
    resp = requests.get(f'{api_url}?delay={delay/2}')

    cur = conn.cursor()
    cur.execute("SELECT pg_sleep(%s), NOW()", (delay/2,))
    
    return 'Hi there! {} {}'.format(resp.text, cur.fetchall())

