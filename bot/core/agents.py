import re
import ua_generator
from ua_generator.options import Options
from ua_generator.data.version import VersionRange

# Mapping of Android versions to SDK versions
ANDROID_SDK_MAPPING = {
    "14": 34,
    "13": 33,
    "12": 31,
    "11": 30,
    "10": 29,
    "9": 28,
    "8": 26
}

# Default values in case extraction fails
DEFAULT_ANDROID_VERSION = "Android 9"
DEFAULT_DEVICE_MODEL = "SM-G892A"
DEFAULT_CHROME_VERSION = "118.0.5993.156"
DEFAULT_SDK_VERSION = 28

# Default app version and name
DEFAULT_APP_VERSION = "11.5.4"
DEFAULT_APP_NAME = "Telegram-Android"

def generate_random_user_agent(device_type='android', browser_type='chrome') -> str:
    chrome_version_range = VersionRange(min_version=117, max_version=131)
    options = Options(version_ranges={'chrome': chrome_version_range})
    ua = ua_generator.generate(platform=device_type, browser=browser_type, options=options)
    normal_user_agent = ua.text
    app_user_agent = generate_app_user_agent(normal_user_agent)
    return app_user_agent

def extract_chrome_version(user_agent) -> str:
    # Extract the Chrome version from the user agent
    chrome_version_match = re.search(r"Chrome/([\d\.]+)", user_agent)
    if chrome_version_match:
        return chrome_version_match.group(1)
    else:
        return DEFAULT_CHROME_VERSION  # Use default if Chrome version is not found

def generate_app_user_agent(normal_user_agent, app_version=DEFAULT_APP_VERSION, app_name=DEFAULT_APP_NAME) -> str:
    device_info_match = re.search(r"\(([^)]+)\)", normal_user_agent)
    
    if device_info_match:
        device_info = device_info_match.group(1)
        parts = device_info.split("; ")

        android_version = parts[1].split(" ")[1] if len(parts) > 1 else DEFAULT_ANDROID_VERSION
        device_model = parts[2].split(" ")[0] if len(parts) > 2 else DEFAULT_DEVICE_MODEL

        # Special handling for Samsung devices
        if device_model.startswith("SM-"):
            device_model = "Samsung " + device_model

        android_version_major = android_version.split(".")[0]
        sdk_version = ANDROID_SDK_MAPPING.get(android_version_major, DEFAULT_SDK_VERSION)

        chrome_version = extract_chrome_version(normal_user_agent)

        # Build the app user agent
        app_user_agent = (
            f"Mozilla/5.0 (Linux; Android {android_version}; K) AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{chrome_version} Mobile Safari/537.36 {app_name}/{app_version} "
            f"({device_model}; Android {android_version}; SDK {sdk_version}; AVERAGE)"
        )
        return app_user_agent
    else:
        return "Mozilla/5.0 (Linux; Android 9; Samsung SM-G892A) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.156 Mobile Safari/537.36 Telegram-Android/11.3.4 (Samsung SM-G892A; Android 9; SDK 28; AVERAGE)"
