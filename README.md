# [![Static Badge](https://img.shields.io/badge/Telegram-Bot%20Link-Link?style=for-the-badge&logo=Telegram&logoColor=white&logoSize=auto&color=blue)](https://t.me/Tomarket_ai_bot/app?startapp=0000A4cW)

## Tomarket Bot

> **Recommendation**: Use **Python 3.10**

---

# Features
| Feature                           | Supported |
|-----------------------------------|:---------:|
| Multithreading                    |     ✅     |
| Proxy binding to session (adv)    |     ✅     |
| User-Agent binding to session     |     ✅     |
| Support for `.session` files      |     ✅     |
| Auto registration in bot          |     ✅     |
| Auto-tasks                        |     ✅     |
| Auto bind wallets                 |     ✅     |
| Daily rewards                     |     ✅     |
| Auto farming                      |     ✅     |
| Auto claim airdrop                |     ✅     |
| Auto claim airdrop tasks          |     ✅     |
| Auto play drop game               |     ✅     |
| Auto solve puzzles                |     ✅     |
| Auto spin                         |     ✅     |
| Auto claim weekly airdrop         |     ✅     |
| Auto upgrade rank                 |     ✅     |
| Auto claim treasure box           |     ✅     |
| Auto swap tomato to star          |     ✅     |
| Advanced anti-detection           |     ✅     |

---

## [Settings](https://github.com/khondokerXhasan/Tomarket-BOT/blob/master/.env-example/)
| Setting                  | Description                                                                                               | Default Value           |
|--------------------------|-----------------------------------------------------------------------------------------------------------|-------------------------|
| **API_ID / API_HASH**    | Platform data from which to run the Telegram session.                                                     | Required for operation  |
| **USE_RANDOM_DELAY_IN_RUN** | Enables random delays during task execution to avoid detection.                                        | `True`                 |
| **START_DELAY**          | Delay (in seconds) between session starts.                                                               | `[30, 60]`             |
| **AUTO_FARMING**         | Enable or disable automatic farming                                                                      | `True`                 |
| **AUTO_TASK**            | Enable or disable automatic task execution.                                                              | `True`                 |
| **JOIN_TG_CHANNELS**     | Auto-join Telegram channels for tasks.                                                                   | `False`                |
| **ARCHIVE_CHANNELS**     | Automatically archive joined Telegram channels.                                                          | `False`                |
| **AUTO_ADD_WALLET**      | Automatically add wallets with seed phrases and public keys and save to `wallets.json`.                  | `False`                |
| **AUTO_SOLVE_PUZZLE**    | Automatically solve puzzles for rewards.                                                                 | `True`                 |
| **AUTO_RANK_UPGRADE**    | Automatically upgrade rank when criteria are met.                                                        | `True`                 |
| **AUTO_SPIN**            | Automatically claim spin rewards.                                                                        | `True`                 |
| **AUTO_CLAIM_AIRDROP**   | Automatically claim seasonal airdrops.                                                                   | `True`                 |
| **AUTO_AIRDROP_TASK**    | Automatically complete airdrop tasks.                                                                    | `True`                 |
| **AUTO_CLAIM_WEEKLY_AIRDROP** | Automatically claim weekly airdrop rewards.                                                         | `True`                 |
| **AUTO_CLAIM_TREASURE**  | Automatically claim treasure rewards.                                                                    | `True`                 |
| **AUTO_SWAP_TOMATO_TO_STAR** | Automatically swap in-game tomatoes to stars for upgrades.                                           | `True`                 |
| **AUTO_PLAY_GAME**       | Automatically play drop game for rewards.                                                                | `True`                 |
| **GAME_PLAY_EACH_ROUND** | Number of rounds to play for each game session.                                                          | `[2, 10]`              |
| **MIN_POINTS**           | Minimum points to play during a game session.                                                            | `400`                  |
| **MAX_POINTS**           | Maximum points to play during a game session.                                                            | `460`                  |
| **REF_ID**               | Referral link ID for user registration.                                                                  | ``                     |
| **SAVE_JS_FILES**        | Save JavaScript files for debugging or analysis (experimental).                                          | `False`                |
| **ADVANCED_ANTI_DETECTION** | Enable advanced anti-detection measures to avoid account bans.                                        | `True`                 |
| **USE_PROXY_FROM_FILE**  | Use proxies from `proxies.txt`.                                                                          | `False`                |
---

## Quick Start 📚

To install dependencies and run the bot quickly, use the provided batch file (`run.bat`) for Windows or the shell script (`run.sh`) for Linux.

### Prerequisites
Ensure you have **Python 3.10** installed.

### Obtaining API Keys
1. Go to [my.telegram.org](https://my.telegram.org) and log in.
2. Under **API development tools**, create a new application to get your `API_ID` and `API_HASH`, and add these to your `.env` file.

---

## Installation

### Clone the Repository
```shell
git clone https://github.com/hasan1818666891/Tomarket-BOT
cd Tomarket-BOT
```

Then you can do automatic installation by typing:

Windows:
```shell
run.bat
```

Linux:
```shell
run.sh
```

# Linux manual installation
```shell
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
cp .env-example .env
nano .env  # Here you must specify your API_ID and API_HASH, the rest is taken by default
python3 main.py
```

You can also use arguments for quick start, for example:
```shell
~/Tomarket-BOT >>> python3 main.py --action (1/2)
# Or
~/Tomarket-BOT >>> python3 main.py -a (1/2)

# 1 - Run clicker
# 2 - Creates a session
```

# Windows manual installation
```shell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env-example .env
# Here you must specify your API_ID and API_HASH, the rest is taken by default
python main.py
```

You can also use arguments for quick start, for example:
```shell
~/Tomarket-BOT >>> python main.py --action (1/2)
# Or
~/Tomarket-BOT >>> python main.py -a (1/2)

# 1 - Run clicker
# 2 - Creates a session
```
## Extra help
if you are facing any problem while installing `tonsdk` try this. it should work:
```shell
pkg install clang libffi openssl libsodium
SODIUM_INSTALL=system pip install pynacl
```
## Usage
1. **First Launch**: Create a session with the `--action 2` option. This will create a `sessions` folder for storing all accounts and an `accounts.json` configuration file.
2. **Existing Sessions**: If you already have sessions, add them to the `sessions` folder and run the bot with the clicker mode.

If `AUTO_ADD_WALLET` is enabled, TON wallets are automatically added to accounts, and wallet credentials (seed phrase, private key, public key) are backed up in `wallets.json`.

### Example of `wallets.json`
```json
{
    "xxxxxxxx": { 
        "wallet": {
            "mnemonic": "total feature answer mystery puzzle loyal spatial organ total feature answer mystery puzzle loyal spatial organ",
            "wallet_address": "UQC6N66gCoOJEXpvTyp4DdODbK4GvC9QNXw30qxxxxxxxxxx",
            "private_key": "xxxxxxxxxxx8b9db73b982021ee9e98f1bd8696b000ea87c95a2a7e98de1197194c7da2f961b10d5a8228efe55b4e8859ab7791xxxxxxxxxxxxxxx",
            "public_key": "e98de1197194c7da2f961b10d5a8228efe55b4e8859ab7791xxxxxxxxxxxxxxx"
        },
        "session_name": "example.session",
        "username": "telegram_username"
    }
}
```
### Example of `accounts.json`
```json
[
  {
    "session_name": "name_example",
    "user_agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.165 Mobile Safari/537.36",
    "proxy": "type://user:pass:ip:port"  // "proxy": "" if no proxy
  }
]
```

### Contacts

Unavailable
