from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int
    API_HASH: str

    USE_RANDOM_DELAY_IN_RUN: bool = True
    START_DELAY: list[int] = [30, 60]

    AUTO_FARMING: bool = True
    AUTO_TASK: bool = True

    AUTO_ADD_WALLET: bool = False

    AUTO_SOLVE_PUZZLE: bool = True

    AUTO_RANK_UPGRADE: bool = True

    AUTO_SPIN: bool = True

    AIRDROP_SEASON: str = "One"

    AUTO_SWAP_TOMATO_TO_STAR: bool = False
    AUTO_CLAIM_WEEKLY_AIRDROP: bool = True
    
    PARTICIPATE_IN_FARMINGPOOL: bool = True
    STAKE_TOMA_IN_LAUNCHPOOL: bool = False
    STAKE_ALL_TOMA: bool = False

    AUTO_PLAY_GAME: bool = True
    GAME_PLAY_EACH_ROUND: list[int] = [2, 5]
    MIN_POINTS: int = 400
    MAX_POINTS: int = 460

    REF_ID: str = '0003b4Ov'

    DISABLED_TASKS: list[str] = [
        'medal_donate',
        'daily_donate',
        'chain_donate_free',
        'airdrop_donate_check',
        'airdrop_invite'
    ]
    TO_DO_TASK: list[str] = [
        'emoji',
        'wallet',
        'telegram',
        'youtube',
        'SOCIAL_SUBSCRIPTION'
    ]

    SAVE_JS_FILES: bool = False  # Experimental `True`
    ADVANCED_ANTI_DETECTION: bool = True
    ENABLE_SSL: bool = True
    USE_PROXY_FROM_FILE: bool = False
    GIT_UPDATE_CHECKER: bool = True


settings = Settings()
