#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
from pathlib import Path
from typing import List

import asyncio
from aiohttp import ClientSession


# https://pawelmhm.github.io/asyncio/python/aiohttp/2016/04/22/asyncio-aiohttp.html
async def fetch(filename: str, url: str, session: ClientSession) -> None:
    async with session.get(url) as response:
        data = await response.read()
        with open(filename, "wb") as f:
            f.write(data)


async def bound_fetch(
    sem: asyncio.Semaphore, filename: str, url: str, session: ClientSession
) -> None:
    async with sem:
        await fetch(filename, url, session)


async def execute_downloads(filenames: List[str], urls: List[str]) -> None:
    tasks = []
    sem = asyncio.Semaphore(10)
    async with ClientSession() as session:
        for fn, url in zip(filenames, urls):
            task = asyncio.ensure_future(bound_fetch(sem, fn, url, session))
            tasks.append(task)
        responses = asyncio.gather(*tasks)
        await responses


def download_files(filenames: List[str], urls: List[str]) -> None:
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(execute_downloads(filenames, urls))
    loop.run_until_complete(future)


def find_files(obj: dict) -> List[str]:
    try:
        keys = obj.keys()
    except AttributeError:
        # It's a list or a plain object
        if isinstance(obj, str):
            return []
        try:
            return [link for blob in obj for link in find_files(blob)]
        except TypeError:
            return []

    if "url_private_download" in keys:
        return [obj["url_private_download"]]

    return [link for k in keys for link in find_files(obj[k])]


def process_path(path: str) -> None:
    files: List[str] = []
    for name in Path(path).rglob("*.json"):
        with open(name, "r") as f:
            blob = json.load(f)
        files += find_files(blob)
    print(f"Found {len(files)} files")

    filenames = []
    for url in files:
        filenames.append(url.split("//")[-1].split("?")[0])
        os.makedirs(os.path.split(filenames[-1])[0], exist_ok=True)

    download_files(filenames, files)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: scrape.py /path/to/slack/export")
        sys.exit(0)

    for path in sys.argv[1:]:
        process_path(path)
