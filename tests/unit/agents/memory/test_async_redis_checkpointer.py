import json
import time
from unittest.mock import patch

import fakeredis
import pytest
import pytest_asyncio

from agents.memory.async_redis_checkpointer import (
    AsyncRedisSaver,
    _get_llm_usage_index_key,
    _get_llm_usage_key_prefix,
    _make_llm_usage_key,
)


@pytest.mark.asyncio
class TestAsyncRedisSaver:
    @pytest_asyncio.fixture
    async def fake_async_redis(self):
        async with fakeredis.FakeAsyncRedis() as client:
            yield client

    @pytest_asyncio.fixture
    def async_redis_saver(self, fake_async_redis):
        return AsyncRedisSaver(conn=fake_async_redis)

    @pytest.mark.parametrize(
        "cluster_id, data, ttl",
        [
            ("cluster1", {"usage": 100}, 0),
            ("test-cluster", {"usage": 200}, 10),
            ("123", {"usage": 300}, 5),
        ],
    )
    async def test_awrite_llm_usage(self, async_redis_saver, fake_async_redis, cluster_id, data, ttl):
        key = await async_redis_saver.awrite_llm_usage(cluster_id, data, ttl)

        stored_data = await fake_async_redis.get(key)
        assert stored_data is not None
        assert json.loads(stored_data) == data

        if ttl > 0:
            ttl_value = await fake_async_redis.ttl(key)
            assert ttl_value > 0

    async def test_awrite_llm_usage_adds_key_to_index(self, async_redis_saver, fake_async_redis):
        key = await async_redis_saver.awrite_llm_usage("cluster1", {"total": 1}, 60)

        index_key = _get_llm_usage_index_key("cluster1")
        assert await fake_async_redis.zrange(index_key, 0, -1) == [key.encode()]
        assert 0 < await fake_async_redis.ttl(index_key) <= 60  # noqa: PLR2004
        # the index is not listed as a usage record.
        assert await fake_async_redis.keys("llm_usage_*") == [key.encode()]

    async def test_alist_llm_usage_records(self, async_redis_saver, fake_async_redis):
        ttl = 100
        now = time.time()
        with patch("agents.memory.async_redis_checkpointer.time.time", return_value=now - ttl - 1):
            await async_redis_saver.awrite_llm_usage("cluster1", {"total": 1})
        with patch("agents.memory.async_redis_checkpointer.time.time", return_value=now - 10):
            await async_redis_saver.awrite_llm_usage("cluster1", {"total": 2})
            await async_redis_saver.awrite_llm_usage("cluster2", {"total": 4})

        records = await async_redis_saver.alist_llm_usage_records("cluster1", ttl)

        assert records == [{"total": 2}]
        # the expired entry is removed from the index.
        assert await fake_async_redis.zcard(_get_llm_usage_index_key("cluster1")) == 1

    async def test_alist_llm_usage_records_skips_expired_records(self, async_redis_saver, fake_async_redis):
        key = await async_redis_saver.awrite_llm_usage("cluster1", {"total": 1}, 60)
        await fake_async_redis.delete(key)

        assert await async_redis_saver.alist_llm_usage_records("cluster1", 60) == []

    async def test_alist_llm_usage_records_does_not_scan_key_space(self, async_redis_saver, fake_async_redis):
        await async_redis_saver.awrite_llm_usage("cluster1", {"total": 1}, 60)

        with (
            patch.object(fake_async_redis, "keys", side_effect=AssertionError("KEYS")),
            patch.object(fake_async_redis, "scan", side_effect=AssertionError("SCAN")),
        ):
            assert await async_redis_saver.alist_llm_usage_records("cluster1", 60) == [{"total": 1}]

    async def test_alist_llm_usage_records_without_index(self, async_redis_saver):
        assert await async_redis_saver.alist_llm_usage_records("cluster1", 60) == []


class TestUtilityFunctions:
    @pytest.mark.parametrize(
        "cluster_id, expected_prefix",
        [
            ("cluster1", "llm_usage_cluster1"),
            ("test-cluster", "llm_usage_test-cluster"),
            ("123", "llm_usage_123"),
        ],
    )
    def test_get_llm_usage_key_prefix(self, cluster_id, expected_prefix):
        assert _get_llm_usage_key_prefix(cluster_id) == expected_prefix

    @pytest.mark.parametrize(
        "cluster_id",
        [
            "cluster1",
            "test-cluster",
            "123",
        ],
    )
    def test_make_llm_usage_key(self, cluster_id):
        key = _make_llm_usage_key(cluster_id)

        assert key.startswith(_get_llm_usage_key_prefix(cluster_id))
        parts = key.split("_")
        expected_parts_count = 4
        assert len(parts) == expected_parts_count
        assert float(parts[-1]) > 0
