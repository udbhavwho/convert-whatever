from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PIL import Image, ImageOps


SUPPORTED_IMAGE_OUTPUTS = ["png", "jpg", "jpeg", "webp", "bmp", "tiff"]


class ImageConvertWorker(QObject):
    finished = Signal(str, str)
    progress = Signal(str, int)

    def __init__(self, input_files: list[str], output_dir: str, output_format: str):
        super().__init__()
        self.input_files = input_files
        self.output_dir = output_dir
        self.output_format = output_format.lower()
        self._cancel_requested = False

    def cancel(self):
        self._cancel_requested = True

    def _save_image(self, img: Image.Image, output_path: Path):
        fmt = self.output_format.upper()
        if fmt == "JPG":
            fmt = "JPEG"

        if self.output_format in {"jpg", "jpeg"}:
            if img.mode not in {"RGB", "L"}:
                img = img.convert("RGB")
            img.save(output_path, format="JPEG", quality=95, optimize=True, progressive=True)
            return

        if self.output_format == "webp":
            if img.mode == "P":
                img = img.convert("RGBA")
            img.save(output_path, format="WEBP", quality=95, method=6)
            return

        img.save(output_path, format=fmt)

    def run(self):
        success_count = 0
        failure_messages = []
        total = len(self.input_files)

        for index, input_file in enumerate(self.input_files, start=1):
            if self._cancel_requested:
                self.finished.emit(
                    "cancelled",
                    f"Cancelled. Converted {success_count} of {total} image(s).",
                )
                return

            input_path = Path(input_file)
            output_path = Path(self.output_dir) / f"{input_path.stem}.{self.output_format}"

            start_percent = int(((index - 1) / total) * 100)
            self.progress.emit(f"Converting {index}/{total}: {input_path.name}", start_percent)

            try:
                with Image.open(input_path) as img:
                    img = ImageOps.exif_transpose(img)
                    self._save_image(img, output_path)
                success_count += 1
            except Exception as e:
                failure_messages.append(f"{input_path.name}: {e}")

            end_percent = int((index / total) * 100)
            self.progress.emit(f"Finished {index}/{total}: {input_path.name}", end_percent)

        if success_count == total:
            self.finished.emit(
                "success",
                f"Converted {success_count} image(s) to {self.output_format.upper()} successfully.",
            )
            return

        if success_count > 0:
            joined = "\n".join(failure_messages)
            self.finished.emit(
                "partial",
                f"Converted {success_count} of {total} image(s).\n\n{joined}",
            )
            return

        joined = "\n".join(failure_messages)
        self.finished.emit("error", joined or "Image format conversion failed.")