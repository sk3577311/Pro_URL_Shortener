# import os
# from dotenv import load_dotenv
# import redis.asyncio as aioredis

# load_dotenv()  # take environment variables from .env.
# redis_client = None  # global instance

# async def init_redis_pool():
#     global redis_client
#     redis_url = os.getenv("REDIS_URL")
#     redis_client = aioredis.from_url(
#         redis_url,
#         decode_responses=True
#     )
#     await redis_client.ping()  # test connection
#     print("✅ Connected to Redis Cloud successfully")
#     return redis_client

# async def close_redis():
#     global redis_client
#     if redis_client:
#         await redis_client.close()
#         print("❌ Redis connection closed")

# redis = aioredis(
#     url=os.getenv("UPSTASH_REDIS_REST_URL"),
#     token=os.getenv("UPSTASH_REDIS_REST_TOKEN")
# )
import os
from upstash_redis import Redis

# Initialize Redis client with Upstash REST API
redis_client = Redis(
    url=os.getenv("UPSTASH_REDIS_REST_URL"),
    token=os.getenv("UPSTASH_REDIS_REST_TOKEN")
)

# Optional test function
async def test_connection():
    try:
        await redis_client.set("test", "connected")
        value = await redis_client.get("test")
        print("✅ Connected to Upstash Redis successfully:", value)
    except Exception as e:
        print("❌ Redis connection failed:", e)
