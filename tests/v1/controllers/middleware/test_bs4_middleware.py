from unittest.mock import AsyncMock, Mock

import pytest
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

from app.v1.controllers.middleware.bs4_middleware import BS4Middleware


class TestBS4Middleware:
    @pytest.fixture
    def middleware(self):
        return BS4Middleware(app=Mock())

    @pytest.fixture
    def mock_request(self):
        request = Mock()
        request.url.path = "/test"
        request.method = "GET"
        return request

    @pytest.fixture
    def html_with_comments(self):
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <!-- This is a comment -->
            <title>Test</title>
        </head>
        <body>
            <!-- Another comment -->
            <h1>Hello World</h1>
            <!-- Final comment -->
        </body>
        </html>
        """.encode()

    @pytest.fixture
    def plain_html(self):
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test</title>
        </head>
        <body>
            <h1>Hello World</h1>
        </body>
        </html>
        """.encode()

    @pytest.mark.asyncio
    async def test_processes_html_and_removes_comments(self, middleware, mock_request, html_with_comments):
        response = Response(content=html_with_comments, media_type="text/html")
        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch.__wrapped__(middleware, mock_request, call_next)

        assert isinstance(result, Response)
        decoded_body = result.body.decode()
        assert "<!-- This is a comment -->" not in decoded_body
        assert "<!-- Another comment -->" not in decoded_body
        assert "<!-- Final comment -->" not in decoded_body
        assert "Test" in decoded_body
        assert "Hello World" in decoded_body

    @pytest.mark.asyncio
    async def test_processes_html_without_comments(self, middleware, mock_request, plain_html):
        response = Response(content=plain_html, media_type="text/html")
        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch.__wrapped__(middleware, mock_request, call_next)

        assert isinstance(result, Response)
        decoded_body = result.body.decode()
        assert "Test" in decoded_body
        assert "Hello World" in decoded_body

    @pytest.mark.asyncio
    async def test_skips_streaming_response(self, middleware, mock_request):
        streaming_response = StreamingResponse(iter([b"test"]), media_type="text/html")
        call_next = AsyncMock(return_value=streaming_response)

        result = await middleware.dispatch.__wrapped__(middleware, mock_request, call_next)

        assert result is streaming_response

    @pytest.mark.asyncio
    async def test_skips_response_without_body_attribute(self, middleware, mock_request):
        response = Mock(spec=["headers"])
        response.headers = {"content-type": "text/html"}
        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch.__wrapped__(middleware, mock_request, call_next)

        assert result is response

    @pytest.mark.asyncio
    async def test_skips_non_html_content(self, middleware, mock_request):
        response = Response(content="test", media_type="application/json")
        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch.__wrapped__(middleware, mock_request, call_next)

        assert result is response
        assert result.body == b"test"

    @pytest.mark.asyncio
    async def test_skips_response_without_content_type(self, middleware, mock_request):
        response = Response(content="test")
        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch.__wrapped__(middleware, mock_request, call_next)

        assert result is response
        assert result.body == b"test"

    @pytest.mark.asyncio
    async def test_handles_non_bytes_body(self, middleware, mock_request):
        response = Mock()
        response.headers = {"content-type": "text/html"}
        response.body = "not bytes"
        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch.__wrapped__(middleware, mock_request, call_next)

        assert result is response

    @pytest.mark.asyncio
    async def test_content_type_with_charset(self, middleware, mock_request, html_with_comments):
        response = Response(content=html_with_comments, media_type="text/html; charset=utf-8")
        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch.__wrapped__(middleware, mock_request, call_next)

        assert isinstance(result, Response)
        decoded_body = result.body.decode()
        assert "<!-- This is a comment -->" not in decoded_body

    @pytest.mark.asyncio
    async def test_empty_html(self, middleware, mock_request):
        response = Response(content="", media_type="text/html")
        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch.__wrapped__(middleware, mock_request, call_next)

        assert isinstance(result, Response)
        # For empty content, the body will be empty since BS4 processing happened
        # but there was no actual HTML content to process
        assert result.body.decode() == ""

    @pytest.mark.asyncio
    async def test_malformed_html(self, middleware, mock_request):
        malformed_html = b"<div><p>Test</div>"
        response = Response(content=malformed_html, media_type="text/html")
        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch.__wrapped__(middleware, mock_request, call_next)

        assert isinstance(result, Response)
        decoded_body = result.body.decode()
        assert "Test" in decoded_body

    @pytest.mark.asyncio
    async def test_html_with_nested_comments(self, middleware, mock_request):
        html_with_nested = b"""
        <html>
        <body>
            <!-- Outer comment
                <!-- Inner comment -->
            -->
            <p>Content</p>
        </body>
        </html>
        """
        response = Response(content=html_with_nested, media_type="text/html")
        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch.__wrapped__(middleware, mock_request, call_next)

        assert isinstance(result, Response)
        decoded_body = result.body.decode()
        assert "<!-- Outer comment" not in decoded_body
        assert "<!-- Inner comment -->" not in decoded_body
        assert "Content" in decoded_body
