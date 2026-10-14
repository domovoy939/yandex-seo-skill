# yandex-seo — SEO под Яндекс для Claude Code

**Первый скил для агентов, который знает Яндекс.** Популярные SEO-скилы для Claude Code работают под Google и нейропоисковики — Вордстата, Вебмастера, коммерческих факторов и Яндекс Карт там нет. А в России большая часть поиска — это Яндекс.

Этот скил — порядок работы, который мы прошли на живом запуске сайта студии: от технической проверки и семантики до Вебмастера, IndexNow и локальной выдачи.

## Что умеет

| Шаг | Что делает |
|---|---|
| **Техника** | Скрипт без зависимостей проверяет зеркала и цепочки редиректов, честную 404, robots.txt (Clean-param, устаревший Host), sitemap и выборку адресов из него, мета-теги, Schema.org, текст и ссылки до выполнения JS (боль React/Vue-сайтов), Метрику, подтверждение Вебмастера, коммерческие сигналы, ключ IndexNow |
| **Вордстат** | Операторы, регионы и главное — **интент**: кто ищет, заказчик или покупатель. «Сайт ЖК» — 127 000 показов, но это покупатели квартир, а не застройщики |
| **Выдача** | Как снимать топ без рекламы в нужном регионе, колдунщики, что из выдачи следует для типа страницы |
| **Коммерческие факторы** | Чек-лист: реквизиты, цены, способы связи, доверие, оформление |
| **Вебмастер** | Подтверждение, sitemap, регион, переезд домена, переобход, ИКС, Метрика |
| **Локальная выдача** | Яндекс Бизнес без домашнего адреса, Карты, 2ГИС, агрегаторы |
| **Закон** | 152-ФЗ, cookie и Метрика после согласия, трансграничная передача, реклама |
| **Агент в браузере** | Готовые задания для Claude в Chrome: Вордстат, выдача, Вебмастер |

На выходе — план P0/P1/P2: что именно сделать в коде или кабинете и как проверить.

## Установка

```bash
git clone https://github.com/<user>/yandex-seo-skill.git
cd yandex-seo-skill && ./install.sh
```

Или вручную: скопируй папку `yandex-seo` в `~/.claude/skills/`.

Скрипты работают на Python 3.9+ и стандартной библиотеке — ничего ставить не нужно.

## Использование

В Claude Code:

```
Сделай SEO-аудит под Яндекс для https://example.ru
```
```
Собери семантику под Яндекс для студии веб-дизайна в Самаре
```

Отдельно скрипты:

```bash
python3 yandex-seo/scripts/yandex_tech_check.py https://example.ru
python3 yandex-seo/scripts/indexnow.py --new-key
python3 yandex-seo/scripts/indexnow.py --host example.ru --key <ключ> --sitemap https://example.ru/sitemap.xml
```

Пример вывода проверки:

```
■ Зеркала и редиректы
  ✅ http://example.ru/ → 301 → главное зеркало
  ⚠️  http://www.example.ru/ → 301 → 301 → 200 (2 прыжка)
      → сделай один 301 сразу на главное зеркало
■ Ответы сервера
  ❌ Несуществующий адрес отдаёт 200 и содержимое главной (мягкая 404)
      → отдавай 404 со своей страницей и noindex
■ Контент без JavaScript
  ⚠️  Внутренних ссылок в исходном HTML: 2
      → разделы должны быть настоящими <a href>, а не кнопками
```

## Принципы

- Частотность — только из Вордстата, с периодом и регионом. Нет данных — «нет данных».
- Капчи за пользователя не проходим, защиту сервисов не обходим.
- Никаких накруток, фейковых отзывов и обещаний «топ-1 за месяц».
- Ничего не публикуем от имени бизнеса без явного «да» владельца.

## Вместе с другими скилами

Скил закрывает Яндекс. Для Google и нейропоисковиков хорошо дополняют:
[claude-seo](https://github.com/AgriciDaniel/claude-seo), [geo-seo-claude](https://github.com/zubair-trabzada/geo-seo-claude), [marketingskills](https://github.com/coreyhaines31/marketingskills).

## Авторы

Сделано в [Шатиной студии](https://shatinadesign.ru) — сайты под ключ на Tilda и на коде. Нашли ошибку или знаете фишку Яндекса, которой тут нет, — открывайте issue или PR.

---

## English

**yandex-seo** is a Claude Code skill for SEO in Yandex, the dominant search engine in Russia. Most agent SEO skills target Google and AI search only; this one covers Yandex Wordstat (keyword volumes and intent), Yandex SERP analysis, commercial ranking factors, Yandex Webmaster (verification, site move, region, recrawl), IndexNow, Yandex Business/Maps for local search and Russian legal requirements (152-FZ, cookie consent). Includes a dependency-free Python tech checker and IndexNow sender, plus ready-made tasks for browser agents. Content is in Russian.

## Лицензия

MIT
