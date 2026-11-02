"""Tests of the instagram support."""

from __future__ import annotations

from seal.instagram import InstagramError, InstagramItem, parse_link


def test_parse_a_post_link() -> None:
    target = parse_link("https://www.instagram.com/p/C2zKxLbPAdq/")
    assert target is not None
    assert target.kind == "post"
    assert target.code == "C2zKxLbPAdq"


def test_parse_a_reel_link() -> None:
    target = parse_link("https://www.instagram.com/reel/DP5oMRXDTjt/")
    assert target is not None
    assert target.kind == "reel"
    assert target.code == "DP5oMRXDTjt"


def test_parse_a_profile_link() -> None:
    target = parse_link("https://www.instagram.com/nasa/")
    assert target is not None
    assert target.kind == "profile"
    assert target.username == "nasa"


def test_parse_a_story_link() -> None:
    target = parse_link("https://www.instagram.com/stories/nasa/3400000000/")
    assert target is not None
    assert target.kind == "story"
    assert target.username == "nasa"
    assert target.code == "3400000000"


def test_other_links_are_ignored() -> None:
    assert parse_link("https://example.com/p/abc/") is None
    assert parse_link("https://www.instagram.com/explore/") is None
    assert parse_link("") is None


def test_the_name_of_a_media_file() -> None:
    item = InstagramItem(
        media_url="https://example.com/1.jpg",
        username="nasa",
        date="2024-01-02 03:04",
        post_code="ABC",
    )
    assert item.filename == "nasa_2024-01-02_03-04_ABC.jpg"

    video = InstagramItem(
        media_url="https://example.com/1.mp4",
        is_video=True,
        username="nasa",
        date="2024-01-02 03:04",
        post_code="ABC",
    )
    assert video.filename.endswith(".mp4")
