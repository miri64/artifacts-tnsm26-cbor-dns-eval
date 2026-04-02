#!/usr/bin/env python

# DOES NOT WORK, use https://github.com/aiortc/aioquic/blob/main/examples/http3_server.py
# instead. Maybe also get inspired by https://www.w3tutorials.net/blog/seriously-simple-python-http-proxy/
# too
# Source: https://abibeh.medium.com/getting-started-with-http-3-in-python-7f89ae3fbdc5

import argparse
import asyncio
import json
import logging
from typing import Dict, Optional

from aioquic.asyncio import QuicConnectionProtocol, serve  # asyncio helpers
from aioquic.h3.connection import H3_ALPN, H3Connection  # HTTP/3 core
from aioquic.h3.events import DataReceived, HeadersReceived, H3Event
from aioquic.quic.configuration import QuicConfiguration

LOG = logging.getLogger("h3server")


class Http3ServerProtocol(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._http: Optional[H3Connection] = None
        # Streams we expect a body for (POST/PUT/PATCH). Value = body buffer.
        self._bodies: Dict[int, bytearray] = {}
        # Remember method/path per stream so DataReceived can route correctly.
        self._req_meta: Dict[int, tuple[str, str]] = {}

    def handle_h3_event(self, event: H3Event) -> None:
        if isinstance(event, HeadersReceived):
            headers = {k.lower(): v for k, v in event.headers}
            method = headers.get(b":method", b"").decode()
            path = headers.get(b":path", b"/").decode()
            sid = event.stream_id

            LOG.info("Headers on stream %d: %s %s", sid, method, path)
            self._req_meta[sid] = (method, path)

            if method in ("POST", "PUT", "PATCH"):
                # We expect a request body.
                self._bodies[sid] = bytearray()
                if event.stream_ended:
                    # Rare case: headers said there's a body, but FIN already set.
                    payload = bytes(self._bodies.pop(sid))
                    self._respond(sid, method, path, payload)
                    self._req_meta.pop(sid, None)
            else:
                # No body expected → respond immediately.
                self._respond(sid, method, path, body=b"")
                # Leave _bodies empty for this stream so DataReceived (empty FIN)
                # gets ignored later.
                self._req_meta.pop(sid, None)

        elif isinstance(event, DataReceived):
            sid = event.stream_id

            # If we never created a body buffer for this stream, we are NOT expecting
            # a body (e.g., GET). Ignore any data/FIN that arrives.
            if sid not in self._bodies:
                return

            # Accumulate body for methods that expect it.
            self._bodies[sid].extend(event.data)

            if event.stream_ended:
                method, path = self._req_meta.get(sid, ("", "/"))
                payload = bytes(self._bodies.pop(sid, bytearray()))
                self._respond(sid, method, path, payload)
                self._req_meta.pop(sid, None)

    # Build and send an HTTP/3 response on a stream
    def _respond(
        self, stream_id: int, method: Optional[str], path: Optional[str], body: bytes
    ) -> None:
        status = b"200"
        content_type = b"text/plain"

        if method == "GET" and path == "/":
            payload = b"hello from aioquic h3 \n"
        elif method == "POST" and path == "/echo":
            try:
                obj = json.loads(body.decode() or "{}")
                payload = (json.dumps(obj, indent=2) + "\n").encode()
                content_type = b"application/json"
            except Exception:
                payload = body or b"(empty)\n"
                content_type = b"application/octet-stream"
        else:
            payload = b"ok\n"

        headers = [
            (b":status", status),
            (b"server", b"aioquic-tutorial"),
            (b"content-type", content_type),
            (b"alt-svc", b'h3=":4433"; ma=3600'),
        ]

        self._http.send_headers(stream_id, headers)
        self._http.send_data(stream_id, payload, end_stream=True)
        LOG.info("Responded on stream %d (%s bytes)", stream_id, len(payload))


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="::1")
    parser.add_argument("--port", type=int, default=4433)
    parser.add_argument("--certificate", default="cert.pem")
    parser.add_argument("--private-key", dest="private_key", default="key.pem")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    # QUIC/TLS configuration
    config = QuicConfiguration(
        is_client=False,
        alpn_protocols=H3_ALPN,
    )
    config.load_cert_chain(args.certificate, args.private_key)

    # 🚀 Start server
    server = await serve(
        host=args.host,
        port=args.port,
        configuration=config,
        create_protocol=Http3ServerProtocol,
    )

    logging.info("HTTP/3 server listening on %s:%d", args.host, args.port)

    # Keep running until cancelled
    try:
        await asyncio.Future()  # run forever
    except KeyboardInterrupt:
        pass
    finally:
        server.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
