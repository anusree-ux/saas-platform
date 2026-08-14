import time

from app.redis_client import redis_client

BUCKET_CAPACITY = 10
REFILL_RATE = 10.0
TOKEN_BUCKET_SCRIPT = """
local key = KEYS[1]

local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local cost = tonumber(ARGV[4])

local data = redis.call("HMGET", key, "tokens", "last_refill")

local tokens = tonumber(data[1])
local last_refill = tonumber(data[2])

if tokens == nil then
    tokens = capacity
    last_refill = now
end

local elapsed = now - last_refill
local refill = elapsed * refill_rate

tokens = math.min(capacity, tokens + refill)

local allowed = 0

if tokens >= cost then
    tokens = tokens - cost
    allowed = 1
end

redis.call("HSET", key,
    "tokens", tokens,
    "last_refill", now
)

return {allowed, tokens}
"""


def check_and_consume(tenant_id) -> bool:
    key = f"rate_limit:tenant:{tenant_id}"

    now = time.time()

    result = redis_client.eval(
        TOKEN_BUCKET_SCRIPT,
        1,
        key,
        BUCKET_CAPACITY,
        REFILL_RATE,
        now,
        1,
    )

    return bool(result[0])