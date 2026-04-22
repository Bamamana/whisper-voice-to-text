#!/usr/bin/env python3
import argparse
import os
import sys
import time
from pathlib import Path

from faster_whisper.utils import _MODELS
from huggingface_hub import snapshot_download
from tqdm.auto import tqdm

DEFAULT_MODELS = ["tiny", "base", "small", "medium", "large-v3"]
ALLOW_PATTERNS = [
    "config.json",
    "preprocessor_config.json",
    "model.bin",
    "tokenizer.json",
    "vocabulary.*",
]


def _format_size(num_bytes: float) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    value = float(num_bytes)
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} TiB"


class InstallerProgressTqdm(tqdm):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("disable", False)
        kwargs.setdefault("file", sys.stdout)
        kwargs.setdefault("leave", True)
        super().__init__(*args, **kwargs)
        self._last_emit_time = 0.0
        self._last_emit_percent = -1
        self._last_message = ""

    def display(self, msg=None, pos=None):
        if self.disable:
            return

        now = time.monotonic()
        percent = int((self.n / self.total) * 100) if self.total else None
        should_emit = (
            self.n == 0
            or self.total is not None and self.n >= self.total
            or percent is not None and percent >= self._last_emit_percent + 5
            or now - self._last_emit_time >= 8.0
        )
        if not should_emit:
            return

        rate = self.format_dict.get("rate") or 0.0
        if self.total:
            message = (
                f"[progress] {self.desc}: {self.n / self.total * 100:5.1f}% "
                f"({_format_size(self.n)} / {_format_size(self.total)}) at {_format_size(rate)}/s"
            )
        else:
            message = f"[progress] {self.desc}: {_format_size(self.n)} at {_format_size(rate)}/s"

        if message == self._last_message:
            return

        self.fp.write(message + "\n")
        self.fp.flush()
        self._last_message = message
        self._last_emit_time = now
        if percent is not None:
            self._last_emit_percent = percent


def download_model_with_progress(model_name: str, cache_dir: Path) -> str:
    repo_id = model_name if "/" in model_name else _MODELS.get(model_name)
    if repo_id is None:
        raise ValueError(f"Invalid model size '{model_name}', expected one of: {', '.join(sorted(_MODELS.keys()))}")

    kwargs = {
        "allow_patterns": ALLOW_PATTERNS,
        "cache_dir": str(cache_dir),
        "local_dir": str(cache_dir),
        "tqdm_class": InstallerProgressTqdm,
    }

    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    if hf_token:
        kwargs["token"] = hf_token

    return snapshot_download(repo_id, **kwargs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-download Whisper models for offline/fast switching.")
    parser.add_argument(
        "models",
        nargs="*",
        default=DEFAULT_MODELS,
        help="Models to download (default: tiny base small medium large-v3)",
    )
    parser.add_argument(
        "--cache-dir",
        default=str(Path(__file__).resolve().parent / "model-cache"),
        help="Directory to store downloaded models",
    )
    args = parser.parse_args()

    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    for model_name in args.models:
        print(f"[download] {model_name} -> {cache_dir}")
        download_model_with_progress(model_name, cache_dir)
        print(f"[download] {model_name} complete")

    print("Done. Models are ready.")


if __name__ == "__main__":
    main()
