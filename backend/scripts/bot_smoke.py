#!/usr/bin/env python3
"""Smoke-check MAX bot identity + open_app keyboard shape.

Usage (from backend/ with venv):
  python scripts/bot_smoke.py
  python scripts/bot_smoke.py --invite-user 123456789
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys

from app.bot.client import max_bot
from app.bot.handlers import WELCOME
from app.core.config import settings


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--invite-user", type=int, default=None, help="MAX user_id to DM")
    parser.add_argument("--invite-chat", type=int, default=None, help="MAX chat_id to message")
    args = parser.parse_args()

    print("enabled=", settings.max_bot_enabled)
    print("mode=", settings.max_bot_mode)
    print("webapp=", settings.max_webapp_url)
    print("token=", "set" if settings.max_bot_token else "empty")

    if not settings.max_bot_token:
        print("MAX_BOT_TOKEN is empty", file=sys.stderr)
        return 1

    me = await max_bot.get_me(force=True)
    print(
        "me=",
        json.dumps(
            {
                "user_id": max_bot.bot_user_id,
                "username": max_bot.bot_username,
                "name": me.get("name") or me.get("first_name"),
                "is_bot": me.get("is_bot"),
            },
            ensure_ascii=False,
        ),
    )
    print("deeplink=", max_bot.max_deeplink())
    keyboard = max_bot.planner_keyboard()
    print("open_app=", json.dumps(keyboard[0][0], ensure_ascii=False))

    open_app = keyboard[0][0]
    if str(open_app.get("web_app") or "").startswith("http"):
        print("FAIL: open_app.web_app must be bot username, not SPA URL", file=sys.stderr)
        return 2
    if open_app.get("contact_id") is None and not open_app.get("web_app"):
        print("FAIL: open_app needs contact_id or web_app", file=sys.stderr)
        return 2
    button_types = [btn["type"] for row in keyboard for btn in row]
    if "link" in button_types:
        print("FAIL: keyboard must not duplicate open via link buttons", file=sys.stderr)
        return 2

    if args.invite_user or args.invite_chat:
        result = await max_bot.send_planner_invite(
            user_id=args.invite_user,
            chat_id=args.invite_chat,
            text=WELCOME,
        )
        print("invite_ok=", bool(result))

    await max_bot.aclose()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
