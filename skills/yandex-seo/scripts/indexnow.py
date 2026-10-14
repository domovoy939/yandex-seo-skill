#!/usr/bin/env python3
"""Отправка адресов в IndexNow (Яндекс и другие участники протокола). Только стандартная библиотека.

Запуск:
    python3 indexnow.py --host example.ru --key <ключ> --sitemap https://example.ru/sitemap.xml
    python3 indexnow.py --host example.ru --key <ключ> --url https://example.ru/ceny/ --url https://example.ru/
    python3 indexnow.py --new-key            # сгенерировать ключ

Перед отправкой положи файл https://<host>/<ключ>.txt с содержимым = ключ.
"""
import argparse
import json
import re
import secrets
import sys
import urllib.error
import urllib.request

ENDPOINTS = {'yandex': 'https://yandex.com/indexnow', 'all': 'https://api.indexnow.org/indexnow'}


def main():
    ap = argparse.ArgumentParser(description='IndexNow: сообщить поисковикам об изменённых страницах')
    ap.add_argument('--host')
    ap.add_argument('--key')
    ap.add_argument('--sitemap', help='взять адреса из sitemap.xml')
    ap.add_argument('--url', action='append', default=[], help='адрес страницы (можно несколько)')
    ap.add_argument('--engine', choices=ENDPOINTS, default='yandex', help='yandex — напрямую в Яндекс, all — общий узел')
    ap.add_argument('--new-key', action='store_true', help='сгенерировать ключ и выйти')
    a = ap.parse_args()

    if a.new_key:
        print(secrets.token_hex(16))
        return
    if not (a.host and a.key):
        ap.error('нужны --host и --key')

    urls = list(a.url)
    if a.sitemap:
        req = urllib.request.Request(a.sitemap, headers={'User-Agent': 'yandex-seo-indexnow/1.0'})
        xml = urllib.request.urlopen(req, timeout=20).read().decode('utf-8', 'replace')
        urls += re.findall(r'<loc>\s*([^<\s]+)\s*</loc>', xml)
    urls = [u for u in dict.fromkeys(urls) if a.host in u]
    if not urls:
        sys.exit('Нет адресов для отправки')

    body = json.dumps({'host': a.host, 'key': a.key, 'keyLocation': f'https://{a.host}/{a.key}.txt', 'urlList': urls[:10000]}).encode()
    req = urllib.request.Request(ENDPOINTS[a.engine], body, {'Content-Type': 'application/json; charset=utf-8'})
    try:
        r = urllib.request.urlopen(req, timeout=20)
        print(f'IndexNow ({a.engine}): {r.status}, отправлено адресов: {len(urls)}')
    except urllib.error.HTTPError as e:
        hint = {400: 'неверный формат', 403: 'ключ не найден по keyLocation или не совпадает', 422: 'адреса не принадлежат host', 429: 'слишком часто'}.get(e.code, '')
        sys.exit(f'IndexNow ответил {e.code} {hint}')


if __name__ == '__main__':
    main()
