from collections.abc import Awaitable, Callable

import logfire
from bs4 import BeautifulSoup, Comment
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse


class BS4Middleware(BaseHTTPMiddleware):
    @logfire.instrument("bs4_middleware")
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        # Process the request
        response: Response = await call_next(request)

        # Skip streaming responses or responses without body attribute
        if isinstance(response, StreamingResponse) or not hasattr(response, "body"):
            return response

        # Only process HTML responses
        if not response.headers.get("content-type", "").startswith("text/html"):
            return response

        # Get the response body
        body = response.body
        if not isinstance(body, bytes):
            logfire.warning(
                "BS4Middleware received non-bytes body",
                body_type=type(body).__name__,
                path=request.url.path,
                method=request.method,
            )
            return response

        # Parse and format the HTML
        soup = BeautifulSoup(body.decode(), "html.parser")

        # Remove all comments
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        comment_count = len(comments)
        for comment in comments:
            comment.extract()

        # Update the response body with formatted HTML
        response.body = str(soup.prettify()).encode()

        logfire.info(
            "BS4Middleware processed HTML",
            path=request.url.path,
            method=request.method,
            comments_removed=comment_count,
        )

        return response
