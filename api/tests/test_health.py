import asyncio

import httpx

from app.main import create_app


def test_health_returns_operational_status() -> None:
    response = asyncio.run(_get("/api/health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def _get(path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        return await client.get(path)
