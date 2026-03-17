import subprocess
from pathlib import Path


class FFmpegConverter:
    @staticmethod
    def video_to_audio(input_file: str, output_file: str) -> tuple[bool, str]:
        input_path = Path(input_file)
        output_path = Path(output_file)

        if not input_path.exists():
            return False, f"Input file not found: {input_path}"

        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-vn",
            str(output_path),
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
            )
            return True, result.stdout or "Conversion completed successfully."
        except subprocess.CalledProcessError as e:
            return False, e.stderr or "FFmpeg conversion failed."
        except Exception as e:
            return False, str(e)