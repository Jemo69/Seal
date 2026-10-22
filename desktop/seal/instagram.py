"""Downloading of public Instagram posts, reels and profiles.

The media is fetched directly from Instagram, no third party service is involved. The
[instaloader](https://github.com/instaloader/instaloader) library does the work, it talks to
the same api the mobile application uses.

Stories and private posts need a session. The session file is created by the user, the
application never stores a password.
"""

from __future__ import annotations

import re
import threading
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

POST_PATTERN = re.compile(r"instagram\.com/(?:p|reel|reels|tv|embed)/(?P<code>[A-Za-z0-9_-]+)")
STORY_PATTERN = re.compile(
    r"instagram\.com/stories/(?P<user>[A-Za-z0-9_.]+)(?:/(?P<pk>\d+))?"
)
PROFILE_PATTERN = re.compile(r"instagram\.com/(?P<user>[A-Za-z0-9_.]+)/?$")


class InstagramError(Exception):
    """Raised when the media of a link cannot be read."""


@dataclass
class InstagramTarget:
    """What a pasted link points to."""

    kind: str  # post, reel, story or profile
    url: str
    code: str = ""
    username: str = ""

    @property
    def label(self) -> str:
        if self.kind == "profile":
            return f"@{self.username}"
        if self.kind == "story":
            return f"story of @{self.username}"
        return self.code


@dataclass
class InstagramItem:
    """A single photo or video."""

    media_url: str
    is_video: bool = False
    thumbnail: str = ""
    description: str = ""
    username: str = ""
    date: str = ""
    extension: str = ""
    post_code: str = ""

    @property
    def filename(self) -> str:
        stamp = self.date.replace(":", "-").replace(" ", "_") or "media"
        suffix = "mp4" if self.is_video else "jpg"
        return f"{self.username}_{stamp}_{self.post_code}.{suffix}"


def parse_link(url: str) -> InstagramTarget | None:
    """Reads the kind of media a link points to."""
    url = url.strip()
    if not url:
        return None
    if "instagram.com" not in url:
        return None

    story = STORY_PATTERN.search(url)
    if story:
        return InstagramTarget(
            kind="story",
            url=url,
            username=story.group("user"),
            code=story.group("pk") or "",
        )

    post = POST_PATTERN.search(url)
    if post:
        code = post.group("code")
        kind = "reel" if "/reel" in url else "post"
        return InstagramTarget(kind=kind, url=url, code=code)

    profile = PROFILE_PATTERN.search(url)
    if profile:
        user = profile.group("user")
        if user.lower() in {"p", "reel", "reels", "tv", "stories", "explore", "accounts"}:
            return None
        return InstagramTarget(kind="profile", url=url, username=user)
    return None


class InstagramClient:
    """Reads the media of an instagram link."""

    def __init__(self, session_file: str = "") -> None:
        self.session_file = session_file
        self._loader: Any = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ loader

    def _get_loader(self) -> Any:
        """Creates the instaloader instance, it is only created once."""
        with self._lock:
            if self._loader is not None:
                return self._loader
            try:
                import instaloader
            except ImportError as error:  # pragma: no cover - depends on the environment
                raise InstagramError(
                    "instaloader is not installed, run 'pip install -r requirements.txt'"
                ) from error

            loader = instaloader.Instaloader(
                quiet=True,
                download_pictures=False,
                download_videos=False,
                download_video_thumbnails=False,
                download_geotags=False,
                download_comments=False,
                save_metadata=False,
                compress_json=False,
                user_agent=USER_AGENT,
                max_connection_attempts=1,
                request_timeout=15.0,
            )
            if self.session_file and Path(self.session_file).exists():
                try:
                    loader.load_session_from_file(self.session_file)
                except Exception as error:  # noqa: BLE001 - the message is shown to the user
                    raise InstagramError(
                        f"The session file could not be read: {error}"
                    ) from error
            self._loader = loader
            return loader

    @property
    def available(self) -> bool:
        """Whether instaloader is installed."""
        try:
            import instaloader  # noqa: F401
        except ImportError:
            return False
        return True

    # ------------------------------------------------------------------ reading

    def fetch(self, target: InstagramTarget, limit: int = 25) -> list[InstagramItem]:
        """Returns the media of the given target."""
        if target.kind == "profile":
            return self._fetch_profile(target, limit)
        if target.kind == "story":
            return self._fetch_story(target)
        return self._fetch_post(target)

    def _fetch_post(self, target: InstagramTarget) -> list[InstagramItem]:
        loader = self._get_loader()
        import instaloader

        try:
            post = instaloader.Post.from_shortcode(loader.context, target.code)
        except Exception as error:  # noqa: BLE001 - the message is shown to the user
            raise InstagramError(
                "The post could not be read. Instagram asks for a login for most of the "
                f"content, a session file solves that. ({error})"
            ) from error

        items: list[InstagramItem] = []
        nodes = [post]
        if post.is_sidecar:
            try:
                nodes = list(post.get_sidecar_nodes())
            except Exception:  # noqa: BLE001 - a single media is downloaded instead
                nodes = [post]

        for node in nodes:
            items.append(self._to_item(node, target.code))
        return items

    def _fetch_profile(self, target: InstagramTarget, limit: int) -> list[InstagramItem]:
        loader = self._get_loader()
        import instaloader

        try:
            profile = instaloader.Profile.from_username(loader.context, target.username)
        except Exception as error:  # noqa: BLE001 - the message is shown to the user
            raise InstagramError(f"The profile could not be read: {error}") from error

        if getattr(profile, "is_private", False) and not self.session_file:
            raise InstagramError(
                "This profile is private, a session file is needed to see its posts."
            )

        items: list[InstagramItem] = []
        try:
            for post in profile.get_posts():
                if len(items) >= limit:
                    break
                items.append(self._to_item(post, post.shortcode))
        except Exception as error:  # noqa: BLE001 - the message is shown to the user
            raise InstagramError(f"The posts could not be read: {error}") from error
        return items

    def _fetch_story(self, target: InstagramTarget) -> list[InstagramItem]:
        loader = self._get_loader()
        import instaloader

        if not self.session_file:
            raise InstagramError(
                "Stories are only available with a session file, see the settings."
            )
        try:
            story = instaloader.Story.from_story_pk(loader.context, target.code)
        except Exception as error:  # noqa: BLE001 - the message is shown to the user
            raise InstagramError(f"The story could not be read: {error}") from error

        items = [self._to_item(story, target.code or "story")]
        if story.has_video:
            items.append(self._to_item(story, target.code or "story"))
        return items

    def _to_item(self, node: Any, code: str) -> InstagramItem:
        is_video = bool(getattr(node, "is_video", False))
        media_url = node.video_url if is_video else node.media_url
        thumbnail = ""
        try:
            thumbnail = node.url  # the url of the post is used as the preview
        except Exception:  # noqa: BLE001 - the preview is optional
            thumbnail = ""

        description = ""
        date = ""
        username = ""
        try:
            description = (node.caption or "").strip()
        except Exception:  # noqa: BLE001 - the description is optional
            description = ""
        try:
            date = node.date_utc.strftime("%Y-%m-%d %H:%M")
        except Exception:  # noqa: BLE001 - the date is optional
            date = ""
        try:
            username = node.owner_username
        except Exception:  # noqa: BLE001 - the name is optional
            username = ""

        return InstagramItem(
            media_url=media_url,
            is_video=is_video,
            thumbnail=thumbnail,
            description=description[:280],
            username=username,
            date=date,
            extension="mp4" if is_video else "jpg",
            post_code=code,
        )

    # --------------------------------------------------------------- downloading

    def download(self, item: InstagramItem, target_dir: Path) -> Path:
        """Downloads a single media file."""
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / item.filename
        request = urllib.request.Request(item.media_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read()
        target.write_bytes(data)
        return target
