import os
import json
import hashlib
from functools import lru_cache

@lru_cache(maxsize=1)
def connection():
    if not os.getenv('REDIS_URL'): return None
    from redis import Redis
    return Redis.from_url(os.environ['REDIS_URL'],socket_connect_timeout=1,socket_timeout=1,decode_responses=True)

def key(namespace,value): return 'researchos:'+namespace+':'+hashlib.sha256(value.encode()).hexdigest()
def get(cache_key):
    try:
        cache=connection()
        value=cache.get(cache_key) if cache else None
        return json.loads(value) if value else None
    except Exception: return None

def put(cache_key,value,ttl=3600):
    try:
        cache=connection()
        if cache: cache.setex(cache_key,ttl,json.dumps(value))
    except Exception: pass
