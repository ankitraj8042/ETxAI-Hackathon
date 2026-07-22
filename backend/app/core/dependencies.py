"""
DCBrain Dependencies
Provides connection managers for PostgreSQL, Neo4j, Redis, and ChromaDB.
Implements resilient fallbacks for Redis (in-memory) and ChromaDB (local persistent client)
to ensure the platform runs out-of-the-box without Docker.
"""

import os
import asyncio
import redis.asyncio as aioredis
from neo4j import AsyncGraphDatabase
import chromadb

from app.core.config import settings

# ── Neo4j ──────────────────────────────────────────────────────────────

_neo4j_driver = None


async def get_neo4j_driver():
    """Get or create the Neo4j async driver."""
    global _neo4j_driver
    if _neo4j_driver is None:
        _neo4j_driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
    return _neo4j_driver


async def get_neo4j_session():
    """FastAPI dependency that provides a Neo4j async session."""
    driver = await get_neo4j_driver()
    async with driver.session() as session:
        yield session


async def close_neo4j():
    """Close the Neo4j driver on shutdown."""
    global _neo4j_driver
    if _neo4j_driver:
        await _neo4j_driver.close()
        _neo4j_driver = None


# ── Redis (with In-Memory Fallback) ────────────────────────────────────

class MockPubSub:
    """Mock Redis PubSub using asyncio Queues."""
    def __init__(self, client):
        self.client = client
        self.queue = asyncio.Queue()
        self.channels = []

    async def subscribe(self, channel: str):
        self.channels.append(channel)
        if channel not in self.client.channels:
            self.client.channels[channel] = []
        self.client.channels[channel].append(self.queue)

    async def unsubscribe(self, channel: str):
        if channel in self.channels:
            self.channels.remove(channel)
            if channel in self.client.channels:
                self.client.channels[channel].remove(self.queue)

    async def get_message(self, ignore_subscribe_messages=True, timeout=1.0):
        try:
            # Wait for item with timeout
            data = await asyncio.wait_for(self.queue.get(), timeout=timeout)
            return {
                "type": "message",
                "channel": self.channels[0] if self.channels else "cascade",
                "data": data
            }
        except asyncio.TimeoutError:
            return None


class MockRedis:
    """Mock Redis Client for in-memory message bus and caching."""
    def __init__(self):
        self.store = {}
        self.channels = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value: str, ex=None):
        self.store[key] = value
        return True

    async def publish(self, channel: str, message: str):
        if channel in self.channels:
            for queue in self.channels[channel]:
                await queue.put(message)
        return 1

    def pubsub(self):
        return MockPubSub(self)

    async def ping(self):
        return True

    async def close(self):
        pass


_redis_client = None
_use_mock_redis = False


async def get_redis():
    """Get or create the Redis client, falling back to MockRedis if offline."""
    global _redis_client, _use_mock_redis
    
    if _redis_client is None:
        if _use_mock_redis:
            _redis_client = MockRedis()
            return _redis_client

        try:
            # Try to connect to actual Redis server
            client = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=2.0
            )
            await client.ping()
            _redis_client = client
            print("🚀 Redis Client: Connected to Redis server.")
        except Exception as e:
            print(f"⚠️ Redis Client: Connection failed ({e}). Falling back to In-Memory Redis Mock.")
            _use_mock_redis = True
            _redis_client = MockRedis()

    return _redis_client


async def close_redis():
    """Close the Redis client on shutdown."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


# ── ChromaDB (using local process PersistentClient) ────────────────────

_chroma_client = None


def get_chroma_client():
    """Get or create the ChromaDB local persistent client."""
    global _chroma_client
    if _chroma_client is None:
        db_path = "./backend/data/chromadb"
        os.makedirs(db_path, exist_ok=True)
        # Using PersistentClient runs Chroma in-process, saving data locally.
        # No external Chroma server is required!
        _chroma_client = chromadb.PersistentClient(path=db_path)
        print(f"📚 ChromaDB: Local Persistent Client initialized at {db_path}")
    return _chroma_client
