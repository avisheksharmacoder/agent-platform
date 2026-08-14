import asyncio
from lorealdb import DBEngineWebServer, DBEngine


class AsyncQueueDBEngine:
    def __init__(self, path: str):
        self._db = DBEngineWebServer(path=path)

    async def get(self, id: str):
        return await asyncio.to_thread(self._db.get, id)

    async def scan_prefix(self, prefix: str, limit: int = None, offset: int = 0):
        results = await asyncio.to_thread(self._db.scan_prefix, prefix)
        if limit is not None:
            return results[offset : offset + limit]
        return results[offset:]

    async def filter_by_metadata(self, index_key: str, index_value: str, limit: int = None, offset: int = None):
        return await asyncio.to_thread(
            self._db.filter_by_metadata, index_key, index_value, limit, offset
        )

    # sync database operations for rust.
    async def insert(self, id: str, payload: dict):
        self._db.insert(id, payload)
        return

    async def upsert(self, id: str, payload: dict):
        self._db.upsert(id, payload)
        return

    async def delete(self, id: str):
        self._db.delete(id)
        return

    def close_engine(self):
        self._db.close_engine()


class AsyncDBEngine:
    def __init__(self, path: str):
        self._db = DBEngineWebServer(path=path)

    async def get(self, id: str):
        return await asyncio.to_thread(self._db.get, id)

    async def insert(self, id: str, payload: dict):
        self._db.insert(id, payload)
        return

    async def upsert(self, id: str, payload: dict):
        self._db.upsert(id, payload)
        return

    async def scan_prefix(self, prefix: str, limit: int = None, offset: int = 0):
        results = await asyncio.to_thread(self._db.scan_prefix, prefix)
        if limit is not None:
            return results[offset : offset + limit]
        return results[offset:]

    async def filter_by_metadata(self, index_key: str, index_value: str, limit: int = None, offset: int = None):
        return await asyncio.to_thread(
            self._db.filter_by_metadata, index_key, index_value, limit, offset
        )

    async def delete(self, id: str):
        self._db.delete(id)
        return

    def close_engine(self):
        self._db.close_engine()
