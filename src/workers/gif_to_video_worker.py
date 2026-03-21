from pathlib import Path

from PySide6.QtCore import QObject, Signal

from converters.ffmpeg_converter import FFmpegConverter, SUPPORTED_VIDEO_OUTPUTS


class GifToVideoWorker(QObject):
    finished = Signal(str, str)
    progress = Signal(str, int)

    def __init__(
        self,
        input_files: list[str],
        output_dir: str,
        output_format: str,
    ):
        super().__init__()
        self.input_files = input_files
        self.output_dir = output_dir
        self.output_format = output_format.lower()
        self.converter = FFmpegConverter()
        self._cancel_requested = False

    def cancel(self):
        self._cancel_requested = True
        self.converter.cancel()

    def _emit_file_progress(self, index: int, total: int, name: str, file_percent: int):
        overall = int((((index - 1) + (file_percent / 100)) / total) * 100)
        self.progress.emit(
            f"Converting GIF {index}/{total}: {name}",
            overall,
        )

    def run(self):
        success_count = 0
        failure_messages = []
        total = len(self.input_files)
        extension = SUPPORTED_VIDEO_OUTPUTS[self.output_format]

        for index, input_file in enumerate(self.input_files, start=1):
            if self._cancel_requested:
                self.finished.emit(
                    "cancelled",
                    f"Cancelled. Converted {success_count} of {total} GIF file(s).",
                )
                return

            input_path = Path(input_file)
            output_file = Path(self.output_dir) / f"{input_path.stem}{extension}"

            ok, result = self.converter.gif_to_video(
                input_file=input_file,
                output_file=str(output_file),
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
                        f"Cancelled. Converted {success_count} of {total} GIF file(s).",
                    )
                    return
                failure_messages.append(f"{input_path.name}: {result}")

        if success_count == total:
            self.finished.emit(
                "success",
                f"Converted {success_count} GIF file(s) to {self.output_format.upper()} successfully.",
            )
            return

        if success_count > 0:
            joined = "\n".join(failure_messages)
            self.finished.emit(
                "partial",
                f"Converted {success_count} of {total} GIF file(s).\n\n{joined}",
            )
            return

        joined = "\n".join(failure_messages)
        self.finished.emit("error", joined or "GIF to video conversion failed.")