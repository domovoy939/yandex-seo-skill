#!/usr/bin/env bash
# Ставит скил yandex-seo в ~/.claude/skills. Ничего не скачивает и не ставит зависимостей.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)/skills/yandex-seo"
DST="${HOME}/.claude/skills/yandex-seo"
[ -f "$SRC/SKILL.md" ] || { echo "Не нашёл $SRC/SKILL.md — запусти скрипт из папки репозитория"; exit 1; }
mkdir -p "${HOME}/.claude/skills"
rm -rf "$DST"
cp -R "$SRC" "$DST"
chmod +x "$DST/scripts/"*.py
echo "✓ yandex-seo установлен → $DST"
echo "  Попробуй в Claude Code: «Сделай SEO-аудит под Яндекс для https://example.ru»"
