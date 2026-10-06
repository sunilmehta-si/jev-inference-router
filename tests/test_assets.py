import httpx
import pytest

from jev_router.app import create_app
from jev_router.config import Settings


@pytest.mark.asyncio
async def test_ui_assets_and_security_headers():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(create_app(Settings())), base_url="http://test"
    ) as client:
        page = await client.get("/")
        assert page.status_code == 200 and 'id="question"' in page.text
        assert "script-src 'self'" in page.headers["Content-Security-Policy"]
        script = await client.get("/assets/app.js")
        assert script.status_code == 200
        assert "localStorage" not in script.text and "innerHTML" not in script.text
        assert (await client.get("/assets/not-allowed")).status_code == 404
