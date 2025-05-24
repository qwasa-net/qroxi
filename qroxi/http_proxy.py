import random
import socket
import threading

from .log import get_logger

log = get_logger()


def run(cfg):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen_to = (cfg.host, cfg.port)
        s.bind(listen_to)
        s.listen(128)
        log.info("proxy listening on %s", listen_to)
        while True:
            client, _ = s.accept()
            log.info("accepted connection from %s", client.getpeername())
            thread = threading.Thread(
                target=try_handle_client,
                args=(cfg, client),
                daemon=True,
            )
            thread.start()


def try_handle_client(cfg, client):
    try:
        handle_client(cfg, client)
    except Exception as e:
        log.error("handle_client: %s", e)
        client.close()


def handle_client(cfg, client):

    request = b""
    while b"\r\n\r\n" not in request:
        chunk = client.recv(cfg.buffer_size)
        if not chunk:
            client.close()
            return
        request += chunk

    header = request.decode(errors="ignore")
    first_line = header.split("\r\n")[0]
    if not first_line.startswith("CONNECT"):
        log.error("bad request: %s", first_line)
        client.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
        client.close()
        return

    method, addr, _ = first_line.split()
    host, port = addr.split(":")
    port = int(port)
    log.info("request: %s %s", method, addr)

    try:
        remote = socket.create_connection((host, port))
        client.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
    except Exception:
        client.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
        client.close()
        return

    t1 = threading.Thread(target=try_proxy_traffic, args=(cfg, client, remote, cfg.resplit))
    t2 = threading.Thread(target=try_proxy_traffic, args=(cfg, remote, client, False))
    t1.start()
    t2.start()


def try_proxy_traffic(cfg, src, dst, resplit=False):
    try:
        return proxy_traffic(cfg, src, dst, resplit)
    except Exception as e:
        log.error("proxy_traffic: %s", e)
        src.close()
        dst.close()
        return -1, -1, -1


def proxy_traffic(cfg, src, dst, resplit=False):
    src_name = src.getpeername()[0]
    dst_name = dst.getpeername()[0]
    i, rx, tx = 0, 0, 0
    try:
        while True:
            data = src.recv(cfg.buffer_size)
            log.debug("[%d] [%s]→[%s] %d bytes {%.64s}", i, src_name, dst_name, len(data), repr(data[:64]))
            if not data:
                break
            i += 1
            rx += len(data)
            if i == 1 and resplit:
                data, parts = split_tls_packet(data)
                log.info("[%d] resplit data → %db %d parts", i, len(data), parts)
            dst.sendall(data)
            tx += len(data)
    except Exception as e:
        log.error("proxy_traffic: %s", e)
    finally:
        src.close()
        dst.close()
    log.info("proxy_traffic done: %s → %s, rx=%d, tx=%d", src_name, dst_name, rx, tx)
    return i, rx, tx


def split_tls_packet(data, min_len=32, max_len=128):

    if len(data) >= 5 and data.startswith(b"\x16\x03"):
        tls_len = int.from_bytes(data[3:5], byteorder="big")
        log.debug("TLS handshake: %s tls-len=%s data-len=%s", data[0:16].hex(), tls_len, len(data))
    else:
        log.debug("TLS not here: %s", data[0:16].hex())
        return data, 1

    parts = []
    pos = 5
    data_len = len(data)

    while pos < data_len:
        part_len = random.randint(min(data_len - pos, min_len), min(max_len, data_len - pos))
        part = data[pos : pos + part_len]
        parts.append(bytes.fromhex("160304"))
        parts.append(int(len(part)).to_bytes(2, byteorder="big"))
        parts.append(part)
        log.debug("part_len=%d, part=%.16s", part_len, repr(part))
        pos += part_len

    return b"".join(parts), len(parts)
