"""Redis-backed LLM usage memory."""

import json
import time
from typing import Protocol, cast

from redis.asyncio import Redis as AsyncRedis


class IUsageMemory(Protocol):
    """Interface for LLM token usage memory."""

    async def awrite_llm_usage(self, cluster_id: str, data: dict, ttl: int = 0) -> str:
        """Write LLM usage data to Redis. Return the key."""

    async def alist_llm_usage_records(self, cluster_id: str, ttl: int) -> list[dict]:
        """List the LLM usage records written within the last ttl seconds."""


def _get_llm_usage_key_prefix(cluster_id: str) -> str:
    """Get the Redis key prefix for LLM usage data."""
    return f"llm_usage_{cluster_id}"


def _make_llm_usage_key(cluster_id: str) -> str:
    """Create a Redis key for storing LLM usage data."""
    return f"{_get_llm_usage_key_prefix(cluster_id)}_{time.time()}"


def _get_llm_usage_index_key(cluster_id: str) -> str:
    """Get the Redis key of the sorted set that indexes the LLM usage records of a cluster.

    The members are the record keys, the scores the times they were written. The key does
    not start with the record prefix (`llm_usage_`), so it is not matched as a record.
    """
    return f"llm_usage:index:{cluster_id}"


class AsyncRedisSaver:
    """Redis-backed LLM usage tracker."""

    conn: AsyncRedis

    def __init__(self, conn: AsyncRedis):
        self.conn = conn

    async def awrite_llm_usage(self, cluster_id: str, data: dict, ttl: int = 0) -> str:
        """Write LLM usage data to Redis and add it to the index of the cluster. Return the key."""
        key = _make_llm_usage_key(cluster_id)
        index_key = _get_llm_usage_index_key(cluster_id)
        async with self.conn.pipeline(transaction=True) as pipe:
            if ttl > 0:
                pipe.set(key, json.dumps(data), ex=ttl)
            else:
                pipe.set(key, json.dumps(data))
            pipe.zadd(index_key, {key: time.time()})
            if ttl > 0:
                # the index lives as long as the latest record.
                pipe.expire(index_key, ttl)
            await pipe.execute()
        return key

    async def alist_llm_usage_records(self, cluster_id: str, ttl: int) -> list[dict]:
        """List the LLM usage records of the cluster written within the last ttl seconds.

        Reads the index of the cluster instead of scanning the key space.
        Older entries are removed from the index.
        """
        index_key = _get_llm_usage_index_key(cluster_id)
        oldest = time.time() - ttl
        await self.conn.zremrangebyscore(index_key, "-inf", oldest)
        # without scores, the result is the list of members.
        keys = cast(list[bytes | str], await self.conn.zrangebyscore(index_key, f"({oldest}", "+inf"))
        if not keys:
            return []
        records = await self.conn.mget(keys)
        return [json.loads(record) for record in records if record]
