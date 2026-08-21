#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓取文章 URL，提取标题 / 作者 / 正文（支持微信文章与普通网页）。

用法:
    python3 fetch_article.py <url> [--format json|text]

输出:
    json: {"title": "...", "author": "...", "content": "...", "chars": 1234}
    text: 标题\n作者\n\n正文（供 agent 直接阅读提炼）
"""
import json
import re
import sys

from bs4 import BeautifulSoup

try:
    import requests
except ImportError:
    requests = None
import trafilatura

WECHAT_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
             "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
             "MicroMessenger/8.0.38")

NOISE_PATTERNS = [
    r"点在看", r"小鱼干", r"在看", r"点赞", r"扫码", r"二维码",
    r"阅读原文", r"点击关注", r"关注我们", r"长按识别", r"星标",
    r"设为星标", r"更多精彩", r"往期", r"点击上方", r"蓝字",
]


def _clean(line):
    line = re.sub(r"\s+", " ", line).strip()
    return line.replace("\u30fb", " ").replace("・", " ")


def _is_noise(line):
    if not line:
        return True
    if re.fullmatch(r"[\d\s\.\-—–]+", line):
        return True
    if len(line) <= 1:
        return True
    for p in NOISE_PATTERNS:
        if re.search(p, line):
            return True
    return False


def extract_wechat(url):
    if requests is None:
        raise SystemExit("缺少 requests 库")
    html = requests.get(url, headers={"User-Agent": WECHAT_UA}, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")
    t = soup.find("meta", property="og:title")
    title = t.get("content") if t else "未命名文章"
    a = soup.find("meta", property="og:article:author")
    author = a.get("content") if a else ""
    content = soup.find(id="js_content")
    if not content:
        raise SystemExit("未找到正文（js_content），文章可能已删除或需登录")
    raw = str(content)
    raw = re.sub(r"<br\s*/?>", "\n", raw)
    raw = re.sub(r"</(p|div|section|h[1-6]|li|blockquote|ul|ol|tr)>", "\n", raw)
    text = re.sub(r"<[^>]+>", "", raw)
    for x, y in [("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"),
                 ("&gt;", ">"), ("&#39;", "'"), ("&quot;", '"')]:
        text = text.replace(x, y)
    paras = [_clean(l) for l in text.split("\n")]
    paras = [l for l in paras if not _is_noise(l)]
    return title, author, "\n".join(paras)


def extract_generic(url):
    downloaded = trafilatura.fetch_url(url)
    text = trafilatura.extract(downloaded, include_comments=False,
                               include_tables=False)
    if not text:
        raise SystemExit("正文提取失败")
    title = url.rstrip("/").split("/")[-1] or "文章"
    paras = [_clean(l) for l in text.split("\n")]
    paras = [l for l in paras if not _is_noise(l)]
    return title, "", "\n".join(paras)


def main():
    if len(sys.argv) < 2:
        raise SystemExit("用法: python3 fetch_article.py <url> [--format json|text]")
    url = sys.argv[1]
    fmt = "json"
    if "--format" in sys.argv:
        fmt = sys.argv[sys.argv.index("--format") + 1]

    if "mp.weixin.qq.com" in url:
        title, author, content = extract_wechat(url)
    else:
        title, author, content = extract_generic(url)

    if fmt == "text":
        head = f"{title}\n{author}\n\n" if author else f"{title}\n\n"
        sys.stdout.write(head + content)
    else:
        sys.stdout.write(json.dumps({
            "title": title, "author": author, "content": content,
            "chars": len(content),
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
