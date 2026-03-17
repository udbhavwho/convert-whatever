from pathlib import Path


FILE_TYPE_GROUPS = {
    "video": {
        ".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".m4v"
    },
    "audio": {
        ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".opus"
    },
    "image": {
        ".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff", ".tif"
    },
    "gif": {
        ".gif"
    },
    "document": {
        ".pdf", ".docx", ".txt", ".md", ".odt"
    },
}


OPERATIONS_BY_FAMILY = {
    "video": [
        "Convert Format",
        "Convert to Audio",
        "Convert to GIF",
        "Extract Frames",
        "Compress",
    ],
    "audio": [
        "Convert Format",
        "Compress",
    ],
    "image": [
        "Convert Format",
        "Compress",
    ],
    "gif": [
        "Convert to Video",
        "Extract Frames",
        "Compress",
    ],
    "document": [
        "Convert Format",
        "Compress",
    ],
}


def detect_file_family(file_path: str) -> str | None:
    suffix = Path(file_path).suffix.lower()

    for family, extensions in FILE_TYPE_GROUPS.items():
        if suffix in extensions:
            return family

    return None


def validate_same_family(file_paths: list[str]) -> tuple[bool, str]:
    """
    Returns:
        (True, family_name) if all files belong to the same supported family
        (False, error_message) otherwise
    """
    if not file_paths:
        return False, "No files selected."

    first_family = detect_file_family(file_paths[0])

    if first_family is None:
        return False, "Unidentified type"

    for file_path in file_paths[1:]:
        current_family = detect_file_family(file_path)

        if current_family is None:
            return False, "Unidentified type"

        if current_family != first_family:
            return False, (
                f"Mixed file types detected. "
                f"Only '{first_family}' files can be selected together."
            )

    return True, first_family


def get_operations_for_family(family: str) -> list[str]:
    return OPERATIONS_BY_FAMILY.get(family, [])