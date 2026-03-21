import os
import platform
import signal
import subprocess
from pathlib import Path
from typing import Callable, Optional, Tuple


SUPPORTED_AUDIO_OUTPUTS = {
    "mp3": ".mp3",
    "wav": ".wav",
    "aac": ".aac",
    "flac": ".flac",
}

SUPPORTED_VIDEO_OUTPUTS = {
    "mp4": ".mp4",
    "mkv": ".mkv",
    "mov": ".mov",
    "avi": ".avi",
}

SUPPORTED_MEDIA_CONVERT_OUTPUTS = {
    "audio": ["mp3", "wav", "aac", "flac"],
    "video": ["mp4", "mkv", "mov", "avi"],
}

SUPPORTED_FRAME_OUTPUTS = {
    "png": ".png",
    "jpg": ".jpg",
    "webp": ".webp",
}


def _timestamp_to_seconds(value: str) -> float:
    try:
        hours, minutes, seconds = value.split(":")
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except Exception:
        return 0.0


class FFmpegConverter:
    def __init__(self):
        self.current_process: Optional[subprocess.Popen] = None

    def cancel(self):
        process = self.current_process
        if not process or process.poll() is not None:
            return

        try:
            if platform.system() == "Windows":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            else:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass

    def get_media_duration(self, input_file: str) -> float:
        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            input_file,
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
            )
            return float(result.stdout.strip())
        except Exception:
            return 0.0

    def _run_ffmpeg_command(
        self,
        command: list[str],
        input_file: str,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> Tuple[bool, str]:
        duration = self.get_media_duration(input_file)

        popen_kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
            "bufsize": 1,
        }

        if platform.system() == "Windows":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True

        try:
            self.current_process = subprocess.Popen(command, **popen_kwargs)

            if progress_callback is not None:
                progress_callback(0)

            if self.current_process.stdout is not None:
                for raw_line in self.current_process.stdout:
                    line = raw_line.strip()

                    if (
                        progress_callback is not None
                        and duration > 0
                        and line.startswith("out_time=")
                    ):
                        current_seconds = _timestamp_to_seconds(
                            line.split("=", 1)[1]
                        )
                        percent = int(
                            min(100, max(0, (current_seconds / duration) * 100))
                        )
                        progress_callback(percent)

                    elif progress_callback is not None and line == "progress=end":
                        progress_callback(100)

            stderr_text = ""
            if self.current_process.stderr is not None:
                stderr_text = self.current_process.stderr.read()

            return_code = self.current_process.wait()

            if return_code == 0:
                if progress_callback is not None:
                    progress_callback(100)
                return True, "Success"

            if return_code < 0 or return_code == 255:
                return False, "Cancelled"

            return False, stderr_text or "FFmpeg command failed."

        except Exception as e:
            return False, str(e)
        finally:
            self.current_process = None

    def video_to_audio(
        self,
        input_file: str,
        output_file: str,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> Tuple[bool, str]:
        input_path = Path(input_file)
        output_path = Path(output_file)

        if not input_path.exists():
            return False, f"Input file not found: {input_path}"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        command = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-progress",
            "pipe:1",
            "-nostats",
            "-i",
            str(input_path),
            "-vn",
            str(output_path),
        ]

        ok, result = self._run_ffmpeg_command(
            command=command,
            input_file=str(input_path),
            progress_callback=progress_callback,
        )

        if ok:
            return True, str(output_path)

        return False, result

    def video_to_gif(
        self,
        input_file: str,
        output_file: str,
        fps: int = 10,
        width: Optional[int] = 480,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> Tuple[bool, str]:
        input_path = Path(input_file)
        output_path = Path(output_file)

        if not input_path.exists():
            return False, f"Input file not found: {input_path}"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if width is None:
            filter_chain = (
                f"fps={fps},split[s0][s1];"
                f"[s0]palettegen[p];"
                f"[s1][p]paletteuse"
            )
        else:
            filter_chain = (
                f"fps={fps},scale={width}:-1:flags=lanczos,"
                f"split[s0][s1];"
                f"[s0]palettegen[p];"
                f"[s1][p]paletteuse"
            )

        command = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-progress",
            "pipe:1",
            "-nostats",
            "-i",
            str(input_path),
            "-vf",
            filter_chain,
            str(output_path),
        ]

        ok, result = self._run_ffmpeg_command(
            command=command,
            input_file=str(input_path),
            progress_callback=progress_callback,
        )

        if ok:
            return True, str(output_path)

        return False, result

    def gif_to_video(
        self,
        input_file: str,
        output_file: str,
        output_format: str,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> Tuple[bool, str]:
        input_path = Path(input_file)
        output_path = Path(output_file)

        if not input_path.exists():
            return False, f"Input file not found: {input_path}"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_format == "mp4":
            codec_args = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart"]
        elif output_format == "mkv":
            codec_args = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-an"]
        elif output_format == "mov":
            codec_args = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-an"]
        elif output_format == "avi":
            codec_args = ["-c:v", "mpeg4", "-an"]
        else:
            return False, f"Unsupported video output format: {output_format}"

        command = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-progress",
            "pipe:1",
            "-nostats",
            "-i",
            str(input_path),
            *codec_args,
            str(output_path),
        ]

        ok, result = self._run_ffmpeg_command(
            command=command,
            input_file=str(input_path),
            progress_callback=progress_callback,
        )

        if ok:
            return True, str(output_path)

        return False, result

    def convert_media_format(
        self,
        input_file: str,
        output_file: str,
        media_family: str,
        output_format: str,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> Tuple[bool, str]:
        input_path = Path(input_file)
        output_path = Path(output_file)

        if not input_path.exists():
            return False, f"Input file not found: {input_path}"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if media_family == "audio":
            if output_format == "mp3":
                codec_args = ["-vn", "-c:a", "libmp3lame", "-q:a", "2"]
            elif output_format == "wav":
                codec_args = ["-vn", "-c:a", "pcm_s16le"]
            elif output_format == "aac":
                codec_args = ["-vn", "-c:a", "aac", "-b:a", "192k"]
            elif output_format == "flac":
                codec_args = ["-vn", "-c:a", "flac"]
            else:
                return False, f"Unsupported audio output format: {output_format}"

        elif media_family == "video":
            if output_format == "mp4":
                codec_args = ["-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart"]
            elif output_format == "mkv":
                codec_args = ["-c:v", "libx264", "-c:a", "aac"]
            elif output_format == "mov":
                codec_args = ["-c:v", "libx264", "-c:a", "aac"]
            elif output_format == "avi":
                codec_args = ["-c:v", "mpeg4", "-c:a", "mp3"]
            else:
                return False, f"Unsupported video output format: {output_format}"

        else:
            return False, f"Unsupported media family: {media_family}"

        command = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-progress",
            "pipe:1",
            "-nostats",
            "-i",
            str(input_path),
            *codec_args,
            str(output_path),
        ]

        ok, result = self._run_ffmpeg_command(
            command=command,
            input_file=str(input_path),
            progress_callback=progress_callback,
        )

        if ok:
            return True, str(output_path)

        return False, result

    def extract_frames(
        self,
        input_file: str,
        output_pattern: str,
        image_format: str = "png",
        sample_fps: Optional[int] = None,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> Tuple[bool, str]:
        input_path = Path(input_file)

        if not input_path.exists():
            return False, f"Input file not found: {input_path}"

        if image_format not in SUPPORTED_FRAME_OUTPUTS:
            return False, f"Unsupported frame output format: {image_format}"

        output_parent = Path(output_pattern).parent
        output_parent.mkdir(parents=True, exist_ok=True)

        vf_args = []
        if sample_fps is not None and sample_fps > 0:
            vf_args = ["-vf", f"fps={sample_fps}"]

        command = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-progress",
            "pipe:1",
            "-nostats",
            "-i",
            str(input_path),
            *vf_args,
            output_pattern,
        ]

        ok, result = self._run_ffmpeg_command(
            command=command,
            input_file=str(input_path),
            progress_callback=progress_callback,
        )

        if ok:
            return True, str(output_parent)

        return False, result