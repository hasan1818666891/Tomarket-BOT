import aiohttp
import asyncio
import traceback
from time import time
from better_proxy import Proxy
from urllib.parse import unquote, quote
from datetime import datetime, timedelta
from typing import Any, Callable, Optional
from aiocfscrape import CloudflareScraper
from aiohttp_proxy import ProxyConnector as http_connector
from aiohttp_socks import ProxyConnector as socks_connector
from random import randint, choices, uniform, choices
from aiohttp import ClientSession, ClientTimeout, ClientConnectorError

from pyrogram import Client
from pyrogram.raw.functions import account
from pyrogram.raw.functions.messages import RequestAppWebView
from pyrogram.raw.types import InputBotAppShortName, InputNotifyPeer, InputPeerNotifySettings
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered, FloodWait, RPCError, UserAlreadyParticipant, UserNotParticipant, UserDeactivatedBan, UserRestricted, PeerIdInvalid

from bot.utils import logger
from .headers import get_headers, options_headers
from bot.config import settings
from bot.utils.proxy import get_proxy
from bot.exceptions import InvalidSession
from bot.core.agents import extract_chrome_version
from bot.core.registrator import get_tg_client
from bot.utils.safe_guard import check_base_url
from bot.utils.helper import get_combo, extract_json_from_response, get_param, is_expired, configure_wallet, convert_utc_to_local, time_until

BASE_API = "https://api-web.tomarket.ai/tomarket-game/v1"

login_api = f"{BASE_API}/user/login"
daily_claim_api = f"{BASE_API}/daily/claim"
wallet_task_api = f"{BASE_API}/tasks/walletTask"
add_wallet_api = f"{BASE_API}/tasks/address"
balance_api = f"{BASE_API}/user/balance"
farm_info_api = f"{BASE_API}/farm/info"
claim_farm_api = f"{BASE_API}/farm/claim"
start_farm_api = f"{BASE_API}/farm/start"
task_list_api = f"{BASE_API}/tasks/list"
task_start_api = f"{BASE_API}/tasks/start"
task_check_api = f"{BASE_API}/tasks/check"
task_claim_api = f"{BASE_API}/tasks/claim"
puzzle_task_api = f"{BASE_API}/tasks/puzzle"
claim_puzzle_api = f"{BASE_API}/tasks/puzzleClaim"
play_game_api = f"{BASE_API}/game/play"
claim_game_api = f"{BASE_API}/game/claim"
share_game_api = f"{BASE_API}/game/share"
rank_data_api = f"{BASE_API}/rank/data"
rank_create_api = f"{BASE_API}/rank/create"
rank_evaluate_api = f"{BASE_API}/rank/evaluate"
spin_show_api = f"{BASE_API}/spin/show"
spin_free_api = f"{BASE_API}/spin/free"
spin_once_api = f"{BASE_API}/spin/once"
spin_raffle_api = f"{BASE_API}/spin/raffle"
user_tickets_api = f"{BASE_API}/user/tickets"
spin_assets_api = f"{BASE_API}/spin/assets"
rank_upgrade_api = f"{BASE_API}/rank/upgrade"
rank_share_api = f"{BASE_API}/rank/sharetg"
check_token_api = f"{BASE_API}/token/check"
claim_token_api = f"{BASE_API}/token/claim"
token_balance_api = f"{BASE_API}/token/balance"
airdrop_task_list_api = f"{BASE_API}/token/airdropTasks"
airdrop_task_start_api = f"{BASE_API}/token/startTask"
airdrop_task_check_api = f"{BASE_API}/token/checkTask"
airdrop_task_claim_api = f"{BASE_API}/token/claimTask"
treasure_status_api = f"{BASE_API}/invite/isTreasureBoxOpen"
treasure_open_api = f"{BASE_API}/invite/openTreasureBox"
treasure_balance_api = f"{BASE_API}/invite/queryTreasureBoxBalance"
season_token_api = f"{BASE_API}/token/season"
tomatoes_api = f"{BASE_API}/token/tomatoes"
swap_tomato_api = f"{BASE_API}/token/tomatoToStar"

get_auto_farms_api = f"{BASE_API}/launchpad/getAutoFarms"
launchpad_task_status_api = f"{BASE_API}/launchpad/taskStatus"
launchpad_tasks_api = f"{BASE_API}/launchpad/tasks"
launchpad_task_claim_api = f"{BASE_API}/launchpad/taskClaim"
launchpad_detail_api = f"{BASE_API}/launchpad/detail"
launchpad_toma_balance_api = f"{BASE_API}/launchpad/tomaBalance"
invest_toma_api = f"{BASE_API}/launchpad/investToma"
start_auto_farm_api = f"{BASE_API}/launchpad/startAutoFarm"
claim_auto_farms_api = f"{BASE_API}/launchpad/claimAutoFarm"


GAME_ID = {
    "daily": "fa873d13-d831-4d6f-8aee-9cff7a1d0db1",
    "drop": "59bcd12e-04e2-404c-a172-311a0084587d",
    "farm": "53b22103-c7ff-413d-bc63-20f6fb806a07"
}

class Tapper:
    def __init__(
        self, tg_client: Client, 
        multi_thread: bool
    ) -> None:
        self.multi_thread = multi_thread
        self.tg_client = tg_client
        self.session_name = tg_client.name
        self.bot_username = "Tomarket_ai_bot"
        self.short_name = "app"
        self.access_token = None
        self.peer = None
        self.airdrop_season = settings.AIRDROP_SEASON
        self.lock = asyncio.Lock()
    
    async def get_tg_web_data(
        self, 
        proxy: str | None
    ) -> str: 
        proxy_dict = await self._parse_proxy(proxy)
        self.tg_client.proxy = proxy_dict
        try:
            async with self.tg_client:
                self.peer = await self.resolve_peer_with_retry(chat_id=self.bot_username, username=self.bot_username)
                ref_id = str(settings.REF_ID)
                ref_id = ref_id.spilt('-')[1] if "-" in ref_id else ref_id
                self.refer_id = choices([ref_id, get_param()], weights=[70, 30], k=1)[0] # this is sensitive data don’t change it (if ydk)
                web_view = await self.tg_client.invoke(
                    RequestAppWebView(
                        peer = self.peer,
                        platform = 'android',
                        app = InputBotAppShortName(
                            bot_id = self.peer, 
                            short_name = self.short_name
                        ),
                        write_allowed = True,
                        start_param = self.refer_id
                    )
                )
                auth_url = web_view.url
                return await self._extract_tg_web_data(auth_url)

        except InvalidSession as error:
            raise error
        except UserDeactivated:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Your Telegram account has been deactivated. You may need to reactivate it.")
            await asyncio.sleep(delay=3)
        except UserDeactivatedBan:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Your Telegram account has been banned. Contact Telegram support for assistance.")
            await asyncio.sleep(delay=3)
        except UserRestricted as e:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Your account is restricted. Details: {e}", exc_info=True)
            await asyncio.sleep(delay=3)
        except Unauthorized:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Session is Unauthorized. Check your API_ID and API_HASH")
            await asyncio.sleep(delay=3)
        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Unknown error during Authorization: {error}")
            await asyncio.sleep(delay=3)

    async def _extract_tg_web_data(self, auth_url: str) -> str:
        tg_web_data = unquote(
            string=unquote(
                string=auth_url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0]
            )
        )
        self.tg_account_info = await self.tg_client.get_me()
        tg_web_data_parts = tg_web_data.split('&')

        data_dict = {part.split('=')[0]: unquote(part.split('=')[1]) for part in tg_web_data_parts}
        return f"user={quote(data_dict['user'])}&chat_instance={data_dict['chat_instance']}&chat_type={data_dict['chat_type']}&start_param={data_dict['start_param']}&auth_date={data_dict['auth_date']}&signature={data_dict['signature']}&hash={data_dict['hash']}"

    async def check_proxy(
        self, 
        http_client: CloudflareScraper, 
        proxy: Proxy
    ) -> None:
        try:
            response = await http_client.get(url='https://ipinfo.io/json', timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
            response.raise_for_status()
            response_json = await extract_json_from_response(response=response)
            ip = response_json.get('ip', 'NO')
            country = response_json.get('country', 'NO')
            logger.info(f"{self.session_name} | Proxy IP: <g>{ip}</g> | Country : <g>{country}</g>")
        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Proxy: {proxy} | Error: {error}")

    async def _parse_proxy(
        self, 
        proxy: str | None
    ) -> dict | None:

        if proxy:
            parsed = Proxy.from_str(proxy)
            return dict(
                scheme=parsed.protocol,
                hostname=parsed.host,
                port=parsed.port,
                username=parsed.login,
                password=parsed.password
            )
        return None

    async def resolve_peer_with_retry(
        self, 
        chat_id: int | str, 
        username: str, 
        max_retries: int = 5
    ):
        retries = 0
        peer = None
        while retries < max_retries:
            try:
                # Try resolving the peer
                peer = await self.tg_client.resolve_peer(chat_id)
                break

            except (KeyError, ValueError, PeerIdInvalid) as e:
                # Handle invalid peer ID or other exceptions
                logger.warning(f"{self.session_name} | Error resolving peer: <y>{str(e)}</y>. Retrying in <e>3</e> seconds.")
                await asyncio.sleep(3)
                retries += 1

            except FloodWait as error:
                # Handle FloodWait error
                logger.warning(f"{self.session_name} | FloodWait error | Retrying in <e>{error.value + 15}</e> seconds.")
                await asyncio.sleep(error.value + 15)
                retries += 1

                peer_found = await self.get_dialog(username=username)
                if peer_found:
                    peer = await self.tg_client.resolve_peer(chat_id)
                    break
        if not peer:
            logger.error(f"{self.session_name} | Could not resolve peer for <y>{username}</e> after <e>{retries}</e> retries.")

        return peer

    async def get_dialog(
        self, 
        username: str
    ) -> bool:
        peer_found = False
        async for dialog in self.tg_client.get_dialogs():
            if dialog.chat and dialog.chat.username == username:
                peer_found = True
                break
        return peer_found

    async def mute_and_archive_chat(
        self, 
        chat, 
        peer, 
        username: str
    ) -> None:
        try:
            # Mute notifications
            await self.tg_client.invoke(
                account.UpdateNotifySettings(
                    peer=InputNotifyPeer(peer=peer),
                    settings=InputPeerNotifySettings(mute_until=2147483647)
                )
            )
            logger.info(f"{self.session_name} | Successfully muted chat <g>{chat.title}</g> for channel <y>{username}</y>")
        
            # Archive the chat
            await asyncio.sleep(delay=5)
            if settings.ARCHIVE_CHANNELS:
                await self.tg_client.archive_chats(chat_ids=[chat.id])
                logger.info(f"{self.session_name} | Channel <g>{chat.title}</g> successfully archived for channel <y>{username}</y>")
        except RPCError as e:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Error muting or archiving chat <g>{chat.title}</g>: {e}", exc_info=True)

    async def join_tg_channel(
        self, 
        link: str
    ) -> None:
        async with self.tg_client:
            try:
                parsed_link = link if 'https://t.me/+' in link else link[13:]
                username = parsed_link if "/" not in parsed_link else parsed_link.split("/")[0]
                try:
                    chat = await self.tg_client.join_chat(username)
                    chat_id = chat.id
                    logger.info(f"{self.session_name} | Successfully joined to <g>{chat.title}</g>")

                except UserAlreadyParticipant:
                    chat = await self.tg_client.get_chat(username)
                    chat_id = chat.id
                    logger.info(f"{self.session_name} | Chat <y>{username}</y> already joined")

                except RPCError:
                    logger.info(f"{self.session_name} | Channel <y>{username}</y> not found")
                    raise
                await asyncio.sleep(delay=5)

                peer = await self.resolve_peer_with_retry(chat_id, username)

                # Proceed only if peer was resolved successfully
                if peer:
                    await self.mute_and_archive_chat(chat, peer, username)

            except UserDeactivated:
                logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Your Telegram account has been deactivated. You may need to reactivate it.")
                await asyncio.sleep(delay=3)
            except UserDeactivatedBan:
                logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Your Telegram account has been banned. Contact Telegram support for assistance.")
                await asyncio.sleep(delay=3)
            except UserRestricted as e:
                logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Your account is restricted. Details: {e}", exc_info=True)
                await asyncio.sleep(delay=3)
            except AuthKeyUnregistered:
                logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Authorization key is unregistered. Please log in again.")
                await asyncio.sleep(delay=3)
            except Unauthorized:
                logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Session is Unauthorized. Check your API_ID and API_HASH")
                await asyncio.sleep(delay=3)
            except Exception as error:
                logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Error while join tg channel: {error} {link}")
                await asyncio.sleep(delay=3)

    async def change_name(
        self, 
        symbol: str
    ) -> bool:
        async with self.tg_client:
            try:
                me = await self.tg_client.get_me()
                first_name = me.first_name
                last_name = me.last_name if me.last_name else ''
                tg_name = f"{me.first_name or ''} {me.last_name or ''}".strip()
                
                if symbol not in tg_name:
                    changed_name = f'{first_name}{symbol}'
                    await self.tg_client.update_profile(first_name=changed_name)
                    logger.info(f"{self.session_name} | First name changed <g>{first_name}</g> to <g>{changed_name}</g>")
                    await asyncio.sleep(delay=randint(20, 30))
                return True
            except Exception as error:
                logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Error while changing tg name : {error}")
                return False

    async def login(
        self, 
        http_client: CloudflareScraper, 
        init_data: str,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[str]:
        retries = 0
        payload = {
            "init_data": init_data,
            "invite_code": str(self.refer_id),
            "from": "",
            "is_bot": False
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(login_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(login_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        user_info = response_json.get('data', {})
                        if user_info.get('is_new', False):
                            logger.success(f"{self.session_name} | 🥳 <green>Account created successfully! - ID: </green><cyan>{user_info['id']}</cyan>")
                        else:
                            logger.info(f"{self.session_name} | 🔐 <green>Account login Successfully</green>")
                        return user_info.get('access_token', None)
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | Get token failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while trying to get token: {e}", exc_info=True)
        return False

    async def claim_daily(
        self, 
        http_client: CloudflareScraper,
        max_retries: int = 10,
        delay: int = 10
    ) -> None:
        retries = 0
        payload = {
            "game_id": GAME_ID["daily"]
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(daily_claim_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(daily_claim_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        user_info = response_json['data']
                        if response_json["message"] != "already_check":
                            streak, tomato, games, tickets, spin, stars, diff = user_info.get("check_counter", 0), user_info.get("today_points", 0), user_info.get("today_game", 0), user_info.get("today_tickets", 0), user_info.get("today_spin", 0), user_info.get("today_stars", 0), user_info.get("diff", 0)

                            logger.success(f"""{self.session_name} | 🎉 <g>Daily Claimed successfully!</g>
                        ====<c> DAILY INFO </c>====
                        ├── Streak    : <lg>{streak}</lg>
                        ├── Tomato    : <g>{tomato}</g>
                        ├── Game      : <g>{games}</g>
                        ├── Tickets   : <g>{tickets}</g>
                        ├── Spin      : <g>{spin}</g>
                        └── Stars     : <g>{stars}</g>
                    """)
                        else:
                            logger.info(f"{self.session_name} | <y>Daily already claimed !</y>")
                        return True
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | claim daily failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while trying to claim daily: {e}", exc_info=True)
        return False

    async def wallet_task(
        self, 
        http_client: CloudflareScraper,
        max_retries: int = 10,
        delay: int = 10
    ) -> None:    
        retries = 0
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(wallet_task_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(wallet_task_api, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', {})
                        return data
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | Get wallet failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while getting wallet task: {e}", exc_info=True)
        return False

    async def add_wallet(
        self, 
        http_client: CloudflareScraper, 
        wallet_address: str,
        max_retries: int = 10,
        delay: int = 10
    ) -> bool:
        retries = 0
        payload = {
            "wallet_address": wallet_address
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(add_wallet_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(add_wallet_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(3)
                    if response.status == 200:
                        response_json = await response.json()
                        data = response_json.get('data',{})
                        if data == "ok":
                            return True
                        elif response_json.get('status',500) == 500:
                            message = response_json.get('message')
                            logger.info(f"{self.session_name} | adding wallet failed, because: <y>{message}<y>")
                            
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | submitting wallet failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while trying to add new wallet : {e}", exc_info=True)
        return False
    
    async def process_wallet_task(
        self, 
        http_client: CloudflareScraper,
        init_data: str
    ) -> None:
        try:
            isWallet = await self.wallet_task(http_client=http_client)
            if isWallet:
                if isWallet.get("walletAddress") == "":
                    logger.info(f"{self.session_name} | <y>Wallet address not found.</y>")
                    if settings.AUTO_ADD_WALLET:
                        tg_id = str(self.tg_account_info.id)
                        tg_username = str(self.tg_account_info.username) if self.tg_account_info.username else None
                        wallet_address = await configure_wallet(tg_id=tg_id, tg_username=tg_username, session_name=self.session_name)
                        if isinstance(wallet_address, str):
                            submit_wallet = await self.add_wallet(http_client=http_client, wallet_address=wallet_address)
                            if submit_wallet:
                                logger.info(f"{self.session_name} | 💳 New wallet address <g>{wallet_address}</g> added successfully.")
                else:
                    logger.info(f"{self.session_name} | 💳 Wallet address : <g>{isWallet.get('walletAddress','Not found')}</g>")
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while processing airdrop : {e}", exc_info=True)
    
    async def get_balance(
        self, 
        http_client: CloudflareScraper,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[dict]:
        retries = 0
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(balance_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(balance_api, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', {})
                        return data
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | getting balance failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while getting balance : {e}", exc_info=True)
        return False

    async def farm_info(
        self, 
        http_client: CloudflareScraper,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[dict]:
        retries = 0
        payload = {
            "game_id": GAME_ID["farm"]
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(farm_info_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(farm_info_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', {})
                        return data
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | getting farm info failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while getting farm info : {e}", exc_info=True)
        return False

    async def claim_farm(
        self, 
        http_client: CloudflareScraper,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[dict]:
        retries = 0
        payload = {
            "game_id": GAME_ID["farm"]
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(claim_farm_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(claim_farm_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', None)
                        farm_points = data.get("points", None)
                        stars = data.get('stars', 0)
                        message = f"Reward: <g>+{farm_points}</g> Tomato"
                        if stars != 0:
                            message += f" - <g>+{stars}</g> Stars"
                        logger.info(f"{self.session_name} | 🎉 <g>Success claim farm</g> | {message}")
                        return True
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | claiming farm failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while claiming farm : {e}", exc_info=True)
        return False

    async def start_farm(
        self, 
        http_client: CloudflareScraper,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[dict]:
        retries = 0
        payload = {
            "game_id": GAME_ID["farm"]
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(start_farm_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(start_farm_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', {})
                        end_at = data.get("end_at", 0)
                        next_farm = datetime.fromtimestamp(end_at)
                        logger.info(f"{self.session_name} | 🚜 <g>Farming started</g> | next claim at <g>{next_farm}</g>")
                        return data
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | Starting farm failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while start farming : {e}", exc_info=True)
        return False

    async def task_list(
        self, 
        http_client: CloudflareScraper, 
        init_data: str,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[dict]:
        retries = 0
        payload = {
            "language_code": "en",
            "init_data": init_data
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(task_list_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(task_list_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', {})
                        return data
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | Getting task list failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while getting task list : {e}", exc_info=True)
        return False

    async def start_task(
        self, 
        http_client: CloudflareScraper, 
        init_data: str, 
        task_id: int,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[dict]:
        retries = 0
        payload = {
            "task_id": task_id,
            "init_data": init_data
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(task_start_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(task_start_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', {})
                        return data
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | Starting task failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while start task: {e}", exc_info=True)
        return False

    async def check_task(
        self, 
        http_client: CloudflareScraper, 
        init_data: str, 
        task_id: int, 
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[bool]:
        retries = 0
        status_check = 0
        payload = {
            "task_id": task_id,
            "init_data": init_data
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(task_check_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(task_check_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=4)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', {})
                        if data.get('status', 1) == 2:
                            return True
                        else:
                            status_check += 1
                            if status_check >= 10:
                                return False
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | Checking task failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while checking task : {e}", exc_info=True)
        return False

    async def claim_task(
        self, 
        http_client: CloudflareScraper, 
        task_id: int,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[dict]:
        retries = 0
        payload = {
            "task_id": task_id
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(task_claim_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(task_claim_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)  
                        return response_json
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | Claiming task failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while claiming task : {e}", exc_info=True)
        return False

    async def process_task(
        self, 
        http_client: CloudflareScraper, 
        tg_web_data: str
    ) -> None:
        try:
            task_data = await self.task_list(http_client=http_client, init_data=tg_web_data)
            tasks_list = [
                task
                for category, tasks in task_data.items()
                for task in (tasks if isinstance(tasks, list) else tasks.get("default", []))
                if task.get("type") not in settings.DISABLED_TASKS
                and task.get("type") in settings.TO_DO_TASK
                and task.get("enable") is True
                and convert_utc_to_local(task.get("startTime", "1970-01-01 00:00:00")) <= int(time())
                and (
                    (task.get("endTime") == "" or convert_utc_to_local(task.get("endTime", "9998-12-31 23:59:59")) >= int(time()))
                ) 
                and task.get("status", 3) != 3
            ]
            for task in tasks_list:
                task_id = task.get('taskId')
                status = task.get('status')
                waitSecond = task.get('waitSecond', 0)
                name = task.get('name', 'not found')
                reward = task.get('score', None)
                if task.get("type") == "emoji" and status == 0:
                    isChanged = await self.change_name(symbol='🍅')
                    
                if status == 0:
                    logger.info(f"{self.session_name} | ⚙️ Performing task <g>{name}</g>")
                    start_task = await self.start_task(http_client=http_client, init_data=tg_web_data, task_id=task_id)
                    if isinstance(start_task, dict) and start_task.get("status", 0) == 1:
                        logger.info(f"{self.session_name} | 🥳 Task <g>{name}</g> started successfully")
                        logger.info(f"{self.session_name} | 🕚 Sleep <e>{max(0, waitSecond)}</e> second before finishing <g>{name}</g>")
                        await asyncio.sleep(max(0,waitSecond))
                        check_task = await self.check_task(http_client=http_client, init_data=tg_web_data, task_id=task_id)
                        if check_task:
                            logger.info(f"{self.session_name} | 🥳 Task <g>{name}</g> finished successfully")
                            claim_task = await self.claim_task(http_client=http_client, task_id=task_id)
                            if claim_task.get('data', None) == 'ok':
                                logger.info(f"{self.session_name} | 🎉 Task <g>{name}</g> claimed successfully | rewarded : <g>+{reward}</g> tomato")
                            else:
                                logger.info(f"{self.session_name} | <y>Task {name} not claimed</y>")
                        else:
                            logger.info(f"{self.session_name} | <y>Task {name} not finished</y>")
                    elif isinstance(start_task, dict) and start_task.get("status", 0) == 2:
                        claim_task = await self.claim_task(http_client=http_client, task_id=task_id)
                        if claim_task.get('data', None) == 'ok':
                            logger.info(f"{self.session_name} | 🎉 Task <g>{name}</g> claimed successfully | rewarded : <g>+{reward}</g> tomato")
                        else:
                            logger.info(f"{self.session_name} | <y>Task {name} not claimed</y>")
                    elif isinstance(start_task, str) and start_task == "ok":
                        logger.info(f"{self.session_name} | 🎉 Task <g>{name}</g> claimed successfully | rewarded : <g>+{reward}</g> tomato")
                    else:
                        logger.info(f"{self.session_name} | <y>Task {name} not started</y>")
                elif status == 1:
                    check_task = await self.check_task(http_client=http_client, init_data=tg_web_data, task_id=task_id)
                    if check_task:
                        logger.info(f"{self.session_name} | 🥳 Task <g>{name}</g> finished successfully")
                        claim_task = await self.claim_task(http_client=http_client, task_id=task_id)
                        if claim_task.get('data', None) == 'ok':
                            logger.info(f"{self.session_name} | 🎉 Task <g>{name}</g> claimed successfully | rewarded : <g>+{reward}</g> tomato")
                        else:
                            logger.info(f"{self.session_name} | <y>Task {name} not claimed</y>")
                    else:
                        logger.info(f"{self.session_name} | <y>Task {name} not finished</y>")
                elif status == 2:
                    claim_task = await self.claim_task(http_client=http_client, task_id=task_id)
                    if claim_task.get('data', None) == 'ok':
                        logger.info(f"{self.session_name} | 🎉 Task <g>{name}</g> claimed successfully | rewarded : <g>+{reward}</g> tomato")
                    else:
                        logger.info(f"{self.session_name} | <y>Task {name} not claimed</y>")
        except Exception as e:
            traceback.print_exc()
            logger.warning(f"{self.session_name} | Unknown error while processing task : {e}", exc_info=True)

    async def get_puzzle_task(
        self, 
        http_client: CloudflareScraper, 
        init_data: str,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[list]:
        retries = 0
        payload = {
            "language_code": "en",
            "init_data": init_data
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(puzzle_task_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(puzzle_task_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', [])
                        return data
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | Getting puzzle task failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while getting puzzle task : {e}", exc_info=True)
        return False

    async def claim_puzzle_task(
        self, http_client: CloudflareScraper, 
        task_id: int, 
        combo_code: str, 
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[dict]:
        retries = 0
        payload = {
            "task_id": int(task_id),
            "code": combo_code
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(claim_puzzle_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(claim_puzzle_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', None)
                        return data
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | Claiming puzzle task failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while claiming puzzle task : {e}", exc_info=True)
        return False

    async def solve_puzzle_task(
        self, 
        http_client: CloudflareScraper, 
        init_data: str
    ) -> None:
        try:
            puzzle_task = await self.get_puzzle_task(http_client=http_client, init_data=init_data)
            if puzzle_task:
                for task in puzzle_task:
                    start_time = convert_utc_to_local(task.get("startTime", "1970-01-01 00:00:00"))
                    end_time_str = task.get("endTime", "9998-12-31 23:59:59")
                    end_time_str = "9999-12-31 23:59:59" if end_time_str == "" else end_time_str              
                    end_time = convert_utc_to_local(end_time_str) 
                    current_time = int(time())
                    
                    if (
                        task.get('status', 3) == 0 and
                        task.get('type', None) == 'puzzle' and
                        start_time <= current_time and
                        end_time >= current_time
                    ):
                        task_id = str(task.get('taskId', None))
                        games = task.get('games', 0)
                        star = task.get('star', 0)
                        score = task.get('score', 0)
                        
                        combo_code = await get_combo()
                        if task_id in combo_code.keys():
                            combo = combo_code.get(task_id, None)
                            claim = await self.claim_puzzle_task(http_client=http_client, task_id=task_id, combo_code=combo)
                            if isinstance(claim, dict):
                                if claim == {}:
                                    message = ""
                                    message += f"rewarded: <g>{score}</g> tomato " if score != 0 else ''
                                    message += f"- <g>{games}</g> game " if games != 0 else ''
                                    message += f"- <g>{star}</g> star" if star != 0 else ''
                                    logger.info(f"{self.session_name} | 🎉 <g>Puzzle solved successfully</g> | Combo: <g>{combo}</g> | {message}")
                                elif "message" in claim.keys():
                                    logger.info(f"{self.session_name} | <y>puzzle not solved, first complete youtube task</y>")
                                else:
                                    logger.info(f"{self.session_name} | <y>puzzle not solved</y>")
                            else:
                                logger.info(f"{self.session_name} | <y>puzzle task not found</y>")
                        else:
                            logger.info(f"{self.session_name} | <y>puzzle code not found</y>")
                    elif task.get('status', 3) == 3:
                        logger.info(f"{self.session_name} | <y>puzzle task already solved</y>")
            else:
                logger.info(f"{self.session_name} | <y>puzzle task not found</y>")
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while processing puzzle task : {e}", exc_info=True)

    async def play_game(
        self,
        http_client: CloudflareScraper,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[dict]:
        retries = 0
        payload = {
            "game_id": GAME_ID["drop"]
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(play_game_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(play_game_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', {})
                        return data
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | starting game failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while starting game: {e}", exc_info=True)
        return False

    async def claim_game(
        self,
        http_client: CloudflareScraper,
        points: int,
        stars: int | float,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[dict]:
        retries = 0
        payload = {
            "game_id": GAME_ID["drop"],
            "points": points,
            "stars": stars
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(claim_game_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(claim_game_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(3)  # Optional delay before checking the response
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', {})
                        return data
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | claiming game failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while claiming game: {e}", exc_info=True)
        return False

    async def share_game(
        self, 
        http_client: CloudflareScraper,
        max_retries: int = 10,
        delay: int = 10
    ) -> None:
        retries = 0
        payload = {
            "game_id": GAME_ID["drop"]
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(share_game_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(share_game_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', None)
                        if data and str(data) == "ok":
                            logger.info(f"{self.session_name} | ➦ <g>game shared successfully</g> | rewarded: <g>+50 </g>tomato")
                        return True
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | sharing game failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while sharing game : {e}", exc_info=True)
        return False

    async def process_game(
        self, 
        http_client: CloudflareScraper
    ) -> None:
        try:
            play_passes = 0
            game = randint(
                settings.GAME_PLAY_EACH_ROUND[0], 
                settings.GAME_PLAY_EACH_ROUND[1]
            )
            get_balance = await self.get_balance(http_client=http_client)
            if get_balance:
                play_passes = get_balance.get("play_passes", 0)

            if play_passes > 0:
                logger.info(f"{self.session_name} | Randomly selected <c>{game}</c> attempts to play the game.")
            while play_passes > 0 and game > 0:
                pre_sleep = randint(5, 15)
                logger.info(f"{self.session_name} | 🕚 Wait <e>{pre_sleep}</e> seconds before starting game")
                await asyncio.sleep(pre_sleep)
                points = randint(
                    settings.MIN_POINTS,
                    settings.MAX_POINTS
                )
                freeze = randint(1, 4)
                game_data = await self.play_game(http_client)
                if game_data is None:
                    logger.warning(f"{self.session_name} | <y>game not started </y>")
                    break
                logger.info(f"{self.session_name} | 🎮 <g>game started </g>")
            
                sleep = 30 + freeze*3
                logger.info(f"{self.session_name} | 🕦 Wait <c>{sleep}</c> seconds to complete game!...")
                await asyncio.sleep(sleep)
                stars = game_data.get('stars', 0)
                points = points + randint(10,25) if stars == 0 else points
                claim_data = await self.claim_game(http_client=http_client, points=points, stars=stars)
                if claim_data:
                    points_ = claim_data.get('points', None)
                    stars_ = claim_data.get('stars', None)
                    message = ""
                    message += f" - <g>{stars_}</g> stars" if stars_ != 0 else ""
                    logger.info(f"{self.session_name} | 🎉 <g>Successfully game complete</g> | rewarded : <g>{points_}</g> tomato{message}")
                    await self.share_game(http_client=http_client)
                play_passes -= 1
                game -= 1
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while processing game : {e}", exc_info=True)

    async def rank_data(
        self, 
        http_client: CloudflareScraper, 
        init_data: str,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[list]:
        retries = 0
        payload = {
            "language_code": "en",
            "init_data": init_data
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(rank_data_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(rank_data_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', {})
                        return data
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | Getting rank data failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while getting rank data : {e}", exc_info=True)
        return False

    async def rank_evaluate(
        self, 
        http_client: CloudflareScraper, 
        max_retries: int = 10,
        delay: int = 10
    ) -> bool:
        retries = 0
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(rank_evaluate_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(rank_evaluate_api, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', None)
                        if data:
                            return True
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | evaluating rank failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while evaluating rank : {e}", exc_info=True)
        return False

    async def rank_create(
        self, 
        http_client: CloudflareScraper, 
        max_retries: int = 10,
        delay: int = 10
    ) -> bool:
        retries = 0
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(rank_create_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(rank_create_api, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', {})
                        if data and data.get('isCreated'):
                            name = data.get('currentRank', {}).get('name', 'Not found')
                            lvl = data.get('currentRank', {}).get('level', 'Not found')
                            logger.info(f"{self.session_name} | 🎊 <g>Successfully rank created</g> | rank name: <g>{name}</g> - level: <g>{lvl}</g>")
                            return True
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | creating rank failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while creating rank : {e}", exc_info=True)
        return False

    async def create_rank(
        self, 
        http_client: CloudflareScraper
    ) -> bool:
        try:
            rank_evaluate = await self.rank_evaluate(http_client=http_client)
            await asyncio.sleep(10)
            if rank_evaluate:
                rank_create = await self.rank_create(http_client=http_client)
                if rank_create:
                    return True
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while processing rank creation : {e}", exc_info=True)
        return False

    async def show_spin(
        self, 
        http_client: CloudflareScraper, 
        init_data: str,
        max_retries: int = 10,
        delay: int = 10
    ) -> bool:
        retries = 0
        payload = {
            "language_code": "en",
            "init_data": init_data
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(spin_show_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(spin_show_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', {})
                        if data:
                            return data.get('show', None)
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | getting spin status failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while getting spin status : {e}", exc_info=True)
        return False

    async def free_spin(
        self, 
        http_client: CloudflareScraper, 
        init_data: str,
        max_retries: int = 10,
        delay: int = 10
    ) -> bool:
        retries = 0
        payload = {
            "language_code": "en",
            "init_data": init_data
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(spin_free_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(spin_free_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', None)
                        if data:
                            return data.get('is_free', None)
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | getting free spin status failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while getting free spin status : {e}", exc_info=True)
        return False

    async def spin_once(
        self, 
        http_client: CloudflareScraper,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[dict]:
        retries = 0
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(spin_once_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(spin_once_api, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    retries += 1
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', {})
                        if data and data.get('results', {}):
                            return data.get('results', {})
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | Spinning once failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while spinning onetime free spin : {e}", exc_info=True)
        return False

    async def user_tickets(
        self, 
        http_client: CloudflareScraper, 
        init_data: str,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[dict]:
        retries = 0
        payload = {
            "language_code": "en",
            "init_data": init_data
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(user_tickets_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(user_tickets_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', {})
                        return data
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | Getting user tickets failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while getting user tickets : {e}", exc_info=True)
        return False

    async def spin_raffle(
        self, 
        http_client: CloudflareScraper,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[list]:
        retries = 0
        payload = {
            "category": "ticket_spin_1"
        }
        retries = 0
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(spin_raffle_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(spin_raffle_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', {})
                        if data and data.get('results', []):
                            return data.get('results', [])
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | spinning raffle failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while spinning raffle : {e}", exc_info=True)
        return False

    async def spin_assets(
        self, 
        http_client: CloudflareScraper,
        init_data: str,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[dict]:
        retries = 0
        payload = {
            "language_code": "en",
            "init_data": init_data
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(spin_assets_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(spin_assets_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    retries += 1
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', {})
                        if data and data.get('balances', []):
                            return data.get('balances', [])
                    else:
                        logger.warning(f"{self.session_name} | getting spin assets failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while getting spin assets : {e}", exc_info=True)
        return False

    async def process_spin(
        self, 
        http_client: CloudflareScraper,
        init_data: str
    ) -> None:
        try:
            ### befor spin check rank, if it not created, create it ###
            rank_data = await self.rank_data(http_client=http_client, init_data=init_data)
            if rank_data:
                if not rank_data['isCreated']:
                    logger.info(f"{self.session_name} | 🛠️ rank not created, creating rank... ")
                    creation_status = await self.create_rank(http_client=http_client)
                    if not creation_status:
                        logger.info(f"{self.session_name} | <y>creating rank failed</y>")
            ### check is spin slot available ###
            isSpin = await self.show_spin(http_client=http_client, init_data=init_data)
            if isSpin:
                ### check free spin ###
                free_spin = await self.free_spin(http_client=http_client, init_data=init_data)
                if free_spin:
                    logger.info(f"{self.session_name} | 🤓 <g>newbie onetime free spin available, spinning...</g>")
                    data = await self.spin_once(http_client=http_client)
                    if data:
                        amount = data.get('amount', 'not found')
                        type = data.get('type', 'not found')
                        logger.info(f"{self.session_name} | 🎉 <g>free spin (once) successfull</g> | rewarded: <g>{amount}</g> {type}")
                    else:
                        logger.info(f"{self.session_name} | <y>free spin (once) failed</y>")

                spin_data = await self.user_tickets(http_client=http_client, init_data=init_data)

                if spin_data:
                    tickets = spin_data.get('ticket_spin_1', 0)
                    logger.info(f"{self.session_name} | 🎟️ You have a total of <g>{tickets}</g> tickets to spin") if tickets > 0 else None
                    while tickets > 0:
                        raffle_data = await self.spin_raffle(http_client=http_client)
                        if raffle_data:
                            message = "Rewarded: "
                            for result in raffle_data:
                                amount = result.get('amount', 'not found')
                                type = result.get('type', 'not found')
                                message += f"- <g>{amount}</g> {type} "
                            logger.info(f"{self.session_name} | 🎉 <g>Spin successful</g> | {message}")
                        else:
                            logger.info(f"{self.session_name} | <y>spin data not available</y>")
                        tickets -= 1
                        await asyncio.sleep(5)
            else:
                logger.info(f"{self.session_name} | <y>spin not available</y>")
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while processing spin : {e}", exc_info=True)

    async def upgrade_rank(
        self, 
        http_client: CloudflareScraper,
        stars: int,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[dict]:
        payload = {
            "stars": stars
        }
        retries = 0
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(rank_upgrade_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(rank_upgrade_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', {})
                        return data
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | upgrading rank failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while upgrading rank : {e}", exc_info=True)
        return False

    async def rank_share(
        self, 
        http_client: CloudflareScraper,
        max_retries: int = 10,
        delay: int = 10
    ) -> None:
        retries = 0
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(rank_share_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(rank_share_api, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', None)
                        if data == "ok":
                            logger.info(f"{self.session_name} | ➦ <g>Rank upgrade shared successfully</g> | rewarded: <g>+2000</g> Tomato")
                        return True
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | sharing rank failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while sharing rank : {e}", exc_info=True)
        return False

    async def process_upgrade(
        self, 
        http_client: CloudflareScraper,
        init_data: str
    ) -> None:
        try:
            rank_data = await self.rank_data(http_client=http_client, init_data=init_data)
            if rank_data:
                if not rank_data['isCreated']:
                    logger.info(f"{self.session_name} | 🛠️ rank not created, creating rank... ")
                    creation_status = await self.create_rank(http_client=http_client)
                    if not creation_status:
                        logger.info(f"{self.session_name} | <y>creating rank failed</y>")
                if rank_data['isCreated']:
                    usedstars = rank_data.get('usedStars', 0)
                    unusedstars = rank_data.get('unusedStars', 0)
                    next_rank = rank_data.get('nextRank', {})
                    if next_rank:
                        minstar = next_rank.get('minStar', 0)
                        maxstar = next_rank.get('maxStar', 0)
                        name = next_rank.get('name', 'not found')
                        need_star = minstar - usedstars
                        if unusedstars >= need_star:
                            star = int(unusedstars - need_star)
                            stars = unusedstars if star == 0 else star
                            logger.info(f"{self.session_name} | 🚀 Upgrading rank with <g>{stars}</g> star...")
                            upgrade_rank = await self.upgrade_rank(http_client=http_client, stars=stars)
                            if upgrade_rank:
                                name_ = upgrade_rank.get('currentRank', {}).get('name', 'not found')
                                lvl_ = upgrade_rank.get('currentRank', {}).get('level', 0)
                                logger.info(f"{self.session_name} | 🎉 <g>Successfully rank upgraded</g> | rank name: <g>{name_}</g> - level: <g>{lvl_}</g>")
                                if upgrade_rank.get('isUpgrade', False):
                                    await self.rank_share(http_client=http_client)
                        else:
                            logger.info(f"{self.session_name} | You need <c>{need_star}</c> star to reach <g>{name}</g> level")
                    else:
                        logger.info(f"{self.session_name} | <y>rank upgrade not available</y>")
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while processing spin : {e}", exc_info=True)

    async def check_token(
        self, 
        http_client: CloudflareScraper,
        init_data: str,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[dict]:
        payload = {
            "language_code": "en",
            "init_data": init_data,
            "round": self.airdrop_season
        }
        retries = 0
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(check_token_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(check_token_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', {})
                        return data
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | checking airdrop failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while checking airdrop : {e}", exc_info=True)
        return False

    async def token_balance(
        self, 
        http_client: CloudflareScraper,
        init_data: str,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[float]:
        payload = {
            "language_code": "en",
            "init_data": init_data,
        }
        retries = 0
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(token_balance_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(token_balance_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', {})
                        return round(float(data.get('total', 0)), 2)
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | getting token balance failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while getting token balance : {e}", exc_info=True)
        return False

    async def claim_token(
        self, 
        http_client: CloudflareScraper,
        max_retries: int = 10,
        delay: int = 10,
        round: str = None,
    ) -> Optional[dict]:
        round = round or self.airdrop_season
        payload = {"round": round}
        retries = 0
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(claim_token_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(claim_token_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', {})
                        return data
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | claiming token failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while claiming token : {e}", exc_info=True)
        return False

    async def process_airdrop(
        self, 
        http_client: CloudflareScraper,
        init_data: str
    ) -> None:
        try:
            check_token = await self.check_token(http_client=http_client, init_data=init_data)
            if check_token:
                rank = check_token.get('rank', 'not found')
                iswitch = check_token.get('isWitch', False)
                claimed = check_token.get('claimed', True)
                if iswitch:
                    if claimed:
                        logger.info(f"{self.session_name} | You already claimed <g>$TOMA</g>")
                    else:
                        claim_drop = await self.claim_token(http_client=http_client)
                        if claim_drop:
                            amount = round(float(claim_drop.get('amount', 0)), 2)
                            logger.info(f"{self.session_name} | Successfully claimed <g>{amount} $TOMA</g>")
                        else:
                            logger.info(f"{self.session_name} | claiming $TOMA failed")
                    t_balance = await self.token_balance(http_client=http_client, init_data=init_data)
                    logger.info(f"{self.session_name} | you have total <g>{t_balance} $TOMA</g>")
                else:
                    logger.info(f"{self.session_name} | You are not eligible to claim <g>$TOMA</g> because a minimum rank of <g>Bronze IV</g> is required, but your rank is <g>{rank}</g>.")
                
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while processing airdrop : {e}", exc_info=True)

    async def airdrop_task_list(
        self, 
        http_client: CloudflareScraper, 
        init_data: str,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[list]:
        retries = 0
        payload = {
            "language_code": "en",
            "init_data": init_data,
            "round": self.airdrop_season
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(airdrop_task_list_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(airdrop_task_list_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', [])
                        return data
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | Getting task list failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while getting airdrop task list : {e}", exc_info=True)
        return False

    async def start_airdrop_task(
        self, 
        http_client: CloudflareScraper, 
        init_data: str, 
        task_id: int,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[dict]:
        retries = 0
        payload = {
            "task_id": task_id,
            "round": self.airdrop_season
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(airdrop_task_start_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(airdrop_task_start_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', {})
                        return data
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | Starting airdrop task failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while starting airdrop task: {e}", exc_info=True)
        return False

    async def check_airdrop_task(
        self, 
        http_client: CloudflareScraper, 
        init_data: str, 
        task_id: int, 
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[bool]:
        retries = 0
        status_check = 0
        payload = {
            "task_id": task_id,
            "round": self.airdrop_season
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(airdrop_task_check_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(airdrop_task_check_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=4)
                    
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)
                        data = response_json.get('data', {})
                        if data.get('status', 1) == 2:
                            return True
                        else:
                            status_check += 1
                            if status_check >= 10:
                                return False
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | Checking airdrop task failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while checking airdrop task : {e}", exc_info=True)
        return False

    async def claim_airdrop_task(
        self, 
        http_client: CloudflareScraper, 
        task_id: int,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[dict]:
        retries = 0
        payload = {
            "task_id": task_id,
            "round": self.airdrop_season
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(airdrop_task_claim_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(airdrop_task_claim_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)  
                        return response_json
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | Claiming airdrop task failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while claiming airdrop task : {e}", exc_info=True)
        return False

    async def process_airdrop_task(
        self,
        http_client: CloudflareScraper,
        init_data: str
    ) -> None:
        try:
            check_token = await self.check_token(http_client=http_client, init_data=init_data)
            if check_token:
                claimed = check_token.get('claimed', False)
                if claimed:
                   task_data = await self.airdrop_task_list(http_client=http_client, init_data=init_data)
                   logger.info(f"{self.session_name} | ⚙️ Processing airdrop task...")
                   tasks_list = [
                        task
                        for task in task_data
                        if task.get("type") not in settings.DISABLED_TASKS
                        and task.get("enable") is True
                        and convert_utc_to_local(task.get("checkStartTime", "1970-01-01 00:00:00")) <= int(time())
                        and (
                            (task.get("checkEndTime") == "" or convert_utc_to_local(task.get("endTime", "9998-12-31 23:59:59")) >= int(time()))
                        ) 
                        and task.get("status", 3) != 3
                    ]
                   for task in tasks_list:
                       task_id = task.get('taskId')
                       status = task.get('status')
                       waitSecond = task.get('waitSecond', 0)
                       name = task.get('name', 'not found')
                       reward = round(float(task.get('amount', 0)), 2)
                 
                       if status == 0:
                           logger.info(f"{self.session_name} | ⚙️ Performing airdrop task <g>{name}</g>")
                           start_task = await self.start_airdrop_task(http_client=http_client, init_data=init_data, task_id=task_id)
                           if isinstance(start_task, dict) and start_task.get("status", 0) == 1:
                               logger.info(f"{self.session_name} | 🥳 Task <g>{name}</g> started successfully")
                               logger.info(f"{self.session_name} | 🕚 Sleep <e>{max(0, waitSecond)}</e> second before finishing <g>{name}</g>")
                               await asyncio.sleep(max(0,waitSecond))
                               check_task = await self.check_airdrop_task(http_client=http_client, init_data=init_data, task_id=task_id)
                               if check_task:
                                   logger.info(f"{self.session_name} | 🥳 Task <g>{name}</g> finished successfully")
                                   claim_task = await self.claim_airdrop_task(http_client=http_client, task_id=task_id)
                                   if claim_task.get('data', None) == 'ok':
                                       logger.info(f"{self.session_name} | 🎉 Task <g>{name}</g> claimed successfully | rewarded : <g>+{reward} $TOMA</g>")
                                   else:
                                       logger.info(f"{self.session_name} | <y>Task {name} not claimed</y>")
                               else:
                                   logger.info(f"{self.session_name} | <y>Task {name} not finished</y>")
                           elif isinstance(start_task, dict) and start_task.get("status", 0) == 2:
                               claim_task = await self.claim_airdrop_task(http_client=http_client, task_id=task_id)
                               if claim_task.get('data', None) == 'ok':
                                   logger.info(f"{self.session_name} | 🎉 Task <g>{name}</g> claimed successfully | rewarded : <g>+{reward} $TOMA</g>")
                               else:
                                   logger.info(f"{self.session_name} | <y>Task {name} not claimed</y>")
                           elif isinstance(start_task, str) and start_task == "ok":
                               logger.info(f"{self.session_name} | 🎉 Task <g>{name}</g> claimed successfully | rewarded : <g>+{reward} $TOMA</g>")
                           else:
                               logger.info(f"{self.session_name} | <y>Task {name} not started</y>")
                       elif status == 1:
                           check_task = await self.check_airdrop_task(http_client=http_client, init_data=init_data, task_id=task_id)
                           if check_task:
                               logger.info(f"{self.session_name} | 🥳 Task <g>{name}</g> finished successfully")
                               claim_task = await self.claim_airdrop_task(http_client=http_client, task_id=task_id)
                               if claim_task.get('data', None) == 'ok':
                                   logger.info(f"{self.session_name} | 🎉 Task <g>{name}</g> claimed successfully | rewarded : <g>+{reward} $TOMA</g>")
                               else:
                                   logger.info(f"{self.session_name} | <y>Task {name} not claimed</y>")
                           else:
                               logger.info(f"{self.session_name} | <y>Task {name} not finished</y>")
                       elif status == 2:
                           claim_task = await self.claim_airdrop_task(http_client=http_client, task_id=task_id)
                           if claim_task.get('data', None) == 'ok':
                               logger.info(f"{self.session_name} | 🎉 Task <g>{name}</g> claimed successfully | rewarded : <g>+{reward} $TOMA</g>")
                           else:
                               logger.info(f"{self.session_name} | <y>Task {name} not claimed</y>")
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while processing airdrop task : {e}", exc_info=True)

    async def check_treasure_box(
        self, 
        http_client: CloudflareScraper, 
        init_data: str,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[dict]:
        retries = 0
        payload = {
            "language_code": "en",
            "init_data": init_data
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(treasure_status_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(treasure_status_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)  
                        return response_json.get('data', {})
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | getting treasure box info failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while getting treasure box info : {e}", exc_info=True)
        return False

    async def open_treasure_box(
        self, 
        http_client: CloudflareScraper, 
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[dict]:
        retries = 0
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(treasure_open_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(treasure_open_api, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)  
                        return response_json.get('data', {})
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | Claiming treasure reward failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while claiming treasure reward : {e}", exc_info=True)
        return False

    async def treasure_balance(
        self, 
        http_client: CloudflareScraper, 
        init_data: str,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[dict]:
        retries = 0
        payload = {
            "language_code": "en",
            "init_data": init_data
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(treasure_balance_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(treasure_balance_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)  
                        return response_json.get('data', {})
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | getting treasure balance failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while getting treasure balance : {e}", exc_info=True)
        return False

    async def process_treasure(
        self,
        http_client: CloudflareScraper,
        init_data: str
    ) -> None:
        try:
            isOpen = await self.check_treasure_box(http_client=http_client, init_data=init_data)
            if isOpen:
                if isOpen.get('open_status', 1) == 0:
                    open_treasure = await self.open_treasure_box(http_client=http_client)
                    if open_treasure:
                        amount = open_treasure.get('toma_reward', None)
                        logger.info(f"{self.session_name} | 🎉 <g>Successfully treasure box opened</g> | rewarded: <g>{amount} $TOMA</g>")

        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while processing treasure task : {e}", exc_info=True)
    
    async def get_season_token(
        self, 
        http_client: CloudflareScraper, 
        init_data: str,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[dict]:
        retries = 0
        payload = {
            "language_code": "en",
            "init_data": init_data
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(season_token_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(season_token_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)  
                        return response_json.get('data', {})
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | getting season token failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while getting season token : {e}", exc_info=True)
        return False

    async def process_weekly_airdrop(
        self,
        http_client: CloudflareScraper,
        init_data: str
    ) -> None:
        try:
            season_token = await self.get_season_token(http_client=http_client, init_data=init_data)
            if season_token:
                round_ = season_token['round'].get('name', 'Not found')
                start_time = convert_utc_to_local(season_token['round'].get('startTime', '1970-01-01 00:00:00'))
                end_time = season_token['round'].get('endTime', '9998-12-31 23:59:59')
                current_time = int(time())
                isClaimed = season_token.get('claimed', True)
                if current_time >= convert_utc_to_local(end_time):
                    if not isClaimed:
                        claim_token = await self.claim_token(http_client=http_client, round=round_)
                        if claim_token:
                            amount = claim_token.get('amount', None)
                            logger.info(f"{self.session_name} | 🎉 <g>Successfully claimed weekly airdrop round {round_}</g> | rewarded : <g>{amount} $TOMA</g>")
                        else:
                            logger.info(f"{self.session_name} | <y>claim token failed</y>")
                    else:
                        logger.info(f"{self.session_name} | <y>Weekly airdrop ended</y>")
                else:
                    toma = round(season_token.get('toma', 0), 2)
                    stars = season_token.get('stars', None)
                    timestamp_end = convert_utc_to_local(end_time)
                    target_time = datetime.fromtimestamp(timestamp_end)
                    days, hours, minutes, seconds = time_until(target_time)
                    logger.info(f"{self.session_name} | Weekly round: <g>{round_}</g> | Claimable: <g>{toma}</g> $TOMA - <g>{stars}</g> Stars | End in: <g>{days}</g> days, <g>{hours}</g> hours, <g>{minutes}</g> minutes, <g>{seconds}</g> seconds")
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while processing weekly airdrop : {e}", exc_info=True)
    
    async def tomatoes(
        self, 
        http_client: CloudflareScraper, 
        init_data: str,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[dict]:
        retries = 0
        payload = {
            "language_code": "en",
            "init_data": init_data
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(tomatoes_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(tomatoes_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)  
                        return response_json.get('data', {})
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | getting tomatoes failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while getting tomatoes : {e}", exc_info=True)
        return False

    async def swap_tomato(
        self, 
        http_client: CloudflareScraper, 
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[dict]:
        retries = 0
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(swap_tomato_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(swap_tomato_api, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)  
                        return response_json.get('data', {}).get('success', False)
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | swaping tomatoes failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while swaping tomatoes : {e}", exc_info=True)
        return False
    
    async def process_swap_tomato(
        self,
        http_client: CloudflareScraper,
        init_data: str
    ) -> None:
        try:
            tomato = await self.tomatoes(http_client=http_client, init_data=init_data)
            balance = int(tomato.get('balance', 0))
            if balance >= 20_000:
                star = round(balance / 20_000)
                swap_me = await self.swap_tomato(http_client=http_client)
                if swap_me:
                    logger.info(f"{self.session_name} | 🎉 <g>Successfully swaped {20_000 * star} tomato</g> | rewarded : <g>+{star}</g> Star")
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while processing swap tomato to star : {e}", exc_info=True)
            
    async def get_auto_farms(
        self, 
        http_client: CloudflareScraper, 
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[list]:
        retries = 0
        payload = {}
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(get_auto_farms_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(get_auto_farms_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)  
                        return response_json.get('data', [])
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | getting farm list failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while getting farm list: {e}", exc_info=True)
        return False
    
    async def launchpad_task_status(
        self, 
        http_client: CloudflareScraper, 
        launchpad_id: int,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[list]:
        retries = 0
        payload = {
            "launchpad_id": launchpad_id
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(launchpad_task_status_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(launchpad_task_status_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)  
                        return response_json.get('data', {}).get('success', False)
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | getting launchpad task status failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while getting launchpad task status: {e}", exc_info=True)
        return False
    
    async def launchpad_task_list(
        self, 
        http_client: CloudflareScraper,
        launchpad_id: int,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[list]:
        retries = 0
        payload = {
            "launchpad_id": launchpad_id
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(launchpad_tasks_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(launchpad_tasks_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)  
                        return response_json.get('data', [])
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | getting launchpad task list failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while getting launchpad task list: {e}", exc_info=True)
        return False

    async def claim_launchpad_task(
        self, 
        http_client: CloudflareScraper, 
        launchpad_id: int,
        task_id: int,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[list]:
        retries = 0
        payload = {
            "launchpad_id": launchpad_id,
            "task_id": task_id
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(launchpad_task_claim_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(launchpad_task_claim_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)  
                        return response_json.get('data', {}).get('success', False)
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | claiming launchpad task failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while claiming launchpad task: {e}", exc_info=True)
        return False

    async def process_launchpad_task(
        self,
        http_client: CloudflareScraper,
        launchpad_id: int
    ) -> None:
        try:
            launchpad_tasks = await self.launchpad_task_list(http_client=http_client, launchpad_id=launchpad_id)
            if launchpad_tasks:
                task_list = [
                    task
                    for task in launchpad_tasks
                    if task.get("enable") is True
                    and task.get("status", 3) == 0
                ]
                for task in task_list:
                    task_id = task.get('taskId')
                    status = task.get('status')
                    waitSecond = task.get('waitSecond', 0)
                    name = task.get('name', 'not found')

                    if status == 0:
                        claim_task = await self.claim_launchpad_task(http_client=http_client, task_id=task_id, launchpad_id=launchpad_id)
                        if claim_task:
                            logger.info(f"{self.session_name} | 🎉 Launchpad task <g>{name}</g> Completed")
                        else:
                            logger.info(f"{self.session_name} | <y>Task {name} not Completed</y>")   
            else:
                logger.info(f"{self.session_name} | <y>launchpad task not found</y>")
        except Exception as e:
                logger.warning(f"{self.session_name} | Unknown error while processing launchpad task : {e}", exc_info=True)
    
    async def invest_toma(
        self, 
        http_client: CloudflareScraper, 
        launchpad_id: int,
        amount: int,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[list]:
        retries = 0
        payload = {
            "launchpad_id": launchpad_id,
            "amount": amount
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(invest_toma_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(invest_toma_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)  
                        return response_json.get('data', {}).get('success', False)
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | staking toma failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while staking toma: {e}", exc_info=True)
        return False
    
    async def stake_toma(
        self,
        http_client: CloudflareScraper,
        init_data: str,
        launchpad_id: int,
        invested_toma: int,
        minInvest: int
    ) -> None:
        try:
            if invested_toma == 0:
                balance = await self.token_balance(http_client=http_client, init_data=init_data)
                toma_balance = int(balance)
            
                if settings.STAKE_TOMA_IN_LAUNCHPOOL and toma_balance >= minInvest:
                    amount = toma_balance if settings.STAKE_ALL_TOMA else minInvest
                else:
                    amount = 0
            
                invest_status = await self.invest_toma(http_client=http_client, launchpad_id=launchpad_id, amount=amount)
                if invest_status and amount != 0:
                    logger.info(f"{self.session_name} | 🎉 Total <g>{amount} $TOMA</g> staked, you will receive your $TOMA at the end of pool")
            
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while processing stake : {e}", exc_info=True)
    
    async def get_launchpad_detail(
        self, 
        http_client: CloudflareScraper, 
        launchpad_id: int,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[dict]:
        retries = 0
        payload = {
            "launchpad_id": launchpad_id
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(launchpad_detail_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(launchpad_detail_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)  
                        return response_json.get('data', {})
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | getting launchpad details failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while getting launchpad details: {e}", exc_info=True)
        return False
    
    async def start_auto_farm(
        self, 
        http_client: CloudflareScraper, 
        launchpad_id: int,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[list]:
        retries = 0
        payload = {
            "launchpad_id": launchpad_id
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(start_auto_farm_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(start_auto_farm_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)  
                        return response_json.get('data', {})
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | starting auto farm failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while starting auto farm: {e}", exc_info=True)
        return False
    
    async def claim_launchpool(
        self, 
        http_client: CloudflareScraper, 
        launchpad_id: int,
        max_retries: int = 10,
        delay: int = 10
    ) -> Optional[list]:
        retries = 0
        payload = {
            "launchpad_id": launchpad_id
        }
        try:
            while retries < max_retries:
                async with self.lock:
                    await http_client.options(claim_auto_farms_api, headers=options_headers(method="POST", kwarg=http_client.headers), ssl=settings.ENABLE_SSL)
                    response = await http_client.post(claim_auto_farms_api, json=payload, timeout=ClientTimeout(20), ssl=settings.ENABLE_SSL)
                    await asyncio.sleep(delay=3)
                    if response.status == 200:
                        response_json = await extract_json_from_response(response=response)  
                        return response_json.get('data', {})
                    else:
                        retries += 1
                        logger.warning(f"{self.session_name} | claiming launchpad task failed: <r>{response.status}</r>, retying... (<g>{retries}</g>/<r>{max_retries}</r>)")
                        await asyncio.sleep(delay)
                        delay *= 2
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while claiming launchpad task: {e}", exc_info=True)
        return False
    
    async def process_farmingpool(
        self,
        http_client: CloudflareScraper,
        init_data: str
    ) -> None:
        try:
            pool_list = await self.get_auto_farms(http_client=http_client)
            if pool_list:
                for pool in pool_list:
                    isFinished = pool.get('finish', True)
                    if not isFinished:
                        launchpad_id = pool.get('launchpad_id')
                        title = pool.get('title','title not found')
                    
                        launchpad_detail = await self.get_launchpad_detail(http_client=http_client, launchpad_id=launchpad_id)
                        minInvest = int(launchpad_detail.get('minInvestToma', '10000'))
                        invested_toma = int(launchpad_detail.get('totalInvest', '0'))
                        token_name = launchpad_detail.get('tokenName', None)
                        await self.process_launchpad_task(http_client=http_client, launchpad_id=launchpad_id)
                        is_task_completed = await self.launchpad_task_status(http_client=http_client, launchpad_id=launchpad_id)
                        if is_task_completed:
                            start_at = int(pool.get('start_at'))
                            end_at = int(pool.get('end_at'))
                            if start_at == 0 == end_at:
                                await self.stake_toma(http_client=http_client, init_data=init_data, launchpad_id=launchpad_id, minInvest=minInvest, invested_toma=invested_toma)
                                start_farm = await self.start_auto_farm(http_client=http_client, launchpad_id=launchpad_id)
                                if start_farm:
                                    pool_end = start_farm.get('end_at', None)
                                    target_time = datetime.fromtimestamp(pool_end)
                                    days, hours, minutes, seconds = time_until(target_time)
                                    logger.info(f"{self.session_name} | 🎉 Launchpool <g>{title}</g> started | End in: <g>{days}</g> days, <g>{hours}</g> hours, <g>{minutes}</g> minutes, <g>{seconds}</g> seconds")
                            elif int(time()) > end_at:
                                claim_farm = await self.claim_launchpool(http_client=http_client, launchpad_id=launchpad_id)
                                if claim_farm:
                                    amount = claim_farm.get('cur_claimed', {}).get('total_points',0)
                                    logger.info(f"{self.session_name} | <g>Successfully claimed {title} launchpool</g> | rewarded: <g>{amount} {token_name}</g>")
                                    start_farm = await self.start_auto_farm(http_client=http_client, launchpad_id=launchpad_id)
                                    if start_farm:
                                        pool_end = start_farm.get('end_at', None)
                                        target_time = datetime.fromtimestamp(pool_end)
                                        days, hours, minutes, seconds = time_until(target_time)
                                        logger.info(f"{self.session_name} | 🎉 Launchpool <g>{title}</g> started | End in: <g>{days}</g> days, <g>{hours}</g> hours, <g>{minutes}</g> minutes, <g>{seconds}</g> seconds")
                                
                            elif end_at > int(time()):
                                target_time = datetime.fromtimestamp(end_at)
                                days, hours, minutes, seconds = time_until(target_time)
                                logger.info(f"{self.session_name} | 🌾 <g>Launchpool Farming in progress</g>, next claim in: <g>{days}</g> days, <g>{hours}</g> hours, <g>{minutes}</g> minutes, <g>{seconds}</g> seconds")
                        else:
                            logger.info(f"{self.session_name} | <y>launchpad task not completed</y>")
                        
        except Exception as e:
            logger.warning(f"{self.session_name} | Unknown error while processing farming pool : {e}", exc_info=True)
    
    async def run(
        self, 
        user_agent: str, 
        proxy: str | None
    ) -> None:
        if settings.USE_RANDOM_DELAY_IN_RUN:
            random_delay = randint(settings.START_DELAY[0], settings.START_DELAY[1])
            logger.info(f"{self.session_name} | 🕚 wait <c>{random_delay}</c> second before starting...")
            await asyncio.sleep(random_delay)

        if 'socks' in str(proxy):
            proxy_conn = socks_connector.from_url(proxy)
        elif 'http' in str(proxy):
            proxy_conn = http_connector.from_url(proxy)
        else:
            proxy_conn = None
        headers = get_headers()
        headers["User-Agent"] = user_agent
        chrome_ver = extract_chrome_version(user_agent=headers['User-Agent']).split('.')[0]
        headers['Sec-Ch-Ua'] = f'"Chromium";v="{chrome_ver}", "Android WebView";v="{chrome_ver}", "Not?A_Brand";v="24"'
        tg_web_data = await self.get_tg_web_data(proxy=proxy)
        if tg_web_data is None:
            logger.warning(f"{self.session_name} | retrieving telegram web data failed")
            return
        timeout = ClientTimeout(total=60)
        async with CloudflareScraper(headers=headers, connector=proxy_conn, trust_env=True, auto_decompress=False, timeout=timeout) as http_client:

            if proxy:
                await self.check_proxy(http_client=http_client, proxy=proxy)

            while True:
                can_run = True
                try:
                    sleep_time = 360
                    if await check_base_url(self.session_name) is False:
                        can_run = False
                        if settings.ADVANCED_ANTI_DETECTION:
                            logger.warning("<y>Detected index js file change. Contact me to check if it's safe to continue</y>: <g>https://t.me/scripts_hub</g>")
                            return sleep_time

                        else:
                            logger.warning("<y>Detected api change! Stopped the bot for safety. Contact me here to update the bot</y>: <g>https://t.me/scripts_hub</g>")
                            return sleep_time

                    end_at = 21600
                    if can_run:
                        self.access_token = await self.login(http_client=http_client, init_data=tg_web_data)
                        if self.access_token is None:
                            continue
                        if await is_expired(self.access_token):
                            continue

                        http_client.headers['Authorization'] = f"{self.access_token}"

                        await self.claim_daily(http_client=http_client)

                        get_balance = await self.get_balance(http_client=http_client)
                        if get_balance:
                            balance = get_balance.get("available_balance", None)
                            play_pass = get_balance.get("play_passes", None)
                            logger.info(f"{self.session_name} | Balance: <g>{balance}</g> - Play pass: <g>{play_pass}</g>")

                        await self.process_wallet_task(http_client=http_client, init_data=tg_web_data)
                        if settings.AUTO_FARMING:
                            farm_info = await self.farm_info(http_client=http_client)

                            if isinstance(farm_info, dict):
                                if farm_info == {}:
                                    start_data = await self.start_farm(http_client=http_client)
                                    end_at = start_data.get("end_at", int(time()*2))
                                else:
                                    end_at = farm_info.get("end_at", int(time()*2))
                                    if int(time()) > end_at:
                                        claim = await self.claim_farm(http_client=http_client)
                                        if claim:
                                            start_data = await self.start_farm(http_client=http_client)
                                            end_at = start_data.get("end_at", int(time()*2))
                                    else:
                                        logger.info(f"{self.session_name} | 🌾 Farming in progress, next claim in <g>{round((end_at - time()) / 60)}</g> minutes")

                        if settings.AUTO_TASK:
                            await self.process_task(http_client=http_client, tg_web_data=tg_web_data)
                        if settings.AUTO_SOLVE_PUZZLE:
                            await self.solve_puzzle_task(http_client=http_client, init_data=tg_web_data)
                        if settings.AUTO_PLAY_GAME:
                            await self.process_game(http_client=http_client)
                        if settings.AUTO_SPIN:
                            await self.process_spin(http_client=http_client, init_data=tg_web_data)
                        if settings.AUTO_RANK_UPGRADE:
                            await self.process_upgrade(http_client=http_client, init_data=tg_web_data)
                        if settings.AUTO_SWAP_TOMATO_TO_STAR:
                            await self.process_swap_tomato(http_client=http_client, init_data=tg_web_data)
                        if settings.PARTICIPATE_IN_FARMINGPOOL:
                            await self.process_farmingpool(http_client=http_client, init_data=tg_web_data)
                        ### spin assets ###
                        spin_assets = await self.spin_assets(http_client=http_client, init_data=tg_web_data)
                        if spin_assets:
                            message = ""
                            for balance in spin_assets:
                                balance_ = round(float(balance.get("balance", 0)), 2) if not isinstance(balance.get("balance", 0), int) else balance.get("balance", 0)
                                type = balance.get("balance_type", None)
                                message += f'- <g>{balance_}</g> {type} ' if balance_ != 0 else ""
                            logger.info(f"{self.session_name} | 🌐 All balance : {message}")

                        
                    if self.multi_thread is True:
                        sleep = round((end_at - time()) / 60) + randint(5,9)
                        logger.info(f"{self.session_name} | 🕦 Sleep <y>{sleep}</y> min")
                        await asyncio.sleep(sleep * 60)
                    else:
                        logger.info(f"{self.session_name} | <m>==== Completed ====</m>")
                        await asyncio.sleep(3)
                        return round((end_at - time()) / 60)
                except InvalidSession as error:
                    raise error

                except Exception as error:
                    traceback.print_exc()
                    logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Unknown error: {error}")
                    await asyncio.sleep(delay=randint(60, 120))

async def run_tapper(tg_client: Client, user_agent: str, proxy: str | None):
    try:
        await Tapper(
            tg_client=tg_client,
            multi_thread=True
        ).run(
            user_agent=user_agent,
            proxy=proxy,
        )
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")

async def run_tapper_synchronous(accounts: list[dict]):
    while True:
        for account in accounts:
            try:
                session_name, user_agent, raw_proxy = account.values()
                tg_client = await get_tg_client(session_name=session_name, proxy=raw_proxy)
                proxy = get_proxy(raw_proxy=raw_proxy)
                                
                _ = await Tapper(
                    tg_client=tg_client,
                    multi_thread=False
                ).run(
                    proxy=proxy,
                    user_agent=user_agent,
                )

                sleep = min(_ or 0, (_ or 0) + randint(5, 9))

            except InvalidSession:
                logger.error(f"{tg_client.name} | Invalid Session")

        logger.info(f"Sleep <red>{round(sleep, 1)}</red> minutes")
        await asyncio.sleep(sleep * 60)
