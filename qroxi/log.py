import logging


def setup_logging(cfg):
    if cfg.silent:
        log_level = logging.WARNING
    elif cfg.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )


def get_logger(cfg=None):
    logger = logging.getLogger()
    return logger
