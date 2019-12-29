# How to use Flask with gevent (uWSGI and Gunicorn editions)

## Create simple Flask application

First, we need to emulate a slow 3rd party API:

```python
# slow_api/api.py
import os

import asyncio
from aiohttp import web

async def handle(request):
    delay = float(request.query.get('delay') or 1)
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
    delay = float(request.args.get('delay') or 1)
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

## Use Nginx reverse proxy in front of application server

See `nginx-gunicorn.yml` and `nginx-uwsgi.yml`:

```bash
$ docker-compose -f nginx-gunicorn.yml build
$ docker-compose -f nginx-gunicorn.yml up

# or

$ docker-compose -f nginx-uwsgi.yml build
$ docker-compose -f nginx-uwsgi.yml up

# and then:

$ ab -r -n 2000 -c 200 http://127.0.0.1:8080/?delay=1
> ...
```

## Bonus: make psycopg2 gevent-friendly with psycogreen

gevent patches only modules from the Python standard library. If we use
3rd party modules, like psycopg2, corresponding IO will still be blocking:

```python
# psycopg2/app.py

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
    cur.execute("SELECT NOW(), pg_sleep(%s)", (delay/2,))
    
    return 'Hi there! {} {}'.format(resp.text, cur.fetchall()[0])
```

We expect ~2 seconds to perform 10 one-second-long HTTP requests with concurrency 5,
but the test shows >5 seconds due to the blocking behavior of psycopg2 calls:

```bash
$ docker-compose -f bonus-psycopg2-gevent.yml build
$ docker-compose -f bonus-psycopg2-gevent.yml up

$ ab -r -n 10 -c 5 http://127.0.0.1:3000/?delay=1
> Concurrency Level:      5
> Time taken for tests:   6.670 seconds
> Complete requests:      10
> Failed requests:        0
> Requests per second:    1.50 [#/sec] (mean)
```

To bypass this limitation, we need to use psycogreen module to patch psycopg2:


```python
# psycopg2/patched.py

from psycogreen.gevent import patch_psycopg
patch_psycopg()

from app import app
```

```bash
$ docker-compose -f bonus-psycopg2-gevent.yml build
$ docker-compose -f bonus-psycopg2-gevent.yml up

$ ab -r -n 10 -c 5 http://127.0.0.1:3001/?delay=1
> Concurrency Level:      5
> Time taken for tests:   3.148 seconds
> Complete requests:      10
> Failed requests:        0
> Requests per second:    3.18 [#/sec] (mean)
```

