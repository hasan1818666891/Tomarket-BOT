import json
import os

from bot.config import settings
from bot.utils import logger


def load_from_json(path: str):

    if os.path.isfile(path):
        with open(path, encoding="utf-8") as file:
            try:
                data = json.load(file)
                if isinstance(data, list):  # Ensure it's a list
                    return data
                else:
                    logger.warning(
                        "Invalid JSON structure. Resetting to default.")
            except json.JSONDecodeError:
                logger.warning(
                    "Empty or invalid JSON file. Resetting to default.")

    example = [{
        "session_name": "name_example",
        "user_agent": "Mozilla/5.0 (Linux; Android 9; Samsung SM-G892A) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.156 Mobile Safari/537.36 Telegram-Android/11.3.4 (Samsung SM-G892A; Android 9; SDK 28; AVERAGE)",
        "proxy": "type://user:pass:ip:port"
    }]
    with open(path, 'w', encoding="utf-8") as file:
        json.dump(example, file, ensure_ascii=False, indent=2)
    return example


def save_to_json(path: str, data: list):

    with open(path, 'w', encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
