def get_headers() -> dict:
    return {
        'Accept': "application/json, text/plain, */*",
        'Accept-Encoding': "gzip, deflate, br, zstd",
        'Content-Type': "application/json",
        'sec-ch-ua-platform': "\"Android\"",
        'sec-ch-ua-mobile': "?1",
        'origin': "https://mini-app.tomarket.ai",
        'x-requested-with': "org.telegram.messenger",
        'sec-fetch-site': "same-site",
        'sec-fetch-mode': "cors",
        'sec-fetch-dest': "empty",
        'referer': "https://mini-app.tomarket.ai/",
        'accept-language': "en,en-US;q=0.9,bn-BD;q=0.8,bn;q=0.7",
        'priority': "u=1, i"
    }


def options_headers(
    method: str,
    kwarg: dict = None
) -> dict:
    if kwarg is None:
        kwarg = {}

    excluded_keys = {'sec-ch-ua', 'sec-ch-ua-mobile',
                     'sec-ch-ua-platform', 'content-type', 'accept', 'authorization'}
    kwarg = {k: v for k, v in kwarg.items() if k.lower() not in excluded_keys}

    return {
        'access-control-request-method': method.upper(),
        'access-control-request-headers': "authorization,content-type" if method.upper() == "GET" else "content-type",
        **kwarg
    }
