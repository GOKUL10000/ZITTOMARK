"""One-time model acquisition. The voice application never runs this script."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request

APP = Path(__file__).resolve().parent
from runtime_paths import RUNTIME

def digest(file):
    h = hashlib.sha256()
    with file.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def acquire(item):
    dest = RUNTIME / "models" / item["folder"] / item["file"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    expected = item.get("sha256")
    if dest.exists() and dest.stat().st_size == item["size"]:
        if not expected or digest(dest) == expected:
            print("Verified existing:", item["file"], flush=True)
            return
    partial = dest.with_name(dest.name + ".partial")
    url = f'https://huggingface.co/{item["repo"]}/resolve/{item["revision"]}/{item["file"]}?download=true'
    for attempt in range(4):
        try:
            offset = partial.stat().st_size if partial.exists() else 0
            headers = {"User-Agent": "LocalVoiceStudio-Setup/1"}
            if offset:
                headers["Range"] = f"bytes={offset}-"
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as response:
                append = offset > 0 and response.status == 206
                with partial.open("ab" if append else "wb") as out:
                    while block := response.read(4 * 1024 * 1024):
                        out.write(block)
            if partial.stat().st_size != item["size"]:
                raise RuntimeError("Incomplete model download")
            if expected and digest(partial) != expected:
                partial.unlink()
                raise RuntimeError("Model checksum mismatch")
            os.replace(partial, dest)
            print("Downloaded and verified:", item["file"], flush=True)
            return
        except Exception as error:
            print(f'Retry {attempt + 1}: {item["file"]}: {error}', flush=True)
            time.sleep(2)
    raise RuntimeError(f'Could not download {item["file"]}')

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Download pinned local speech models; this is the explicit online setup step.')
    parser.add_argument('--creative', action='store_true', help='Also download the optional English VoiceDesign model.')
    args = parser.parse_args()
    manifest = json.loads((APP / "model-manifest.json").read_text(encoding="utf-8-sig"))
    if args.creative:
        manifest += json.loads((APP / 'creative-model-manifest.json').read_text(encoding='utf-8'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(acquire, manifest))
    print("All offline voice models are present and verified.", flush=True)
