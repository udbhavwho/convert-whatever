from dataclasses import dataclass


@dataclass
class AppState:
    ffmpeg_available: bool = False
    ffprobe_available: bool = False