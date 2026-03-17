import shutil


def is_tool_available(name: str) -> bool:
    return shutil.which(name) is not None


def get_dependency_status() -> dict:
    return {
        "ffmpeg": is_tool_available("ffmpeg"),
        "ffprobe": is_tool_available("ffprobe"),
    }