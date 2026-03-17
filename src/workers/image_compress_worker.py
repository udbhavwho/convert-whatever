from PySide6.QtCore import QObject, Signal

from converters.image_converter import compress_single_image


class ImageCompressWorker(QObject):
    finished = Signal(str, str)
    progress = Signal(str)

    def __init__(self, input_files: list[str], output_dir: str, strength: int):
        super().__init__()
        self.input_files = input_files
        self.output_dir = output_dir
        self.strength = strength
        self._cancel_requested = False

    def cancel(self):
        self._cancel_requested = True

    def run(self):
        success_count = 0
        failure_messages = []
        total = len(self.input_files)

        for index, input_file in enumerate(self.input_files, start=1):
            if self._cancel_requested:
                self.finished.emit(
                    "cancelled",
                    f"Cancelled. Compressed {success_count} of {total} image(s).",
                )
                return

            self.progress.emit(f"Compressing {index}/{total}: {input_file}")

            ok, result = compress_single_image(
                input_file=input_file,
                output_dir=self.output_dir,
                strength=self.strength,
            )

            if ok:
                success_count += 1
            else:
                failure_messages.append(result)

        if success_count == total:
            self.finished.emit(
                "success",
                f"Compressed {success_count} image(s) successfully.",
            )
            return

        if success_count > 0:
            joined = "\n".join(failure_messages)
            self.finished.emit(
                "partial",
                f"Compressed {success_count} of {total} image(s).\n\n{joined}",
            )
            return

        joined = "\n".join(failure_messages)
        self.finished.emit(
            "error",
            joined or "Image compression failed.",
        )