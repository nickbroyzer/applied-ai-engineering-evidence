"""Socket-level outbound network block. Loopback and unix sockets only."""
import socket

_ALLOWED = {"127.0.0.1", "::1", "localhost", ""}


class BlockedNetwork(RuntimeError):
    pass


_orig_connect = socket.socket.connect
_orig_connect_ex = socket.socket.connect_ex


def _host_of(address):
    if isinstance(address, tuple):
        return address[0]
    return ""  # AF_UNIX path


def _guard(fn):
    def wrapper(self, address, *a, **k):
        if self.family in (socket.AF_INET, socket.AF_INET6):
            host = _host_of(address)
            if host not in _ALLOWED:
                raise BlockedNetwork(f"outbound network blocked: {address!r}")
        return fn(self, address, *a, **k)
    return wrapper


socket.socket.connect = _guard(_orig_connect)
socket.socket.connect_ex = _guard(_orig_connect_ex)


def _blocked_getaddrinfo(host, *a, **k):
    if host not in _ALLOWED:
        raise BlockedNetwork(f"DNS blocked: {host!r}")
    return _orig_getaddrinfo(host, *a, **k)


_orig_getaddrinfo = socket.getaddrinfo
socket.getaddrinfo = _blocked_getaddrinfo
