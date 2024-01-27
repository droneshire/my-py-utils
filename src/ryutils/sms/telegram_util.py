import json
import os
import typing as T

import telegram

from ryutils import log
from ryutils.async_utils import force_sync


class TelegramUtil:
    def __init__(self, token: str, cache_path: str, dry_run: bool = False) -> None:
        self.bot = telegram.Bot(token=token)
        self.dry_run = dry_run
        self.chat_id_cache = cache_path

    def check_token(self) -> bool:
        if self.dry_run:
            log.print_normal("TelegramUtil: check_token (dry run)")
            return True

        return self._check_token()  # type: ignore[no-any-return]

    @force_sync
    async def _check_token(self) -> bool:
        async with self.bot:
            try:
                its_me = await self.bot.get_me()
                log.print_ok_arrow(f"Telegram bot is running as {its_me.username}")
                return True
            except:  # pylint: disable=bare-except
                log.print_fail("Telegram bot token is invalid!")
                return False
        return False

    def get_channel_chats(self) -> T.List[telegram.Chat]:
        if self.dry_run:
            log.print_normal("TelegramUtil: get_channel_chats (dry run)")
            return []

        return self._get_channel_chats()  # type: ignore[no-any-return]

    @force_sync
    async def _get_channel_chats(self) -> T.List[telegram.Chat]:
        chats: T.List[telegram.Chat] = []
        async with self.bot:
            updates = await self.bot.get_updates()
        for update in updates:
            if update.channel_post:
                chats.append(update.channel_post.chat)
        return chats

    def get_chat_id(self, title: str) -> T.Optional[int]:
        if self.dry_run:
            log.print_normal("TelegramUtil: get_chat_id (dry run)")
            return None

        try:
            chats: T.List[telegram.Chat] = self.get_channel_chats()
        except:  # pylint: disable=bare-except
            log.print_fail("TelegramUtil: get_chat_id: failed to get channel chats")
            return None
        for chat in chats:
            if chat.title == title:
                with open(self.chat_id_cache, "w", encoding="utf-8") as outfile:
                    json.dump({title: chat.id}, outfile)
                return int(chat.id)

        if self.chat_id_cache and os.path.exists(self.chat_id_cache):
            with open(self.chat_id_cache, "r", encoding="utf-8") as infile:
                try:
                    return int(json.load(infile).get(title, None))
                except (json.JSONDecodeError, KeyError):
                    log.print_fail("TelegramUtil: get_chat_id: failed to get chat id from cache")

        return None

    def send_message(self, chat_id: int, message: str) -> None:
        if self.dry_run:
            log.print_normal("TelegramUtil: send_message (dry run)")
            return
        self._send_message(chat_id, message)  # type: ignore[no-any-return]

    @force_sync
    async def _send_message(self, chat_id: str, message: str) -> None:
        async with self.bot:
            await self.bot.send_message(chat_id=chat_id, text=message)
