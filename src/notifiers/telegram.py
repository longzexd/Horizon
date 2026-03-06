"""Telegram notifier."""

import os

import httpx

from ..models import TelegramNotificationConfig

TELEGRAM_MAX_MESSAGE_CHARS = 3900


class TelegramNotifier:
    """Send generated summaries to Telegram chats."""

    def __init__(self, config: TelegramNotificationConfig):
        self.config = config

    def is_enabled(self) -> bool:
        return self.config.enabled

    def _credentials(self) -> tuple[str, str]:
        token = (os.getenv(self.config.bot_token_env) or "").strip()
        chat_id = (os.getenv(self.config.chat_id_env) or "").strip()
        if not token:
            raise ValueError(
                f"Missing Telegram bot token env: {self.config.bot_token_env}"
            )
        if not chat_id:
            raise ValueError(
                f"Missing Telegram chat id env: {self.config.chat_id_env}"
            )
        return token, chat_id

    async def send_summary(
        self,
        summary_text: str,
        date: str,
        language: str,
        selected_count: int,
        fetched_count: int,
    ) -> None:
        """Send summary as plain text messages (auto-split if too long)."""
        token, chat_id = self._credentials()
        endpoint = f"https://api.telegram.org/bot{token}/sendMessage"
        header = (
            f"Horizon Daily {date} ({language.upper()})\n"
            f"Selected: {selected_count} / {fetched_count}"
        )
        text = (summary_text or "").strip()
        full_text = f"{header}\n\n{text}" if text else header

        async with httpx.AsyncClient(timeout=30.0) as client:
            for chunk in self._split_text(full_text, TELEGRAM_MAX_MESSAGE_CHARS):
                payload = {
                    "chat_id": chat_id,
                    "text": chunk,
                    "disable_notification": self.config.disable_notification,
                }
                resp = await client.post(endpoint, json=payload)
                resp.raise_for_status()

    @staticmethod
    def _split_text(text: str, max_len: int) -> list[str]:
        """Split long text into Telegram-safe chunks."""
        if len(text) <= max_len:
            return [text]

        chunks = []
        remaining = text
        while len(remaining) > max_len:
            split_at = remaining.rfind("\n", 0, max_len)
            if split_at < max_len // 2:
                split_at = max_len
            chunks.append(remaining[:split_at].strip())
            remaining = remaining[split_at:].lstrip("\n")
        if remaining.strip():
            chunks.append(remaining.strip())
        return chunks
