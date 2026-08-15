import fakeredis
import redis

from fplquant.api import cache as cache_module


def test_roundtrip_with_working_redis() -> None:
    cache_module.set_client(fakeredis.FakeRedis(decode_responses=True))

    cache_module.cache_set("k", "v", ttl_seconds=60)

    assert cache_module.cache_get("k") == "v"


def test_get_returns_none_on_cache_miss() -> None:
    cache_module.set_client(fakeredis.FakeRedis(decode_responses=True))
    assert cache_module.cache_get("does-not-exist") is None


def test_get_returns_none_when_redis_unreachable_instead_of_raising() -> None:
    unreachable = redis.Redis(
        host="localhost", port=1, socket_connect_timeout=0.1, socket_timeout=0.1
    )
    cache_module.set_client(unreachable)

    assert cache_module.cache_get("k") is None


def test_set_does_not_raise_when_redis_unreachable() -> None:
    unreachable = redis.Redis(
        host="localhost", port=1, socket_connect_timeout=0.1, socket_timeout=0.1
    )
    cache_module.set_client(unreachable)

    cache_module.cache_set("k", "v", ttl_seconds=60)  # must not raise
