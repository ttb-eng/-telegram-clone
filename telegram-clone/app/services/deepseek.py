import logging

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


async def get_ai_reply(message: str) -> str | None:
    if not settings.deepseek_api_key:
        return None

    try:
        client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_api_url,
        )
        resp = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant in a Telegram-like chat app. "
                               "Keep replies concise and friendly, under 200 characters.",
                },
                {"role": "user", "content": message},
            ],
            max_tokens=200,
            timeout=30,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"DeepSeek API error: {e}")
        return None
