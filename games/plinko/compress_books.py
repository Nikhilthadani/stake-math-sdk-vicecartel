"""Convert uncompressed Plinko books (.json) to Stake Engine format (.jsonl.zst).

Reads the giant JSON array files one object at a time using streaming,
writes compressed JSONL. No need to re-run the 2-hour simulation.

Usage (from SDK root):
    python games/plinko/compress_books.py
"""

import os
import sys
import json
import time
import zstandard as zstd

SDK_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, SDK_ROOT)

BOOKS_DIR = os.path.join(SDK_ROOT, "games", "plinko", "library", "books")
COMPRESSED_DIR = os.path.join(SDK_ROOT, "games", "plinko", "library", "books_compressed")
PUBLISH_DIR = os.path.join(SDK_ROOT, "games", "plinko", "library", "publish_files")

ROWS = [8, 10, 12, 14, 16]
RISKS = ["low", "medium", "high"]


def stream_json_array(filepath):
    """Stream objects from a JSON array file without loading it all into memory.

    The books are written as: [{...}, {...}, ...]
    We use a simple incremental JSON decoder.
    """
    decoder = json.JSONDecoder()
    with open(filepath, "r", encoding="utf-8") as f:
        buf = ""
        in_array = False
        count = 0

        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            buf += chunk

            while buf:
                buf = buf.lstrip()
                if not buf:
                    break

                if not in_array:
                    if buf[0] == "[":
                        buf = buf[1:]
                        in_array = True
                        continue
                    else:
                        break

                if buf[0] == "]":
                    return

                if buf[0] == ",":
                    buf = buf[1:]
                    continue

                try:
                    obj, idx = decoder.raw_decode(buf)
                    buf = buf[idx:]
                    count += 1
                    yield obj
                except json.JSONDecodeError:
                    break


def compress_book(mode):
    """Convert one book file from JSON array to .jsonl.zst."""
    src = os.path.join(BOOKS_DIR, f"books_{mode}.json")
    if not os.path.exists(src):
        print(f"  SKIP {mode} — source not found")
        return False

    dst_compressed = os.path.join(COMPRESSED_DIR, f"books_{mode}.jsonl.zst")
    dst_publish = os.path.join(PUBLISH_DIR, f"books_{mode}.jsonl.zst")

    src_size_gb = os.path.getsize(src) / (1024 ** 3)
    print(f"  {mode}: {src_size_gb:.2f} GB -> ", end="", flush=True)

    cctx = zstd.ZstdCompressor(level=3, threads=4)
    count = 0
    start = time.time()

    with open(dst_compressed, "wb") as out_f:
        with cctx.stream_writer(out_f) as writer:
            for obj in stream_json_array(src):
                line = json.dumps(obj, separators=(",", ":")) + "\n"
                writer.write(line.encode("utf-8"))
                count += 1
                if count % 1_000_000 == 0:
                    print(f"{count // 1_000_000}M..", end="", flush=True)

    elapsed = time.time() - start
    dst_size_mb = os.path.getsize(dst_compressed) / (1024 ** 2)
    ratio = (src_size_gb * 1024) / dst_size_mb if dst_size_mb > 0 else 0

    # Copy to publish dir
    import shutil
    shutil.copy2(dst_compressed, dst_publish)

    print(f" {dst_size_mb:.1f} MB ({ratio:.0f}x) in {elapsed:.0f}s [{count:,} sims]")
    return True


if __name__ == "__main__":
    os.makedirs(COMPRESSED_DIR, exist_ok=True)
    os.makedirs(PUBLISH_DIR, exist_ok=True)

    print("Converting Plinko books to .jsonl.zst format\n")
    print(f"  Source:      {BOOKS_DIR}")
    print(f"  Compressed:  {COMPRESSED_DIR}")
    print(f"  Publish:     {PUBLISH_DIR}")
    print()

    ok = 0
    for rows in ROWS:
        for risk in RISKS:
            mode = f"{rows}_{risk}"
            if compress_book(mode):
                ok += 1

    print(f"\nDone. {ok}/15 books compressed.")
    print("Files ready in: games/plinko/library/publish_files/")
