#!/usr/bin/env python3
"""Send next month's content plan to Telegram."""

from __future__ import annotations

import calendar
import html
import json
import os
import sys
from datetime import date
from pathlib import Path

import requests

PLAN_PATH = Path(__file__).resolve().parent.parent / "plan" / "content_plan.json"
TELEGRAM_API = "https://api.telegram.org"


def next_month_key(today: date) -> str:
    year = today.year + (1 if today.month == 12 else 0)
    month = 1 if today.month == 12 else today.month + 1
    return f"{year}-{month:02d}"


def should_skip_today(today: date) -> bool:
    # We schedule both 29th (every month) and 28th of February.
    # In leap years Feb 29 exists, so the 28th run would duplicate — skip it.
    return today.month == 2 and today.day == 28 and calendar.isleap(today.year)


def format_message(month_data: dict) -> str:
    title = html.escape(month_data["title"])
    lines = [f"📅 <b>Контент-план: {title}</b>", ""]
    for post in month_data["posts"]:
        d = html.escape(post["date"])
        rubric = html.escape(post["rubric"])
        theme = post.get("theme") or ""
        theme = html.escape(theme) if theme else "<i>— не назначено</i>"
        lines.append(f"<b>{d}</b> · {rubric}")
        lines.append(f"   {theme}")
        lines.append("")
    return "\n".join(lines).rstrip()


def send_telegram(token: str, chat_id: str, text: str) -> None:
    url = f"{TELEGRAM_API}/bot{token}/sendMessage"
    response = requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    if not response.ok:
        print(f"Telegram API error {response.status_code}: {response.text}", file=sys.stderr)
        response.raise_for_status()


def main() -> int:
    today = date.today()

    if should_skip_today(today):
        print(f"Skipping {today.isoformat()} (leap-year Feb 28 — Feb 29 will fire)")
        return 0

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    key = next_month_key(today)
    month_data = plan["months"].get(key)

    if not month_data:
        text = (
            f"⚠️ <b>Контент-план на {html.escape(key)} не найден</b>\n\n"
            "План закончился — пора собирать следующий цикл."
        )
        send_telegram(token, chat_id, text)
        print(f"Sent missing-plan notice for {key}")
        return 0

    text = format_message(month_data)
    send_telegram(token, chat_id, text)
    print(f"Sent plan for {key}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
