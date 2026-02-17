"""
Aquilia Benchmark – WebSocket Controller
=========================================
Uses Aquilia's socket system correctly:
- @Socket(path) class decorator (PascalCase)
- @OnConnect() / @OnDisconnect() lifecycle hooks (must be called)
- @Event("event_name") for message routing via envelope protocol
- Connection.send_json() for raw JSON responses
"""
import time

from aquilia.sockets import (
    SocketController,
    Socket,
    OnConnect,
    OnDisconnect,
    Event,
    Connection,
)


@Socket("/ws")
class BenchSocketController(SocketController):
    """Echo WebSocket controller for benchmark parity."""

    @OnConnect()
    async def handle_connect(self, conn: Connection):
        await conn.send_json({"event": "connected", "ts": time.time()})

    @OnDisconnect()
    async def handle_disconnect(self, conn: Connection):
        pass

    @Event("echo")
    async def handle_echo(self, conn: Connection, payload):
        """
        Echo handler – receives envelope payload and echoes it back.

        Clients send:  {"event": "echo", "data": {"cid": 0, "seq": 1, ...}}
        Runtime decodes the envelope and passes payload={"cid": 0, "seq": 1, ...}
        We echo the payload back as raw JSON.
        """
        await conn.send_json(payload)
