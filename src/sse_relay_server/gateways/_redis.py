import json
import httpx
from typing import AsyncGenerator

import redis
import redis.asyncio as async_redis
from loguru import logger
from sse_starlette import ServerSentEvent
from ..config import get_last_messages_endpoint_url


class RedisGateway:
    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url

    async def listen(self, channel: str, last_id: str|None) -> AsyncGenerator[ServerSentEvent, None]:
        r = async_redis.from_url(self.redis_url)

        if last_id:
            last_messages = httpx.get(
                f"{get_last_messages_endpoint_url()}/{channel}/{last_id}"
            )
            for message in last_messages:
                payload = json.loads(message)
                logger.debug(f"Received from {channel}: {payload}")
                yield ServerSentEvent(**payload)

        async with r.pubsub() as pubsub:
            await pubsub.subscribe(channel)
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True)
                if message is not None:
                    payload = json.loads(message["data"].decode())
                    logger.debug(f"Received from {channel}: {payload}")
                    yield ServerSentEvent(**payload)

    def notify(self, channel: str, sse_payload: dict) -> None:
        r = redis.from_url(self.redis_url)
        r.publish(channel=channel, message=json.dumps(sse_payload))
