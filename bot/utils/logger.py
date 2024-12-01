import sys
from loguru import logger
import os

os.makedirs("logs", exist_ok=True)
logger.remove()

logger.add(
    sink=sys.stdout,
    format="<white>{time:YYYY-MM-DD HH:mm:ss}</white>"
           " | <level>{level: <8}</level>"
           " | <cyan><b>{line: <4}</b></cyan>"
           " - <white><b>{message}</b></white>"
)

logger.add(
    "logs/app.log",
    rotation="1 MB",
    retention="3 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
)

logger.add(
    "logs/debug.log",
    level="DEBUG",
    rotation="1 MB",
    retention="7 days"
)

logger = logger.opt(colors=True)