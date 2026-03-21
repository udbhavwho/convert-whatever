from pathlib import Path

from PySide6.QtCore import QObject, Signal

from converters.ffmpeg_converter import FFmpegConverter, SUPPORTED_FRAME_OUTPUTS


class ExtractFramesWorker(QObject):
    finished = Signal(str, str)
    progress = Signal(str, int)

    def __init__(
        self,
        input_files: list[str],
        output_dir: str,
        image_format: str,
        sample_fps: int | None,
    ):
        super().__init__()
        self.input_files = input_files
        self.output_dir = output_dir
        self.image_format = image_format.lower()
        self.sample_fps = sample_fps
        self.converter = FFmpegConverter()
        self._cancel_requested = False

    def cancel(self):
        self._cancel_requested = True
        self.converter.cancel()

    def _emit_file_progress(self, index: int, total: int, name: str, file_percent: int):
        overall = int((((index - 1) + (file_percent / 100)) / total) * 100)
        self.progress.emit(
            f"Extracting frames {index}/{total}: {name}",
            overall,
        )

    def run(self):
        success_count = 0
        failure_messages = []
        total = len(self.input_files)
        extension = SUPPORTED_FRAME_OUTPUTS[self.image_format]

        for index, input_file in enumerate(self.input_files, start=1):
            if self._cancel_requested:
                self.finished.emit(
                    "cancelled",
                    f"Cancelled. Extracted frames from {success_count} of {total} file(s).",
                )
                return

            input_path = Path(input_file)
            file_output_dir = Path(self.output_dir) / f"{input_path.stem}_frames"
            output_pattern = file_output_dir / f"frame_%06d{extension}"

            ok, result = self.converter.extract_frames(
                input_file=input_file,
                output_pattern=str(output_pattern),
                image_format=self.image_format,
                sample_fps=self.sample_fps,
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
                        f"Cancelled. Extracted frames from {success_count} of {total} file(s).",
                    )
                    return
                failure_messages.append(f"{input_path.name}: {result}")

        if success_count == total:
            self.finished.emit(
                "success",
                f"Extracted frames from {success_count} file(s) successfully.",
            )
            return

        if success_count > 0:
            joined = "\n".join(failure_messages)
            self.finished.emit(
                "partial",
                f"Extracted frames from {success_count} of {total} file(s).\n\n{joined}",
            )
            return

        joined = "\n".join(failure_messages)
        self.finished.emit("error", joined or "Frame extraction failed.")