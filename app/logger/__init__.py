import logging
from logging.handlers import RotatingFileHandler

logger = logging.getLogger("words")
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(filename)s:%(lineno)s (%(funcName)s) | %(message)s")

sh = logging.StreamHandler()
sh.setFormatter(formatter)
sh.setLevel(logging.DEBUG)

fh = RotatingFileHandler("log.log", maxBytes=1024 ** 2, backupCount=1, encoding='utf-8')
fh.setFormatter(formatter)
fh.setLevel(logging.DEBUG)

logger.addHandler(sh)
logger.addHandler(fh)
