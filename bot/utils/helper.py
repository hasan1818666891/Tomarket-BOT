import asyncio
import json
import io
import os
import zlib
import gzip
import brotli
import aiohttp
import base64
import functools
from pytz import UTC
from typing import Callable
from bot.utils import logger
from datetime import datetime
from tzlocal import get_localzone
from aiocache import Cache, cached
from tonsdk.contract.wallet import Wallets, WalletVersionEnum


async def extract_json_from_response(response):
    try:
        response_bytes = await response.read()
        content_encoding = response.headers.get('Content-Encoding', '').lower()
        if content_encoding == 'br':
            response_text = brotli.decompress(response_bytes)
        elif content_encoding == 'deflate':
            response_text = zlib.decompress(response_bytes)
        elif content_encoding == 'gzip':
            with gzip.GzipFile(fileobj=io.BytesIO(response_bytes)) as f:
                response_text = f.read()
        else:
            response_text = response_bytes
        return json.loads(response_text.decode('utf-8'))
    except (brotli.error, gzip.error, UnicodeDecodeError) as e:
        logger.warning(f"Error processing response: {e}")
        return await response.json()

@cached(ttl=3600, cache=Cache.MEMORY)  # Cache combo.json file for 1 hour
async def get_combo() -> dict:
    url = 'https://raw.githubusercontent.com/boytegar/TomarketBOT/refs/heads/master/combo.json'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    response_text = await response.text()
                    return json.loads(response_text)
                else:
                    logger.error(f"Failed to fetch combo. Status code: {response.status}")
                    return {}
    except Exception as e:
        logger.error(f"Error fetching combo: {e}")
        return {}

def get_param() -> str:
    parts = [
        str(0 * 1), str(0 * 1), str(0 * 1), str(0 * 1),
        chr(65), str(4 * 1), chr(99), chr(87)
    ]
    return ''.join(parts)

async def generate_ton_wallet(session_name: str) -> dict | bool:
    try:
        # Create a new wallet using WalletVersionEnum.v4r2
        mnemonics, public_key, private_key, wallet = Wallets.create(WalletVersionEnum.v4r2, workchain=0)

        # Generate the wallet address
        wallet_address = wallet.address.to_string(True, True, False)

        # Return all wallet credentials in a dictionary
        return True, {
            "mnemonic": " ".join(mnemonics),
            "wallet_address": wallet_address,
            "private_key": private_key.hex(),
            "public_key": public_key.hex()
        }

    except ModuleNotFoundError:
        logger.error(f"<light-yellow>{session_name}</light-yellow> | Error: The tonsdk library is not installed or not found.")
        return None, {}
    except Exception as e:
        logger.error(f"<light-yellow>{session_name}</light-yellow> | Unknown error when generating wallets: {e}")
        await asyncio.sleep(delay=3)
        return None, {}

async def configure_wallet(
    tg_id: str, 
    tg_username: str, 
    session_name: str
) -> str | bool:
    try:
        if not os.path.exists("wallets.json"):
            with open("wallets.json", "w") as f:
                    json.dump({}, f, indent=4)
        with open("wallets.json", "r") as f:
            wallets_json_file = json.load(f)
        if tg_id in list(wallets_json_file.keys()):
            wallet_address = wallets_json_file[tg_id]['wallet'].get('wallet_address')
        else:
            status, wallet_data = await generate_ton_wallet(session_name)
            if status and wallet_data != {}:
                wallets_json_file[tg_id]={
                    "wallet": wallet_data,
                    "session_name": f"{session_name}.session",
                    "username": tg_username
                }
                with open('wallets.json', 'w') as file:
                    json.dump(wallets_json_file, file, indent=4)
                wallet_address = wallet_data['wallet_address']
                logger.info(f"{session_name} | <g>New Ton wallet generated and saved it to</g> <c>wallets.json</c>")
        return wallet_address

    except Exception as e:
        logger.error(f"<light-yellow>{session_name}</light-yellow> | Unknown error when configuring wallets: {e}")
        await asyncio.sleep(delay=3)
        return False

async def is_expired(token: str) -> bool:
    if token is None or isinstance(token, bool):
        return True
    try:
        header, payload, sign = token.split(".")
        payload += "=" * ((4 - len(payload) % 4) % 4)  # Correct padding
        payload_data = base64.urlsafe_b64decode(payload).decode()
        payload_json = json.loads(payload_data)
        now = round(datetime.now().timestamp()) + 300  # Adding a 5-minute buffer
        exp = payload_json.get("exp")
        if exp is None or now > exp:
            return True
        return False
    except Exception as e:
        # In case of any error (like invalid token format)
        return True

def convert_utc_to_local(iso_time):
    try:
        dt = datetime.strptime(iso_time, "%Y-%m-%d %H:%M:%S")
        dt = dt.replace(tzinfo=UTC)
        local_timezone = get_localzone()
        local_dt = dt.astimezone(local_timezone)
        unix_time = int(local_dt.timestamp())
        return unix_time
    except Exception as e:
        logger.error(f"Error converting time: {e}, iso_time: {iso_time}")
        return None
