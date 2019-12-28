# How to use Flask with gevent (uWSGI and Gunicorn editions)

## Create a simple Flask application

First, we need to emulate a slow 3rd parth API:

```python
# slow_api/api.py
import os

import asyncio
from aiohttp import web

async def handle(request):
    delay = int(request.query.get('delay') or 1)
    await asyncio.sleep(delay)
    return web.Response(text='slow api response')

app = web.Application()
app.add_routes([web.get('/', handle)])

if __name__ == '__main__':
    web.run_app(app, port=os.environ['PORT'])
```

Then, we create a simple flask application with a dependency on the slow 3rd party API:

```python
# flask_app/app.py
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
```

## Deploy Flask application using Flask dev server

```bash
# Build and start app served by Flask dev server
$ docker-compose -f sync-devserver.yml build
$ docker-compose -f sync-devserver.yml up

# Test single-threaded deployment
$ ab -r -n 10 -c 5 http://127.0.0.1:3000/?delay=1
> Concurrency Level:      5
> Time taken for tests:   10.139 seconds
> Complete requests:      10
> Failed requests:        0
> Requests per second:    0.99 [#/sec] (mean)

# Test multi-threaded deployment
$ ab -r -n 10 -c 5 http://127.0.0.1:3001/?delay=1
> Concurrency Level:      5
> Time taken for tests:   3.069 seconds
> Complete requests:      10
> Failed requests:        0
> Requests per second:    3.26 [#/sec] (mean)
```

## Deploy Flask application using uWSGI (4 worker processes x 50 threads each)

```bash
# Build and start app served by uWSGI
$ docker-compose -f sync-uwsgi.yml build
$ docker-compose -f sync-uwsgi.yml up

$ ab -r -n 2000 -c 200 http://127.0.0.1:3000/?delay=1
> Concurrency Level:      200
> Time taken for tests:   12.685 seconds
> Complete requests:      2000
> Failed requests:        0
> Requests per second:    157.67 [#/sec] (mean)
```

## Deploy Flask application using Gunicorn (4 worker processes x 50 threads each)

```bash
# Build and start app served by uWSGI
$ docker-compose -f sync-gunicorn.yml build
$ docker-compose -f sync-gunicorn.yml up

$ ab -r -n 2000 -c 200 http://127.0.0.1:3000/?delay=1
> Concurrency Level:      200
> Time taken for tests:   13.427 seconds
> Complete requests:      2000
> Failed requests:        0
> Requests per second:    148.95 [#/sec] (mean)
```

## Deploy Flask application using gevent.pywsgi

First, we need to create an entrypoint:

```python
# flask_app/pywsgi.py
from gevent import monkey
monkey.patch_all()

import os
from gevent.pywsgi import WSGIServer
from app import app

http_server = WSGIServer(('0.0.0.0', int(os.environ['PORT_APP'])), app)
http_server.serve_forever()
```

Notice, how it patches our flask application. Without `monkey.patch_all()` there would be no benefit from using gevent here.

```bash
# Build and start app served by gevent.pywsgi
$ docker-compose -f async-gevent-pywsgi.yml build
$ docker-compose -f async-gevent-pywsgi.yml up

$ ab -r -n 2000 -c 200 http://127.0.0.1:3000/?delay=1
> Concurrency Level:      200
> Time taken for tests:   17.536 seconds
> Complete requests:      2000
> Failed requests:        0
> Requests per second:    114.05 [#/sec] (mean)
```

## Deploy Flask application using uWSGI + gevent

First, we need to create an entrypoint:

```python
# flask_app/patched.py
from gevent import monkey
monkey.patch_all()

from app import app  # re-export
```

We need to patch very early.

```bash
# Build and start app served by uWSGI + gevent
$ docker-compose -f async-gevent-uwsgi.yml build
$ docker-compose -f async-gevent-uwsgi.yml up

$ ab -r -n 2000 -c 200 http://127.0.0.1:3000/?delay=1
> Time taken for tests:   13.164 seconds
> Complete requests:      2000
> Failed requests:        0
> Requests per second:    151.93 [#/sec] (mean)
```

## Deploy Flask application using Gunicorn + gevent

This setup uses the same `patched.py` entrypoint.

```bash
# Build and start app served by Gunicorn + gevent
$ docker-compose -f async-gevent-gunicorn.yml build
$ docker-compose -f async-gevent-gunicorn.yml up

$ ab -r -n 2000 -c 200 http://127.0.0.1:3000/?delay=1
> Concurrency Level:      200
> Time taken for tests:   17.839 seconds
> Complete requests:      2000
> Failed requests:        0
> Requests per second:    112.11 [#/sec] (mean)
```
