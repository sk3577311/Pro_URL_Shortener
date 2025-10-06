import tracemalloc
import asyncio
import redis.asyncio as aioredis

tracemalloc.start()

async def test():
    client = aioredis.from_url("redis://:EwvMtESNIZoJ0OrgBFX2fiUuEL11Tpqv@redis-11398.c278.us-east-1-4.ec2.redns.redis-cloud.com:11398", decode_responses=True)
    print(await client.ping())

asyncio.run(test())