"""Tests of the data classes."""

from __future__ import annotations

from seal.models import Format, Task, TaskState, VideoInfo

INFO = {
    "title": "A video",
    "uploader": "A channel",
    "duration": 125,
    "thumbnail": "https://example.com/thumb.png",
    "extractor_key": "Youtube",
    "_type": "video",
    "formats": [
        {
            "format_id": "137",
            "ext": "mp4",
            "resolution": "1920x1080",
            "vcodec": "avc1",
            "acodec": "none",
            "tbr": 4000,
            "filesize": 1000,
        },
        {
            "format_id": "140",
            "ext": "m4a",
            "vcodec": "none",
            "acodec": "mp4a",
            "tbr": 128,
        },
    ],
}


def test_video_info_from_info() -> None:
    info = VideoInfo.from_info("https://example.com/video", INFO)
    assert info.title == "A video"
    assert info.uploader == "A channel"
    assert info.duration_text == "2:05"
    assert len(info.formats) == 2
    assert not info.is_playlist


def test_video_info_of_a_playlist() -> None:
    info = VideoInfo.from_info(
        "https://example.com/list",
        {"_type": "playlist", "title": "A list", "entries": [{"url": "a"}, {"url": "b"}]},
    )
    assert info.is_playlist
    assert info.playlist_count == 2
    assert info.entries == ["a", "b"]


def test_format_properties() -> None:
    video = Format(format_id="1", ext="mp4", resolution="1920x1080", vcodec="avc1", tbr=4000)
    audio = Format(format_id="2", ext="m4a", acodec="mp4a", tbr=128)
    assert video.has_video and not video.has_audio
    assert audio.has_audio and not audio.has_video
    assert video.height == 1080
    assert "mp4" in video.label


def test_a_video_without_sound_gets_the_audio_of_the_website() -> None:
    """A video format without a sound would be downloaded without any sound."""
    video = Format(format_id="137", ext="mp4", resolution="1920x1080", vcodec="avc1")
    assert video.selector == "137+bestaudio/137"


def test_a_format_with_sound_is_used_as_it_is() -> None:
    complete = Format(format_id="18", ext="mp4", resolution="640x360", vcodec="avc1", acodec="mp4a")
    assert complete.selector == "18"


def test_task_progress_is_capped() -> None:
    task = Task(url="https://example.com", progress=1.5)
    assert task.progress_percent == 100
    task.progress = -1
    assert task.progress_percent == 0
    assert not task.state.is_finished
    task.state = TaskState.COMPLETED
    assert task.state.is_finished
