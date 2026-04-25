"""Tests for NetworkTransport (TCP:9100 raster delivery).

Uses a localhost socket server as the stand-in for the printer — the
print path is one-way bytes-to-printer, so we don't need real hardware.
Status queries go via SNMP (UDP:161); see test_snmp.py for that side.
"""

from __future__ import annotations

import socket
import threading
from contextlib import contextmanager

import pytest

from label_printer.transport.base import StatusUnavailable
from label_printer.transport.network import NetworkTransport


@contextmanager
def _fake_printer(capture: list[bytes] | None = None):
    """Spin up a localhost TCP server that swallows whatever the client sends."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    host, port = server.getsockname()

    def serve():
        try:
            conn, _ = server.accept()
            with conn:
                conn.settimeout(0.5)
                buf = bytearray()
                try:
                    while True:
                        chunk = conn.recv(4096)
                        if not chunk:
                            break
                        buf.extend(chunk)
                except TimeoutError:
                    pass
                if capture is not None:
                    capture.append(bytes(buf))
        finally:
            server.close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        yield host, port
    finally:
        thread.join(timeout=2)


def test_send_writes_payload_to_socket():
    captured: list[bytes] = []
    with _fake_printer(capture=captured) as (host, port):
        transport = NetworkTransport(host, port=port, recv_timeout=1.0)
        transport.send(b"hello world")
    assert captured == [b"hello world"]


def test_probe_succeeds_on_listening_port():
    with _fake_printer() as (host, port):
        transport = NetworkTransport(host, port=port)
        transport.probe(timeout=1.0)  # no exception = pass


def test_probe_raises_oserror_on_unreachable_port():
    # Bind a port, close it immediately — guaranteed nothing listening.
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    _, port = s.getsockname()
    s.close()

    transport = NetworkTransport("127.0.0.1", port=port)
    with pytest.raises(OSError):
        transport.probe(timeout=0.5)


def test_query_status_surfaces_status_unavailable_when_snmp_fails(monkeypatch):
    """A NetworkTransport whose host doesn't speak SNMP must raise StatusUnavailable, not a raw exception."""
    from label_printer.transport import snmp as snmp_mod

    def boom(*args, **kwargs):
        raise snmp_mod.StatusViaSnmpFailed("simulated SNMP outage")

    monkeypatch.setattr(snmp_mod, "query_status_via_snmp", boom)

    transport = NetworkTransport("127.0.0.1")
    with pytest.raises(StatusUnavailable, match="simulated SNMP outage"):
        transport.query_status()


def test_connect_failure_during_send_raises_oserror():
    # Bind a port, close it immediately — guaranteed nothing listening.
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    _, port = s.getsockname()
    s.close()

    transport = NetworkTransport("127.0.0.1", port=port, connect_timeout=0.5)
    with pytest.raises(OSError):
        transport.send(b"anything")
