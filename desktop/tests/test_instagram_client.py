"""Tests of the instagram client with a fake instaloader."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from seal.instagram import InstagramClient, InstagramError, parse_link


class FakeNode:
    """Stands in for a post of instaloader."""

    is_video = False
    is_sidecar = False
    caption = "A caption"
    shortcode = "ABC"
    owner_username = "nasa"
    media_url = "https://example.com/photo.jpg"
    video_url = "https://example.com/video.mp4"
    url = "https://www.instagram.com/p/ABC/"

    class date_utc:  # noqa: N801 - the name comes from instaloader
        @staticmethod
        def strftime(_format: str) -> str:
            return "2024-01-02 03:04"


class FakeSidecarNode(FakeNode):
    is_video = True
    media_url = "https://example.com/photo2.jpg"


class FakePost(FakeNode):
    is_sidecar = True

    def get_sidecar_nodes(self):
        return [FakeNode(), FakeSidecarNode()]


def install_fake_instaloader(monkeypatch) -> None:
    """Puts a fake instaloader into the python path."""
    module = types.ModuleType("instaloader")

    class Post(FakePost):
        @classmethod
        def from_shortcode(cls, context, shortcode):  # noqa: ANN001 - the fake api
            return cls()

    class Profile:
        is_private = False

        @classmethod
        def from_username(cls, context, username):  # noqa: ANN001 - the fake api
            return cls()

        def get_posts(self):
            return [FakeNode()]

    class Story:
        has_video = False

        @classmethod
        def from_story_pk(cls, context, pk):  # noqa: ANN001 - the fake api
            return cls()

    module.Post = Post
    module.Profile = Profile
    module.Story = Story
    module.Instaloader = lambda **kwargs: types.SimpleNamespace(context=object())
    monkeypatch.setitem(sys.modules, "instaloader", module)


def test_fetch_a_post(monkeypatch) -> None:
    install_fake_instaloader(monkeypatch)
    client = InstagramClient()
    target = parse_link("https://www.instagram.com/p/ABC/")
    assert target is not None

    items = client.fetch(target)
    assert len(items) == 2
    assert items[0].is_video is False
    assert items[1].is_video is True
    assert items[0].filename.endswith(".jpg")
    assert items[1].filename.endswith(".mp4")


def test_fetch_a_profile(monkeypatch) -> None:
    install_fake_instaloader(monkeypatch)
    client = InstagramClient()
    target = parse_link("https://www.instagram.com/nasa/")
    assert target is not None

    items = client.fetch(target, limit=5)
    assert len(items) == 1
    assert items[0].username == "nasa"


def test_a_story_needs_a_session(monkeypatch) -> None:
    install_fake_instaloader(monkeypatch)
    client = InstagramClient()
    target = parse_link("https://www.instagram.com/stories/nasa/1234/")
    assert target is not None

    with pytest.raises(InstagramError, match="session"):
        client.fetch(target)


def test_a_missing_instaloader_is_reported(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "instaloader", None)
    client = InstagramClient()
    target = parse_link("https://www.instagram.com/p/ABC/")
    assert target is not None
    with pytest.raises(InstagramError, match="instaloader"):
        client.fetch(target)


def test_download_writes_the_file(monkeypatch, tmp_path: Path) -> None:
    from seal.instagram import InstagramItem

    class FakeResponse:
        def __init__(self, data: bytes) -> None:
            self.data = data

        def read(self) -> bytes:
            return self.data

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        "urllib.request.urlopen", lambda request, timeout=0: FakeResponse(b"data")
    )
    client = InstagramClient()
    item = InstagramItem(media_url="https://example.com/photo.jpg", username="nasa")
    path = client.download(item, tmp_path)
    assert path.exists()
    assert path.read_bytes() == b"data"
