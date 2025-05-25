import random
import socket
import threading

from .log import get_logger

log = get_logger()


def run(cfg):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen_to = (cfg.host, cfg.port)
        server.bind(listen_to)
        server.listen(128)
        log.info("proxy listening on %s", listen_to)
        while True:
            client, _ = server.accept()
            log.info("accepted connection from %s [%d]", client.getpeername(), threading.active_count())
            thread = threading.Thread(target=try_handle_client, args=(cfg, client), daemon=True)
            thread.start()


def try_handle_client(cfg, client):
    try:
        handle_client(cfg, client)
    except Exception as e:
        log.error("handle_client: %s", e)
        try_shutdown_socket(client)


def try_shutdown_socket(sock):
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except Exception as e:
        log.debug("shutdown socket error: %s", e)
    finally:
        sock.close()


def read_request(cfg, client):

    request = b""
    while b"\r\n\r\n" not in request:
        chunk = client.recv(cfg.buffer_size)
        if not chunk:
            return None, None, None
        request += chunk

    header = request.decode(encoding="utf-8", errors="ignore")
    first_line = header.split("\r\n", maxsplit=1)[0]
    method, host, *_ = first_line.split()
    host, port = (":" in host and host.split(":")) or (host, "443")
    port = (port.isdigit() and int(port)) or 0
    return method, host, port


def handle_client(cfg, client):

    try:
        method, host, port = read_request(cfg, client)
        log.info("request: %s %s:%s", method, host, port)
        assert method == "CONNECT", "only CONNECT method is supported"
        assert host, "host is required"
        assert port, "port is required"
    except Exception as e:
        log.error("read_request error: %s", e)
        client.sendall(f"HTTP/1.1 400 Bad Request ({e})\r\n\r\n".encode("utf-8", errors="ignore"))
        try_shutdown_socket(client)
        return

    try:
        remote = socket.create_connection((host, port))
        client.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
    except Exception as e:
        log.error("create_connection error: (%s:%s) %s", host, port, e)
        client.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
        try_shutdown_socket(client)
        return

    tout = threading.Thread(target=try_proxy_traffic, args=(cfg, client, remote, cfg.resplit))
    tin = threading.Thread(target=try_proxy_traffic, args=(cfg, remote, client, False))
    tout.start()
    tin.start()
    tin.join()
    tout.join()


def try_proxy_traffic(cfg, src, dst, resplit=False):
    try:
        return proxy_traffic(cfg, src, dst, resplit)
    except Exception as e:
        log.error("proxy_traffic: %s", e)
        return -1, -1, -1
    finally:
        try_shutdown_socket(src)
        try_shutdown_socket(dst)


def proxy_traffic(cfg, src, dst, resplit=False):
    src_name = src.getpeername()[0]
    dst_name = dst.getpeername()[0]
    i, rx, tx = 0, 0, 0
    while True:
        data = src.recv(cfg.buffer_size)
        if cfg.debug:
            log.debug("[%d] [%s]→[%s] %db {%.80s}", i, src_name, dst_name, len(data), data[:64].hex())
        if not data:
            break
        i += 1
        rx += len(data)
        if i <= cfg.resplit_count and resplit:
            parts, parted_data_len = split_tls_record(cfg, data)
            log.info("[%d] resplit data → %db %d parts", i, parted_data_len, len(parts))
        else:
            parts = [data]
        for part_data in parts:
            dst.sendall(part_data)
            tx += len(part_data)
    log.info("proxy_traffic done: %s→%s, rx=%d, tx=%d [%d]", src_name, dst_name, rx, tx, i)
    return i, rx, tx


def split_tls_record(cfg, data):

    data_len = len(data)

    if data_len < 5 or not data.startswith(b"\x16\x03"):
        if cfg.debug:
            log.debug("TLS not here: %s", data[0:16].hex())
        return [data], data_len

    tls_len = int.from_bytes(data[3:5], byteorder="big")

    if cfg.debug:
        log.debug("TLS record: %s tls-len=%s data-len=%s", data[0:16].hex(), tls_len, data_len)

    if tls_len + 5 != data_len:
        log.warning("TLS record length mismatch: %s tls-len=%s data-len=%s", data[0:16].hex(), tls_len, data_len)
        return [data], data_len

    parts = []
    parted_data_len = 0
    pos = 5

    while pos < data_len:
        part_len = random.randint(min(data_len - pos, cfg.min_split), min(cfg.max_split, data_len - pos))
        part_data = data[pos : pos + part_len]
        parts.append(
            bytes.fromhex("160304")  # 3 bytes TLS record header
            + part_len.to_bytes(2, byteorder="big")  # 2 bytes TLS record length
            + part_data  # part data
        )
        if cfg.debug:
            log.debug("pos=%d part_len=%d, part=%.80s", pos, part_len, part_data[:32].hex())
        pos += part_len
        parted_data_len += 3 + 2 + part_len

    return parts, parted_data_len
