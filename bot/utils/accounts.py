import os
import json
from better_proxy import Proxy

from bot.utils import logger
from bot.config import settings
from bot.utils.proxy import get_proxies
from bot.core.agents import generate_random_user_agent
from bot.utils.file_manager import load_from_json, save_to_json


class Accounts:
    def __init__(self):
        self.workdir = "sessions/"
        self.api_id = settings.API_ID
        self.api_hash = settings.API_HASH

    def get_unused_proxy(self, used_proxies: list) -> str:

        proxies = get_proxies()
        for proxy in proxies:
            if proxy not in used_proxies:
                return proxy
        return None

    def parse_sessions(self) -> list:

        sessions = [
            file.replace(".session", "")
            for file in os.listdir(self.workdir)
            if file.endswith(".session")
        ]
        #logger.info(f"Searched sessions: <g>{len(sessions)}</g>")
        return sessions

    def get_available_accounts(self, sessions: list) -> list:

        accounts_file = "sessions/accounts.json"
        accounts_from_json = load_from_json(accounts_file)

        if not accounts_from_json:
            raise ValueError("Can't run script | Please add accounts in sessions/accounts.json")

        # Track used proxies to avoid duplicates
        used_proxies = [account["proxy"] for account in accounts_from_json if account["proxy"]]

        accounts_from_json_filtered = [
            account for account in accounts_from_json if account["session_name"] != "name_example"
        ]

        available_accounts = []

        # Check proxy-session length mismatch
        proxies = get_proxies() if settings.USE_PROXY_FROM_FILE else []
        if settings.USE_PROXY_FROM_FILE and len(proxies) != len(sessions):
            logger.warning(f"Proxy count (<g>{len(proxies)}</g>) does not match session count (<g>{len(sessions)}</g>).")

        for session in sessions:
            account = next((acc for acc in accounts_from_json_filtered if acc["session_name"] == session), None)

            if account:
                # Update proxy if required
                if settings.USE_PROXY_FROM_FILE and not account.get("proxy"):
                    unused_proxy = self.get_unused_proxy(used_proxies)
                    if unused_proxy:
                        account["proxy"] = unused_proxy
                        used_proxies.append(unused_proxy)
                    else:
                        logger.warning(f"No unused proxies available for session: {session}")
                elif not settings.USE_PROXY_FROM_FILE:
                    account["proxy"] = None
            else:
                # Create a new account entry for missing sessions
                user_agent = generate_random_user_agent(device_type='android', browser_type='chrome')
                proxy = None
                if settings.USE_PROXY_FROM_FILE:
                    proxy = self.get_unused_proxy(used_proxies)
                    if proxy:
                        used_proxies.append(proxy)

                account = {
                    "session_name": session,
                    "user_agent": user_agent,
                    "proxy": proxy,
                }
                accounts_from_json.append(account)
                logger.success(f"Account <g>{session}</g> added successfully")

            available_accounts.append(account)

        # Save updated accounts to the JSON file
        save_to_json(accounts_file,accounts_from_json)

        return available_accounts

    async def get_accounts(self) -> list:

        sessions = self.parse_sessions()
        available_accounts = self.get_available_accounts(sessions)

        if not available_accounts:
            raise ValueError("Available accounts not found! Please add accounts in the 'sessions' folder")
        else:
            logger.success(f"Available accounts: <g>{len(available_accounts)}</g>")

        return available_accounts