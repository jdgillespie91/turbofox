from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.testclient import TestClient

from app.v1.controllers.v1_router import index, lifespan, router


class TestLifespan:
    @pytest.mark.asyncio
    @patch("app.v1.controllers.v1_router.upgrade")
    async def test_lifespan_calls_upgrade(self, mock_upgrade: MagicMock):
        app = FastAPI()
        
        async with lifespan(app):
            pass
        
        mock_upgrade.assert_called_once()


class TestRouter:
    def test_router_configuration(self):
        assert router.prefix == "/v1"
        assert router.tags == ["v1"]

    def test_index_endpoint(self):
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        response = client.get("/v1/", follow_redirects=False)
        
        assert response.status_code == 307
        assert response.headers["location"] == "/v5/budget"

    @pytest.mark.asyncio
    async def test_index_endpoint_returns_redirect_response(self):
        response = await index()
        
        assert isinstance(response, RedirectResponse)
        assert response.headers["location"] == "/v5/budget"
