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

