import os
from pathlib import Path
import sys
import platform
import shutil
import requests

from rich.progress import Progress

FFMPEG_URLS = {
    "windows": {
        "amd64": "https://github.com/eugeneware/ffmpeg-static/releases/download/b6.0/ffmpeg-win32-x64",
        "i686": "https://github.com/eugeneware/ffmpeg-static/releases/download/b6.0/ffmpeg-win32-ia32"
    }
}

FFPROBE_URLS = {
    "windows": {
        "amd64": "https://github.com/eugeneware/ffmpeg-static/releases/download/b6.0/ffprobe-win32-x64",
        "i686": "https://github.com/eugeneware/ffmpeg-static/releases/download/b6.0/ffprobe-win32-ia32",
    }
}


def is_ffprobe_installed(ffprobe: str = "ffprobe") -> bool:

    if ffprobe == "ffprobe":
        global_ffprobe = shutil.which("ffprobe")
        if global_ffprobe is None:
            ffprobe_path = get_ffprobe_path()
        else:
            ffprobe_path = Path(global_ffprobe)
    else:
        ffprobe_path = Path(ffprobe)

    if ffprobe_path is None:
        return False

    # else check if path to ffprobe is valid
    # and if ffprobe has the correct access rights
    return ffprobe_path.exists() and os.access(ffprobe_path, os.X_OK)

def get_local_ffprobe():

    ffmpeg_path = Path(
        "ffprobe" + (".exe" if platform.system() == "Windows" else "")
    )

    if ffmpeg_path.is_file():
        return ffmpeg_path

    return None


def get_ffprobe_path():

    # Check if ffprobe is installed
    global_ffprobe = shutil.which("ffprobe")
    if global_ffprobe:
        return Path(global_ffprobe)

    # Get local ffprobe path
    return get_local_ffprobe()

def download_ffmpeg() -> Path:

    os_name = "windows"
    os_arch = platform.machine().lower()
    ffmpeg_url: str = None

    ffmpeg_url = FFMPEG_URLS.get(os_name, {}).get(os_arch)

    if ffmpeg_url is None:
        raise ValueError("FFmpeg binary is not available for your system.")

    ffmpeg_path = Path(
        os.path.join(
            "ffmpeg" + ".exe"
        )
    )

    # Download binary and save it to a file in spotdl directory
    response = requests.get(ffmpeg_url, stream=True, allow_redirects=True, timeout=10)
    total_size_in_bytes = int(response.headers.get('content-length', 0))
    block_size = 1024  # 1 Kibibyte

    with Progress() as progress:
        task_id = progress.add_task("[cyan]Downloading...", total=total_size_in_bytes)

        with open(ffmpeg_path, "wb") as ffmpeg_file:
            for data in response.iter_content(block_size):
                ffmpeg_file.write(data)
                progress.update(task_id, advance=len(data))

    return ffmpeg_path

def download_ffprobe() -> Path:

    os_name = "windows"
    os_arch = platform.machine().lower()
    ffprobe_url: str = None

    ffprobe_url = FFPROBE_URLS.get(os_name, {}).get(os_arch)

    if ffprobe_url is None:
        raise ValueError("FFmpeg binary is not available for your system.")

    ffprobe_path = Path(
        os.path.join(
            "ffmprobe" + ".exe"
        )
    )

    # Download binary and save it to a file in spotdl directory
    response = requests.get(ffprobe_url, stream=True, allow_redirects=True, timeout=10)
    total_size_in_bytes = int(response.headers.get('content-length', 0))
    block_size = 1024  # 1 Kibibyte

    with Progress() as progress:
        task_id = progress.add_task("[cyan]Downloading...", total=total_size_in_bytes)

        with open(ffprobe_path, "wb") as ffprobe_file:
            for data in response.iter_content(block_size):
                ffprobe_file.write(data)
                progress.update(task_id, advance=len(data))

    return ffprobe_path
