"""Keep inference local, including if a dependency attempts an online fallback."""
import ipaddress
import socket

def enforce_local_network():
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_resolve = socket.getaddrinfo

    def allowed(host):
        if host is None or host in ("localhost", b"localhost"):
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    def connect(sock, address):
        if isinstance(address, tuple) and not allowed(address[0]):
            raise OSError("Offline mode: external network connections are disabled")
        return original_connect(sock, address)

    def connect_ex(sock, address):
        if isinstance(address, tuple) and not allowed(address[0]):
            raise OSError("Offline mode: external network connections are disabled")
        return original_connect_ex(sock, address)

    def resolve(host, *args, **kwargs):
        if not allowed(host):
            raise OSError("Offline mode: external name resolution is disabled")
        return original_resolve(host, *args, **kwargs)

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex
    socket.getaddrinfo = resolve
