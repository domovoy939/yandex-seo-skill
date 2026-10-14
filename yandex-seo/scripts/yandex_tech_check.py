#!/usr/bin/env python3
"""Техническая проверка сайта под Яндекс. Только стандартная библиотека, Python 3.9+.

Запуск:
    python3 yandex_tech_check.py https://example.ru
    python3 yandex_tech_check.py https://example.ru --json > report.json
    python3 yandex_tech_check.py https://example.ru --indexnow-key <ключ>

Что проверяет: зеркала и цепочки редиректов, честную 404, robots.txt (Clean-param, Host, доступ Яндекса),
sitemap и выборку адресов из него, мета-теги и разметку главной, контент до выполнения JS,
подтверждение Вебмастера, Метрику, сигналы коммерческих факторов, ключ IndexNow.
"""
import argparse
import json
import re
import secrets
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

UA = 'Mozilla/5.0 (compatible; yandex-seo-check/1.0; +https://github.com/shatinadesign/yandex-seo-skill)'
TIMEOUT = 20
OK, WARN, BAD, INFO = 'ok', 'warn', 'bad', 'info'
ICON = {OK: '✅', WARN: '⚠️ ', BAD: '❌', INFO: 'ℹ️ '}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def fetch(url, follow=True, limit=600_000):
    """Возвращает (status, final_url, headers, body_text, chain). chain — список (status, url) по прыжкам."""
    opener = urllib.request.build_opener(NoRedirect, urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    chain, cur = [], url
    for _ in range(10):
        req = urllib.request.Request(cur, headers={'User-Agent': UA, 'Accept-Language': 'ru,en;q=0.8'})
        try:
            r = opener.open(req, timeout=TIMEOUT)
            body = r.read(limit).decode(r.headers.get_content_charset() or 'utf-8', 'replace')
            chain.append((r.status, cur))
            return r.status, cur, dict(r.headers), body, chain
        except urllib.error.HTTPError as e:
            loc = e.headers.get('Location')
            chain.append((e.code, cur))
            if e.code in (301, 302, 303, 307, 308) and loc and follow:
                cur = urllib.parse.urljoin(cur, loc)
                continue
            body = ''
            try:
                body = e.read(limit).decode('utf-8', 'replace')
            except Exception:
                pass
            return e.code, cur, dict(e.headers or {}), body, chain
        except Exception as e:  # сеть, SSL, таймаут
            chain.append((0, cur))
            return 0, cur, {}, str(e), chain
    return chain[-1][0], cur, {}, '', chain


class Page(HTMLParser):
    """Достаём из HTML всё, что нужно для проверки, без сторонних библиотек."""
    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base = base
        self.title, self.in_title = '', False
        self.meta, self.links, self.canonical = {}, [], None
        self.h1, self.in_h1, self.h1_text = 0, False, []
        self.jsonld, self.in_ld, self.ld_buf = [], False, ''
        self.scripts_src, self.text, self.skip = [], [], 0
        self.lang = ''

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or '') for k, v in attrs}
        if tag == 'html':
            self.lang = a.get('lang', '')
        elif tag == 'title':
            self.in_title = True
        elif tag == 'meta':
            key = (a.get('name') or a.get('property') or '').lower()
            if key:
                self.meta[key] = a.get('content', '')
        elif tag == 'link' and 'canonical' in a.get('rel', '').lower():
            self.canonical = urllib.parse.urljoin(self.base, a.get('href', ''))
        elif tag == 'a' and a.get('href'):
            self.links.append(a['href'])
        elif tag == 'h1':
            self.h1 += 1
            self.in_h1 = True
        elif tag == 'script':
            if a.get('type', '').lower() == 'application/ld+json':
                self.in_ld, self.ld_buf = True, ''
            elif a.get('src'):
                self.scripts_src.append(a['src'])
            self.skip += 1
        elif tag in ('style', 'noscript'):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
        elif tag == 'h1':
            self.in_h1 = False
        elif tag == 'script':
            if self.in_ld:
                self.jsonld.append(self.ld_buf)
                self.in_ld = False
            self.skip = max(0, self.skip - 1)
        elif tag in ('style', 'noscript'):
            self.skip = max(0, self.skip - 1)

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.in_ld:
            self.ld_buf += data
        if self.in_h1:
            self.h1_text.append(data.strip())
        if not self.skip and data.strip():
            self.text.append(data.strip())


def ld_types(blocks):
    types = set()

    def walk(o):
        if isinstance(o, dict):
            t = o.get('@type')
            if isinstance(t, list):
                types.update(map(str, t))
            elif t:
                types.add(str(t))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    for b in blocks:
        try:
            walk(json.loads(b))
        except Exception:
            types.add('(ошибка JSON)')
    return sorted(types)


class Report:
    def __init__(self):
        self.items = []

    def add(self, group, level, text, fix=''):
        self.items.append({'group': group, 'level': level, 'text': text, 'fix': fix})

    def print(self, url):
        print(f'\nПроверка под Яндекс: {url}\n')
        group = None
        for it in self.items:
            if it['group'] != group:
                group = it['group']
                print(f'\n■ {group}')
            print(f"  {ICON[it['level']]} {it['text']}")
            if it['fix'] and it['level'] in (WARN, BAD):
                print(f"      → {it['fix']}")
        bad = sum(1 for i in self.items if i['level'] == BAD)
        warn = sum(1 for i in self.items if i['level'] == WARN)
        print(f'\nИтого: критичных {bad}, предупреждений {warn}. Это техника — семантику, выдачу и кабинеты смотри по шагам скила.\n')


def check(url, indexnow_key=None):
    R = Report()
    p = urllib.parse.urlparse(url if '://' in url else 'https://' + url)
    host = p.hostname
    bare = host[4:] if host.startswith('www.') else host
    main = f'{p.scheme}://{host}/'

    # ── Зеркала и редиректы
    G = 'Зеркала и редиректы'
    st, final, hdr, body, chain = fetch(main)
    if st != 200:
        R.add(G, BAD, f'Главная {main} отдаёт {st or "ошибку соединения"}', 'главная должна отдавать 200')
        return R, {}
    final_host = urllib.parse.urlparse(final).hostname
    moved = final_host.removeprefix('www.') if hasattr(str, 'removeprefix') else re.sub(r'^www\.', '', final_host)
    if moved != bare:
        R.add(G, INFO, f'Домен переадресует на {final_host} — это переезд. Дальше проверяется новый сайт; '
                       f'в Вебмастере старого домена должен быть оформлен «Переезд сайта»')
        hops = [f"{s} {u}" for s, u in chain]
        R.add(G, OK if len(chain) == 2 and chain[0][0] == 301 else WARN, f'Старая главная: {" → ".join(hops)}',
              'старая главная — один 301 на новую главную')
    else:
        R.add(G, OK if len(chain) == 1 else WARN, f'Главная: {" → ".join(f"{s} {u}" for s, u in chain)}',
              'главное зеркало должно открываться без редиректов')
    variants = {f'http://{bare}/', f'http://www.{bare}/', f'https://www.{bare}/', f'https://{bare}/'} - {final}
    for v in sorted(variants):
        s, f, _, _, ch = fetch(v)
        hops = len(ch) - 1
        if s == 0:
            R.add(G, INFO, f'{v} — не открывается (нет DNS или сертификата)', '')
        elif f.rstrip('/') == final.rstrip('/') and s == 200:
            codes = [c for c, _ in ch[:-1]]
            if all(c == 301 for c in codes) and hops == 1:
                R.add(G, OK, f'{v} → 301 → главное зеркало')
            else:
                R.add(G, WARN, f'{v} → {" → ".join(str(c) for c, _ in ch)} ({hops} прыжка)',
                      'сделай один 301 сразу на главное зеркало; 302 для зеркал не подходит')
        else:
            R.add(G, BAD, f'{v} отдаёт {s} на {f} — второе зеркало или ошибка', 'настрой 301 на главное зеркало')

    # ── 404
    G = 'Ответы сервера'
    probe = urllib.parse.urljoin(final, f'yandex-seo-check-{secrets.token_hex(4)}/')
    s404, _, _, b404, _ = fetch(probe, follow=False)
    if s404 in (404, 410):
        R.add(G, OK, f'Несуществующий адрес отдаёт {s404}')
    elif s404 == 200:
        same = b404[:3000] == body[:3000]
        R.add(G, BAD, 'Несуществующий адрес отдаёт 200' + (' и содержимое главной (мягкая 404)' if same else ''),
              'отдавай 404 со своей страницей и noindex; для SPA — index только на известные маршруты')
    else:
        R.add(G, WARN, f'Несуществующий адрес отдаёт {s404}', 'ожидается 404')
    cc = hdr.get('Cache-Control', '')
    if cc:
        R.add(G, INFO, f'Cache-Control главной: {cc}')
    if 'max-age' in cc and not re.search(r'max-age=0\b', cc) and 'no-cache' not in cc:
        R.add(G, WARN, 'HTML главной кэшируется — после деплоя посетители и робот могут видеть старую версию', 'для HTML: Cache-Control: no-cache')

    # ── robots.txt
    G = 'robots.txt'
    rs, _, _, robots, _ = fetch(urllib.parse.urljoin(final, '/robots.txt'))
    sitemaps = []
    if rs != 200:
        R.add(G, BAD, f'robots.txt отдаёт {rs}', 'положи robots.txt в корень')
    else:
        low = robots.lower()
        sitemaps = re.findall(r'(?im)^\s*sitemap:\s*(\S+)', robots)
        R.add(G, OK if sitemaps else WARN, f'Sitemap в robots.txt: {", ".join(sitemaps) or "нет"}', 'добавь строку Sitemap: https://…/sitemap.xml')
        if re.search(r'(?im)^\s*host:', robots):
            R.add(G, WARN, 'Есть директива Host — Яндекс её не учитывает с 2018 года', 'убери Host, главное зеркало задаётся 301')
        if 'clean-param' in low:
            R.add(G, OK, 'Clean-param задан — служебные параметры склеиваются')
        else:
            R.add(G, WARN, 'Нет Clean-param — адреса с utm_* могут попадать в индекс как дубли',
                  'Clean-param: utm_source&utm_medium&utm_campaign&utm_content&utm_term')
        blocks = re.split(r'(?im)^\s*user-agent:', robots)
        for blk in blocks[1:]:
            agent = blk.strip().splitlines()[0].strip().lower() if blk.strip() else ''
            if agent in ('*', 'yandex') and re.search(r'(?im)^\s*disallow:\s*/\s*$', blk):
                R.add(G, BAD, f'User-agent: {agent} — Disallow: / закрывает весь сайт', 'открой сайт для индексации')
        if re.search(r'(?im)^\s*disallow:.*\.(css|js)\b', robots):
            R.add(G, WARN, 'Закрыты CSS или JS — роботу сложнее отрендерить страницу', 'не закрывай стили и скрипты')

    # ── Главная: мета и разметка
    G = 'Главная: мета и разметка'
    pg = Page(final)
    try:
        pg.feed(body)
    except Exception:
        pass
    t = ' '.join(pg.title.split())
    R.add(G, OK if 10 <= len(t) <= 65 else WARN, f'title ({len(t)} симв.): {t[:90]}', 'длина 10–65 символов, основной запрос + город/бренд')
    d = pg.meta.get('description', '')
    R.add(G, OK if 50 <= len(d) <= 160 else WARN, f'description ({len(d)} симв.)', 'длина 50–160, оффер и цена «от»')
    R.add(G, OK if pg.h1 == 1 else WARN, f'h1 на странице: {pg.h1}', 'ровно один h1')
    if pg.canonical:
        R.add(G, OK if pg.canonical.rstrip('/') == final.rstrip('/') else WARN, f'canonical: {pg.canonical}', 'canonical главной — на саму главную')
    else:
        R.add(G, WARN, 'Нет canonical', 'добавь <link rel="canonical">')
    R.add(G, OK if 'viewport' in pg.meta else BAD, 'meta viewport ' + ('есть' if 'viewport' in pg.meta else 'нет'), 'без viewport нет мобильной версии')
    robots_meta = pg.meta.get('robots', '') + pg.meta.get('yandex', '')
    if 'noindex' in robots_meta.lower():
        R.add(G, BAD, f'meta robots: {robots_meta} — главная закрыта от индексации', 'убери noindex')
    R.add(G, OK if pg.lang.lower().startswith('ru') else INFO, f'lang: {pg.lang or "не задан"}')
    types = ld_types(pg.jsonld)
    R.add(G, OK if types else WARN, f'Schema.org: {", ".join(types) or "нет"}', 'Organization/LocalBusiness, Service, BreadcrumbList, FAQPage')
    R.add(G, OK if pg.meta.get('og:image') else WARN, 'og:image ' + ('есть' if pg.meta.get('og:image') else 'нет'), 'картинка 1200×630 для превью в мессенджерах')
    R.add(G, OK if 'yandex-verification' in pg.meta else INFO,
          'Подтверждение Вебмастера meta-тегом ' + ('есть' if 'yandex-verification' in pg.meta else 'не найдено (возможно, через DNS или файл)'))
    metrika = re.search(r'mc\.yandex\.ru/metrika|ym\(\s*\d+', body)
    R.add(G, OK if metrika else INFO, 'Метрика в HTML ' + ('найдена' if metrika else 'не найдена (может подключаться после согласия на cookie)'))

    # ── Контент до выполнения JS (важно для SPA)
    G = 'Контент без JavaScript'
    text_len = len(' '.join(pg.text))
    internal = {urllib.parse.urljoin(final, h).split('#')[0] for h in pg.links
                if urllib.parse.urlparse(urllib.parse.urljoin(final, h)).hostname in (host, bare, 'www.' + bare)}
    internal.discard(final)
    R.add(G, OK if text_len > 1500 else WARN, f'Текста в исходном HTML: ~{text_len} символов',
          'если сайт на React/Vue — пререндер или SSR, чтобы текст был в HTML без JS')
    R.add(G, OK if len(internal) >= 5 else WARN, f'Внутренних ссылок в исходном HTML: {len(internal)}',
          'разделы должны быть настоящими <a href>, а не кнопками с обработчиком')
    roots = re.findall(r'<div id="(root|app|__next|__nuxt)"[^>]*>\s*</div>', body)
    if roots:
        R.add(G, BAD, f'Пустой контейнер приложения #{roots[0]} — без JS страница пустая', 'пререндер / SSR')

    # ── Коммерческие факторы (сигналы на главной)
    G = 'Коммерческие сигналы на главной'
    raw = ' '.join(pg.text)
    hrefs = ' '.join(pg.links).lower()
    sig = [
        ('Телефон', bool(re.search(r'(\+7|8)[\s(-]*\d{3}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}', raw)) or 'tel:' in hrefs, 'телефон в шапке, ссылкой tel:'),
        ('Мессенджеры', bool(re.search(r't\.me/|wa\.me/|vk\.com/|max\.ru/', hrefs)), 'Telegram, WhatsApp, VK, MAX'),
        ('Цены', bool(re.search(r'\d[\d\s]*\s?(₽|руб)', raw)), 'цены или «от» на главной и в услугах'),
        ('Реквизиты (ИНН/ОГРН)', bool(re.search(r'ИНН|ОГРН', raw)), 'реквизиты в подвале'),
        ('Почта', bool(re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', raw)) or 'mailto:' in hrefs, 'почта на сайте'),
        ('Политика конфиденциальности', bool(re.search(r'политик|privacy|konfiden|politika', hrefs + raw.lower())), 'ссылка на политику 152-ФЗ'),
        ('Страница контактов', bool(re.search(r'contact|kontakt|контакт', hrefs)), 'отдельная страница «Контакты»'),
    ]
    for name, ok, fix in sig:
        R.add(G, OK if ok else WARN, name, fix)

    # ── sitemap
    G = 'sitemap.xml'
    sm_url = sitemaps[0] if sitemaps else urllib.parse.urljoin(final, '/sitemap.xml')
    ss, _, _, sm, _ = fetch(sm_url)
    if ss != 200:
        R.add(G, BAD, f'{sm_url} отдаёт {ss}', 'создай sitemap.xml и добавь в Вебмастер')
    else:
        locs = re.findall(r'<loc>\s*([^<\s]+)\s*</loc>', sm)
        is_index = '<sitemapindex' in sm
        R.add(G, OK if locs else WARN, f'{"Индекс sitemap" if is_index else "Адресов"}: {len(locs)}')
        lastmods = set(re.findall(r'<lastmod>([^<]+)</lastmod>', sm))
        if len(locs) > 5 and len(lastmods) == 1:
            R.add(G, INFO, f'У всех адресов одинаковый lastmod ({next(iter(lastmods))})', 'ставь реальную дату изменения страницы')
        if not is_index:
            bad = []
            for u in locs[:20]:
                s, f, _, b, ch = fetch(u)
                if s != 200 or len(ch) > 1:
                    bad.append(f'{u} → {s}{" (редирект)" if len(ch) > 1 else ""}')
                    continue
                pp = Page(f)
                try:
                    pp.feed(b)
                except Exception:
                    pass
                if pp.canonical and pp.canonical.rstrip('/') != u.rstrip('/'):
                    bad.append(f'{u} → canonical на {pp.canonical}')
                if 'noindex' in (pp.meta.get('robots', '') + pp.meta.get('yandex', '')).lower():
                    bad.append(f'{u} → noindex')
            if bad:
                R.add(G, WARN, f'Проблемы у {len(bad)} из {min(20, len(locs))} проверенных адресов: ' + '; '.join(bad[:5]),
                      'в sitemap только канонические страницы с ответом 200')
            else:
                R.add(G, OK, f'Проверено {min(20, len(locs))} адресов: все 200, canonical на себя, без noindex')

    # ── IndexNow
    if indexnow_key:
        G = 'IndexNow'
        ks, _, _, kb, _ = fetch(urllib.parse.urljoin(final, f'/{indexnow_key}.txt'))
        R.add(G, OK if ks == 200 and kb.strip() == indexnow_key else BAD,
              f'Файл ключа /{indexnow_key}.txt: {ks}', 'файл должен отдавать 200 и содержать ровно ключ')

    data = {'url': final, 'items': R.items}
    return R, data


def main():
    ap = argparse.ArgumentParser(description='Техническая проверка сайта под Яндекс')
    ap.add_argument('url')
    ap.add_argument('--json', action='store_true', help='вывести результат в JSON')
    ap.add_argument('--indexnow-key', help='проверить файл ключа IndexNow')
    a = ap.parse_args()
    R, data = check(a.url, a.indexnow_key)
    if a.json:
        json.dump(data or {'items': R.items}, sys.stdout, ensure_ascii=False, indent=1)
        print()
    else:
        R.print(a.url)


if __name__ == '__main__':
    main()
