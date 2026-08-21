#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把口播稿文本合成为单段 mp3，并输出时长。

引擎策略（双引擎）:
1. 优先用 阿里云 DashScope CosyVoice（qwen-tts 模型，中文自然度高）。
   需要环境变量 DASHSCOPE_API_KEY（或文件 ~/.config/article-podcast/dashscope.key）。
2. 没配置 key / 调用失败时，自动回退到 edge-tts（免费、无需 key）。

用法:
    python3 tts.py --file 口播稿.txt --out out.mp3 [--voice Cherry] [--rate +5%]
    python3 tts.py --text "口播稿" --out out.mp3

--voice 语义:
    CosyVoice 模式下: Cherry / coffee / longxiaochun / longwan / longxiaoxia ...
    edge-tts 模式下:  zh-CN-YunxiNeural 等
    （不传时默认 Cherry；若传了 zh-CN-* 前缀会自动切 edge-tts 音色）

返回: JSON {"path": "...", "seconds": 298.5, "size_kb": 4200, "engine": "cosyvoice|edge-tts"}
"""
import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

DEFAULT_VOICE = "Cherry"
DASHSCOPE_ENDPOINT = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
KEY_FILE = os.path.expanduser("~/.config/article-podcast/dashscope.key")


def _get_api_key():
    k = os.environ.get("DASHSCOPE_API_KEY")
    if k:
        return k.strip()
    try:
        with open(KEY_FILE, encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return None


def _clean_title_for_filename(s):
    return re.sub(r"[^\w\u4e00-\u9fff]+", "_", s)[:40]


# ---------------- CosyVoice (DashScope qwen-tts) ----------------

def cosy_synth(text, voice, out_path, retries=3):
    api_key = _get_api_key()
    if not api_key:
        return False
    payload = json.dumps({
        "model": "qwen-tts",
        "input": {"text": text},
        "parameters": {"voice": voice, "response_format": "mp3"},
    }).encode("utf-8")
    import time
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                DASHSCOPE_ENDPOINT, data=payload,
                headers={"Authorization": f"Bearer {api_key}",
                         "Content-Type": "application/json"},
                method="POST")
            resp = json.loads(urllib.request.urlopen(req, timeout=90).read())
            url = resp["output"]["audio"]["url"]
            # CosyVoice 实际返回 wav（即使请求 mp3），下载为原始文件
            raw_path = out_path + ".raw"
            urllib.request.urlretrieve(url, raw_path)
            if os.path.getsize(raw_path) == 0:
                os.remove(raw_path)
                continue
            # 统一转成标准 mp3（保证 concat 时编码一致）
            subprocess.run(
                ["ffmpeg", "-y", "-i", raw_path, "-codec:a", "libmp3lame",
                 "-qscale:a", "4", out_path],
                check=True, capture_output=True)
            os.remove(raw_path)
            if os.path.getsize(out_path) > 0:
                return True
        except Exception:
            pass
        time.sleep(2 * (attempt + 1))
    return False


# ---------------- edge-tts (免费兜底) ----------------

def _edge_synth_once(text, voice, rate, out_path):
    """单次 edge-tts 合成（内部跑 asyncio）。"""
    import edge_tts

    async def _run():
        c = edge_tts.Communicate(text, voice, rate=rate)
        with open(out_path, "wb") as f:
            async for chunk in c.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
    asyncio.run(_run())
    return os.path.getsize(out_path) > 0


def _edge_synth_sync(text, voice, rate, out_path, retries=6):
    import time
    for attempt in range(retries):
        try:
            if _edge_synth_once(text, voice, rate, out_path):
                return True
        except Exception:
            pass
        time.sleep(1.5 * (attempt + 1))
    return False


# ---------------- 分段与拼接 ----------------

def split_text(script, limit=400):
    parts = script.split("\n")
    chunks, buf = [], ""
    for p in parts:
        if buf and len(buf) + len(p) + 1 > limit:
            chunks.append(buf)
            buf = p
        else:
            buf = (buf + "\n" + p) if buf else p
    if buf:
        chunks.append(buf)
    return chunks


def duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True)
    return float(r.stdout.strip())


def concat(segs, out_path):
    tmp = os.path.dirname(segs[0])
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as f:
        for s in segs:
            f.write(f"file '{s}'\n")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", lst, "-c", "copy", out_path],
                   check=True, capture_output=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default=None)
    ap.add_argument("--file", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--voice", default=DEFAULT_VOICE)
    ap.add_argument("--rate", default="+5%")
    ap.add_argument("--engine", default="auto",
                    help="auto|cosyvoice|edge-tts")
    args = ap.parse_args()

    if args.file:
        text = open(args.file, encoding="utf-8").read()
    elif args.text:
        text = args.text
    else:
        raise SystemExit("需要 --text 或 --file")

    # 决定引擎
    use_cosy = (args.engine != "edge-tts") and not args.voice.startswith("zh-CN-")
    if use_cosy and not _get_api_key():
        use_cosy = False

    chunks = split_text(text)
    tmp = tempfile.mkdtemp()
    segs = []
    engine_used = ""

    if use_cosy:
        voice = args.voice if not args.voice.startswith("zh-CN-") else DEFAULT_VOICE
        for i, ch in enumerate(chunks):
            p = os.path.join(tmp, f"seg_{i:03d}.mp3")
            ok = cosy_synth(ch, voice, p)
            if not ok:
                print(f"[warn] CosyVoice 段 {i+1} 失败，回退 edge-tts", file=sys.stderr)
                use_cosy = False
                engine_used = "edge-tts"
                break
            segs.append(p)
        if use_cosy:
            engine_used = "cosyvoice"
    if not use_cosy:
        voice = args.voice if args.voice.startswith("zh-CN-") else "zh-CN-YunxiNeural"
        for i, ch in enumerate(chunks):
            p = os.path.join(tmp, f"seg_{i:03d}.mp3")
            ok = _edge_synth_sync(ch, voice, args.rate, p)
            if not ok:
                raise SystemExit(f"段 {i+1}/{len(chunks)} 合成失败")
            segs.append(p)
        if not engine_used:
            engine_used = "edge-tts"

    concat(segs, args.out)
    secs = duration(args.out)
    size_kb = os.path.getsize(args.out) // 1024
    print(json.dumps({"path": args.out, "seconds": round(secs, 1),
                      "size_kb": size_kb, "engine": engine_used},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
