from pathlib import Path

from PySide6.QtCore import QObject, Signal

from converters.ffmpeg_converter import (
    FFmpegConverter,
    SUPPORTED_AUDIO_OUTPUTS,
    SUPPORTED_VIDEO_OUTPUTS,
)


class MediaConvertWorker(QObject):
    finished = Signal(str, str)
    progress = Signal(str, int)

    def __init__(
        self,
        input_files: list[str],
        output_dir: str,
        media_family: str,
        output_format: str,
    ):
        super().__init__()
        self.input_files = input_files
        self.output_dir = output_dir
        self.media_family = media_family
        self.output_format = output_format.lower()
        self.converter = FFmpegConverter()
        self._cancel_requested = False

    def cancel(self):
        self._cancel_requested = True
        self.converter.cancel()

    def _emit_file_progress(self, index: int, total: int, name: str, file_percent: int):
        overall = int((((index - 1) + (file_percent / 100)) / total) * 100)
        self.progress.emit(
            f"Converting {index}/{total}: {name}",
            overall,
        )

    def _get_extension(self) -> str:
        if self.media_family == "audio":
            return SUPPORTED_AUDIO_OUTPUTS[self.output_format]
        if self.media_family == "video":
            return SUPPORTED_VIDEO_OUTPUTS[self.output_format]
        raise ValueError(f"Unsupported media family: {self.media_family}")

    def run(self):
        success_count = 0
        failure_messages = []
        total = len(self.input_files)
        extension = self._get_extension()

        for index, input_file in enumerate(self.input_files, start=1):
            if self._cancel_requested:
                self.finished.emit(
                    "cancelled",
                    f"Cancelled. Converted {success_count} of {total} file(s).",
                )
                return

            input_path = Path(input_file)
            output_file = Path(self.output_dir) / f"{input_path.stem}{extension}"

            ok, result = self.converter.convert_media_format(
                input_file=input_file,
                output_file=str(output_file),
                media_family=self.media_family,
                output_format=self.output_format,
                progress_callback=lambda percent, idx=index, name=input_path.name: self._emit_file_progress(
                    idx, total, name, percent
                ),
            )

            if ok:
                success_count += 1
            else:
                if result == "Cancelled":
                    self.finished.emit(
                        "cancelled",
                        f"Cancelled. Converted {success_count} of {total} file(s).",
                    )
                    return
                failure_messages.append(f"{input_path.name}: {result}")

        if success_count == total:
            self.finished.emit(
                "success",
                f"Converted {success_count} {self.media_family} file(s) to {self.output_format.upper()}.",
            )
            return

        if success_count > 0:
            joined = "\n".join(failure_messages)
            self.finished.emit(
                "partial",
                f"Converted {success_count} of {total} file(s).\n\n{joined}",
            )
            return

        joined = "\n".join(failure_messages)
        self.finished.emit("error", joined or "Media format conversion failed.")