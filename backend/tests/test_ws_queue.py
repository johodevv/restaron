import asyncio
import json
import time
import pytest
from app.websockets.manager import ConnectionManager

pytestmark=pytest.mark.anyio


class Socket:
    def __init__(self, slow=False):
        self.slow=slow;self.messages=[];self.ready=asyncio.Event()
    async def accept(self):pass
    async def send_json(self,message):self.messages.append(message)
    async def send_text(self,message):
        if self.slow:await asyncio.sleep(10)
        self.messages.append(json.loads(message));self.ready.set()
    async def close(self,code=1000):pass


async def test_slow_socket_cannot_hold_mutation_response_and_fifo_is_preserved():
    mgr=ConnectionManager();slow=Socket(True);fast=Socket()
    await mgr.connect(slow,1,role='waiter');await mgr.connect(fast,1,role='admin')
    start=time.perf_counter()
    for i in range(50):await mgr.broadcast_to_restaurant(1,{'type':'order_updated','version':i})
    assert time.perf_counter()-start < .5
    await asyncio.wait_for(fast.ready.wait(),1)
    while len(fast.messages)<51:await asyncio.sleep(.01)
    assert [m['version'] for m in fast.messages[1:]]==list(range(50))
    await mgr.disconnect(slow);await mgr.disconnect(fast)


async def test_socket_backlog_is_bounded_and_lagging_connection_is_closed():
    mgr=ConnectionManager();slow=Socket(True)
    await mgr.connect(slow,1,role='waiter')
    for i in range(300):await mgr.broadcast_to_restaurant(1,{'version':i})
    await asyncio.sleep(.05)
    assert slow not in mgr._connection_meta and slow not in mgr._outgoing
