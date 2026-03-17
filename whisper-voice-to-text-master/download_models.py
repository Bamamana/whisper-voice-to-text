#!/usr/bin/env python3
import argparse
from pathlib import Path

from faster_whisper.utils import download_model

DEFAULT_MODELS = ["tiny", "base", "small", "medium", "large-v3"]


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
        download_model(model_name, output_dir=str(cache_dir), cache_dir=str(cache_dir))

    print("Done. Models are ready.")


if __name__ == "__main__":
    main()
