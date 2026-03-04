"""Telegram notifier."""

import os
from pathlib import Path

import httpx

from ..models import TelegramNotificationConfig


class TelegramNotifier:
    """Send generated summaries to Telegram chats."""

    def __init__(self, config: TelegramNotificationConfig):
        self.config = config

    def is_enabled(self) -> bool:
        return self.config.enabled

    def _credentials(self) -> tuple[str, str]:
        token = os.getenv(self.config.bot_token_env)
        chat_id = os.getenv(self.config.chat_id_env)
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
        summary_path: Path,
        date: str,
        language: str,
        selected_count: int,
        fetched_count: int,
    ) -> None:
        """Upload one summary markdown file to Telegram as a document."""
        token, chat_id = self._credentials()
        endpoint = f"https://api.telegram.org/bot{token}/sendDocument"
        caption = (
            f"Horizon Daily {date} ({language.upper()})\n"
            f"Selected: {selected_count} / {fetched_count}"
        )[:1024]

        with summary_path.open("rb") as file_obj:
            files = {
                "document": (
                    summary_path.name,
                    file_obj,
                    "text/markdown",
                )
            }
            data = {
                "chat_id": chat_id,
                "caption": caption,
                "disable_notification": str(self.config.disable_notification).lower(),
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(endpoint, data=data, files=files)
                resp.raise_for_status()
