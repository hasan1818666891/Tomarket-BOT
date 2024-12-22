from pyrogram import Client

from bot.utils import logger
from bot.config import settings
from bot.core.agents import generate_random_user_agent
from bot.utils.file_manager import load_from_json, save_to_json


async def register_sessions() -> None:
    API_ID = settings.API_ID
    API_HASH = settings.API_HASH

    if not API_ID or not API_HASH:
        raise ValueError("API_ID and API_HASH not found in the .env file.")

    session_name = input('\nEnter the session name (press Enter to exit): ')

    if not session_name:
        return None

    raw_proxy = str(input(
        "Input the proxy in the format type://user:pass@ip:port (press Enter to use without proxy): ")).strip()

    accounts_data = load_from_json('sessions/accounts.json')

    # Create the session details
    user_agent = generate_random_user_agent(
        device_type='android', browser_type='chrome')
    session_info = {
        "session_name": session_name,
        "user_agent": user_agent,
        "proxy": raw_proxy if raw_proxy != "" else None
    }

    # Append the new session information to the accounts data
    accounts_data.append(session_info)

    # Save the updated accounts data to JSON
    save_to_json('sessions/accounts.json', accounts_data)

    # Establish the client with the provided session and proxy
    session = await get_tg_client(session_name=session_name, proxy=raw_proxy)
    async with session:
        user_data = await session.get_me()

    logger.success(
        f'Session added successfully @{user_data.username} | {user_data.first_name} {user_data.last_name}')


async def get_tg_client(session_name: str, proxy: str | None) -> Client:
    if not session_name:
        raise FileNotFoundError(f"Not found session {session_name}")

    if not settings.API_ID or not settings.API_HASH:
        raise ValueError("API_ID and API_HASH not found in the .env file.")

    proxy_dict = None
    if proxy:
        # Parse the proxy string (e.g., socks5://username:password@hostname:port)
        proxy_parts = proxy.split("://")
        scheme = proxy_parts[0]  # e.g., "socks5"
        user_pass, hostname_port = proxy_parts[1].split("@")
        username, password = user_pass.split(":")
        hostname, port = hostname_port.split(":")
        port = int(port)  # Ensure the port is an integer

        # Construct the proxy dictionary
        proxy_dict = {
            "scheme": scheme,
            "username": username,
            "password": password,
            "hostname": hostname,
            "port": port
        }

    tg_client = Client(
        name=session_name,
        api_id=settings.API_ID,
        api_hash=settings.API_HASH,
        workdir="sessions/",
        proxy=proxy_dict
    )

    return tg_client
