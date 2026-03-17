from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageOps


SUPPORTED_IMAGE_COMPRESSION_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tiff",
    ".tif",
}


def _map_strength_to_quality(strength: int) -> int:
    """
    Maps 0-100 compression strength to JPEG/WEBP quality.
    Lower quality means stronger compression.
    """
    strength = max(0, min(100, strength))
    return max(20, 95 - int(strength * 0.7))


def _map_strength_to_png_compress_level(strength: int) -> int:
    """
    Maps 0-100 compression strength to PNG compress level (0-9).
    """
    strength = max(0, min(100, strength))
    return min(9, max(1, round((strength / 100) * 9)))


def _map_strength_to_png_colors(strength: int) -> int:
    """
    Higher compression strength = fewer colors for PNG palette conversion.
    """
    if strength <= 25:
        return 256
    if strength <= 50:
        return 128
    if strength <= 75:
        return 64
    return 32


def _maybe_resize_image(image: Image.Image, strength: int) -> Image.Image:
    """
    For stronger compression, resize very large images down.
    Small images are left unchanged.
    """
    max_dimension = None

    if strength <= 25:
        max_dimension = None
    elif strength <= 50:
        max_dimension = 2400
    elif strength <= 75:
        max_dimension = 1800
    else:
        max_dimension = 1280

    if max_dimension is None:
        return image

    width, height = image.size
    largest_side = max(width, height)

    if largest_side <= max_dimension:
        return image

    scale = max_dimension / largest_side
    new_size = (int(width * scale), int(height * scale))
    return image.resize(new_size, Image.LANCZOS)


def compress_single_image(
    input_file: str,
    output_dir: str,
    strength: int,
) -> Tuple[bool, str]:
    input_path = Path(input_file)
    output_path_dir = Path(output_dir)

    if not input_path.exists():
        return False, f"Input file not found: {input_path}"

    suffix = input_path.suffix.lower()

    if suffix not in SUPPORTED_IMAGE_COMPRESSION_EXTENSIONS:
        return False, f"Unsupported image format for compression: {suffix}"

    output_path_dir.mkdir(parents=True, exist_ok=True)

    try:
        with Image.open(input_path) as img:
            img = ImageOps.exif_transpose(img)
            img = _maybe_resize_image(img, strength)

            quality = _map_strength_to_quality(strength)

            # JPEG / JPG
            if suffix in {".jpg", ".jpeg"}:
                output_path = output_path_dir / f"{input_path.stem}_compressed.jpg"

                if img.mode not in {"RGB", "L"}:
                    img = img.convert("RGB")

                img.save(
                    output_path,
                    format="JPEG",
                    quality=quality,
                    optimize=True,
                    progressive=True,
                )
                return True, str(output_path)

            # PNG
            if suffix == ".png":
                output_path = output_path_dir / f"{input_path.stem}_compressed.png"

                compress_level = _map_strength_to_png_compress_level(strength)
                colors = _map_strength_to_png_colors(strength)

                if img.mode not in {"RGB", "RGBA", "P", "L"}:
                    img = img.convert("RGBA")

                if strength >= 35:
                    if img.mode == "RGBA":
                        img = img.convert("P", palette=Image.ADAPTIVE, colors=colors)
                    elif img.mode in {"RGB", "L"}:
                        img = img.convert("P", palette=Image.ADAPTIVE, colors=colors)

                img.save(
                    output_path,
                    format="PNG",
                    optimize=True,
                    compress_level=compress_level,
                )
                return True, str(output_path)

            # WEBP
            if suffix == ".webp":
                output_path = output_path_dir / f"{input_path.stem}_compressed.webp"

                if img.mode == "P":
                    img = img.convert("RGBA")

                img.save(
                    output_path,
                    format="WEBP",
                    quality=quality,
                    method=6,
                )
                return True, str(output_path)

            # BMP / TIFF / TIF
            # For v1, compress these by exporting to JPEG when possible,
            # or PNG if transparency is present.
            has_alpha = img.mode in {"RGBA", "LA"} or "transparency" in img.info

            if has_alpha:
                output_path = output_path_dir / f"{input_path.stem}_compressed.png"
                compress_level = _map_strength_to_png_compress_level(strength)

                if img.mode not in {"RGBA", "P"}:
                    img = img.convert("RGBA")

                img.save(
                    output_path,
                    format="PNG",
                    optimize=True,
                    compress_level=compress_level,
                )
                return True, str(output_path)

            output_path = output_path_dir / f"{input_path.stem}_compressed.jpg"

            if img.mode not in {"RGB", "L"}:
                img = img.convert("RGB")

            img.save(
                output_path,
                format="JPEG",
                quality=quality,
                optimize=True,
                progressive=True,
            )
            return True, str(output_path)

    except Exception as e:
        return False, f"Failed to compress {input_path.name}: {e}"


def compress_images(
    input_files: List[str],
    output_dir: str,
    strength: int,
) -> Tuple[bool, str]:
    if not input_files:
        return False, "No input files provided."

    success_count = 0
    failure_messages = []

    for input_file in input_files:
        ok, result = compress_single_image(input_file, output_dir, strength)

        if ok:
            success_count += 1
        else:
            failure_messages.append(result)

    if success_count == len(input_files):
        return True, f"Compressed {success_count} image(s) successfully."

    if success_count > 0:
        joined = "\n".join(failure_messages)
        return True, (
            f"Compressed {success_count} image(s), "
            f"but some files failed:\n{joined}"
        )

    joined = "\n".join(failure_messages)
    return False, joined or "Image compression failed."