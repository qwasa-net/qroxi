import argparse

from .config import Config
from .http_proxy import run
from .log import setup_logging


def main():
    cfg = read_args()
    setup_logging(cfg)
    run(cfg)


def read_args():
    parser = argparse.ArgumentParser(description="qproxi it is")
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18010)
    parser.add_argument("--resplit", "-r", action="store_true")
    parser.add_argument("--resplit-count", type=int, default=1)
    parser.add_argument("--debug", "-d", action="store_true")
    parser.add_argument("--silent", "-s", action="store_true")
    parser.add_argument("--buffer-size", type=int, default=8192)
    parser.add_argument("--min-split", type=int, default=32)
    parser.add_argument("--max-split", type=int, default=256)
    args = parser.parse_args()
    return Config(
        name="qproxi",
        resplit=args.resplit,
        resplit_count=args.resplit_count,
        host=args.host,
        port=args.port,
        debug=args.debug,
        silent=args.silent,
        buffer_size=args.buffer_size,
        min_split=args.min_split,
        max_split=args.max_split,
    )
