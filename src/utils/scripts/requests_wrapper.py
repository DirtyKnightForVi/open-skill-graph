import os

import requests


def request_proxy(url, method, proxy_url=None, **kwargs):
    """ 请求代理 """
    method = method.upper()
    proxy_url = proxy_url or os.getenv("INNER_PROXY_URL")
    headers = kwargs.pop('headers', {})
    if proxy_url:
        headers['actualurl'] = url
        url = proxy_url

    return requests.request(method, url, headers=headers, **kwargs)