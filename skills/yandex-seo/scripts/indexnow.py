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
import urllib.parse
import urllib.request
from pathlib import Path

# sitemap скачиваем тем же защищённым загрузчиком, что и проверка: только http(s), без внутренней сети
sys.path.insert(0, str(Path(__file__).resolve().parent))
from yandex_tech_check import TRUSTED, _proxy_hosts, fetch  # noqa: E402

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
    # ключ по протоколу IndexNow: 8–128 символов, латиница, цифры, дефис
    if not re.fullmatch(r'[A-Za-z0-9-]{8,128}', a.key):
        ap.error('ключ: 8–128 символов, только латиница, цифры и дефис')
    host = a.host.strip().lower()
    if not re.fullmatch(r'[a-z0-9.-]+\.[a-z0-9-]{2,}|xn--[a-z0-9.-]+', host):
        ap.error('--host — только домен, без https:// и пути, например example.ru')

    urls = list(a.url)
    if a.sitemap:
        if urllib.parse.urlsplit(a.sitemap).scheme not in ('http', 'https'):
            ap.error('--sitemap — адрес http(s)://…')
        TRUSTED.update(_proxy_hosts())
        st, _, _, xml, _ = fetch(a.sitemap, limit=20_000_000)
        if st != 200:
            sys.exit(f'sitemap не скачался: {st or xml}')
        urls += re.findall(r'<loc>\s*([^<\s]{1,2048})\s*</loc>', xml)
    # отправляем только адреса своего домена — иначе IndexNow вернёт 422, а чужие адреса слать незачем
    urls = [u for u in dict.fromkeys(urls)
            if urllib.parse.urlsplit(u).scheme in ('http', 'https') and urllib.parse.urlsplit(u).hostname in (host, 'www.' + host)]
    if not urls:
        sys.exit('Нет адресов для отправки')

    urls = urls[:10000]   # больше за один запрос протокол не принимает
    body = json.dumps({'host': host, 'key': a.key, 'keyLocation': f'https://{host}/{a.key}.txt', 'urlList': urls}).encode()
    req = urllib.request.Request(ENDPOINTS[a.engine], body, {'Content-Type': 'application/json; charset=utf-8'})
    try:
        r = urllib.request.urlopen(req, timeout=20)
        print(f'IndexNow ({a.engine}): {r.status}, отправлено адресов: {len(urls)}')
    except urllib.error.HTTPError as e:
        hint = {400: 'неверный формат', 403: 'ключ не найден по keyLocation или не совпадает', 422: 'адреса не принадлежат host', 429: 'слишком часто'}.get(e.code, '')
        sys.exit(f'IndexNow ответил {e.code} {hint}')
    except (urllib.error.URLError, OSError) as e:
        sys.exit(f'Не достучался до IndexNow: {e}')


if __name__ == '__main__':
    main()
