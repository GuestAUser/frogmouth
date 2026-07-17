from gzip import compress

import httpx
import pytest

from frogmouth.widgets import viewer as viewer_module
from frogmouth.widgets.viewer import History


@pytest.mark.anyio
async def test_remote_markdown_is_bounded_after_decompression() -> None:
    decoded = b"x" * (viewer_module.MAX_DOCUMENT_BYTES + 1)

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=compress(decoded),
            headers={
                "content-encoding": "gzip",
                "content-type": "text/markdown; charset=utf-8",
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(viewer_module.DocumentTooLargeError):
            await viewer_module.download_markdown(
                client, httpx.URL("https://example.test/README.md")
            )


@pytest.mark.anyio
async def test_bounded_remote_markdown_decodes_text() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content="# Safe\n".encode(),
            headers={"content-type": "text/markdown; charset=utf-8"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        content = await viewer_module.download_markdown(
            client, httpx.URL("https://example.test/README.md")
        )

    assert content == "# Safe\n"


def test_deleting_current_final_history_entry_keeps_valid_location() -> None:
    history = History(
        [
            httpx.URL("https://example.test/one.md"),
            httpx.URL("https://example.test/two.md"),
        ]
    )

    del history[1]

    assert history.current == 0
    assert history.location == httpx.URL("https://example.test/one.md")


def test_deleting_entry_before_current_preserves_current_location() -> None:
    current = httpx.URL("https://example.test/two.md")
    history = History(
        [
            httpx.URL("https://example.test/one.md"),
            current,
            httpx.URL("https://example.test/three.md"),
        ]
    )
    history.back()

    del history[0]

    assert history.current == 0
    assert history.location == current
