#!/usr/bin/env python3
"""Pre-download checksum-pinned Conan sources and rewrite them to file URLs."""

import argparse
import hashlib
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
import yaml


def source_nodes(value):
    if isinstance(value, dict):
        urls = value.get("url")
        if isinstance(urls, str) or (
            isinstance(urls, list)
            and urls
            and all(isinstance(url, str) for url in urls)
        ):
            yield value
        for child in value.values():
            yield from source_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from source_nodes(child)


def mirror_urls(url):
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lstrip("/")

    if host == "github.com" or host.endswith(".githubusercontent.com"):
        return [f"https://gh-proxy.com/{url}", url]
    if host == "ftpmirror.gnu.org":
        return [
            f"https://mirrors.tuna.tsinghua.edu.cn/{path}",
            f"https://mirrors.ustc.edu.cn/{path}",
            f"https://mirrors.aliyun.com/{path}",
            url,
        ]
    if host == "download.gnome.org":
        return [
            f"https://mirrors.ustc.edu.cn/gnome/{path}",
            f"https://mirrors.tuna.tsinghua.edu.cn/gnome/{path}",
            f"https://mirror.nju.edu.cn/gnome/{path}",
            url,
        ]
    if host == "cdn.kernel.org":
        return [
            f"https://mirrors.ustc.edu.cn/kernel.org/{path}",
            f"https://mirrors.tuna.tsinghua.edu.cn/{path}",
            url,
        ]
    return [url]


def candidate_urls(value):
    urls = [value] if isinstance(value, str) else value
    candidates = []
    for url in urls:
        for candidate in mirror_urls(url):
            if candidate not in candidates:
                candidates.append(candidate)
    return candidates


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cache_path(cache_dir, urls, sha256):
    first_path = unquote(urlparse(urls[0]).path)
    filename = Path(first_path).name or f"source-{sha256[:12]}"
    filename = re.sub(r"[^A-Za-z0-9._+-]", "_", filename)
    return cache_dir / f"{sha256[:16]}-{filename}"


def download(url, destination):
    try:
        with requests.get(url, stream=True, timeout=(20, 60)) as response:
            status = str(response.status_code)
            response.raise_for_status()
            with destination.open("wb") as target:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        target.write(chunk)
        return True, status, ""
    except (OSError, requests.RequestException) as exc:
        return False, "", str(exc)


def predownload(document, cache_dir):
    nodes = list(source_nodes(document))
    rewritten = 0
    print(f"  found {len(nodes)} checksum-pinned source entr{'y' if len(nodes) == 1 else 'ies'}")

    for node in nodes:
        expected = str(node.get("sha256", "")).lower()
        urls = candidate_urls(node["url"])
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            print(f"  [warn] skipping source without a valid sha256: {urls[0]}")
            continue

        destination = cache_path(cache_dir, urls, expected)
        if destination.is_file() and file_sha256(destination) == expected:
            print(f"  [cached] {destination.name}")
            node["url"] = destination.resolve().as_uri()
            rewritten += 1
            continue

        destination.unlink(missing_ok=True)
        for index, url in enumerate(urls, start=1):
            print(f"  [try {index}/{len(urls)}] {url[:100]}")
            ok, status, error = download(url, destination)

            actual = file_sha256(destination) if destination.is_file() else ""
            if ok and actual == expected:
                print(f"  [ok] {destination.name} sha256={actual}")
                node["url"] = destination.resolve().as_uri()
                rewritten += 1
                break

            destination.unlink(missing_ok=True)
            detail = f"http={status}" if status else error[:120]
            if actual and actual != expected:
                detail = f"sha256 mismatch: {actual}"
            print(f"  [fail] {detail}")
        else:
            print("  [warn] pre-download failed; Conan will use the original URL list")

    return rewritten


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("conandata", type=Path)
    parser.add_argument("cache_dir", type=Path)
    args = parser.parse_args()

    args.cache_dir.mkdir(parents=True, exist_ok=True)
    with args.conandata.open("r", encoding="utf-8") as source:
        document = yaml.safe_load(source) or {}

    rewritten = predownload(document, args.cache_dir)
    if rewritten:
        with args.conandata.open("w", encoding="utf-8", newline="\n") as target:
            yaml.safe_dump(document, target, sort_keys=False, allow_unicode=True)
    print(f"  [done] pre-downloaded {rewritten} source entr{'y' if rewritten == 1 else 'ies'}")


if __name__ == "__main__":
    main()
