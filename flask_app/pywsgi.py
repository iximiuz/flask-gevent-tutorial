import os

from gevent import monkey
from gevent.pywsgi import WSGIServer

from app import app


monkey.patch_all()

http_server = WSGIServer(('0.0.0.0', int(os.environ['PORT_APP'])), app)
http_server.serve_forever()

