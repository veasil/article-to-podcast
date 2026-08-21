#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""维护一个播客 RSS feed（podcast.xml），追加新一集。

用法:
    python3 make_rss.py \
        --title "福島真人：Scaling 规模化（2018）" \
        --description "5分钟单人讲解" \
        --audio-url "https://你的域名/audio/xxx.mp3" \
        --seconds 298 \
        --date "2026-08-22" \
        --feed /workspace/podcast/podcast.xml

若 --feed 不存在则自动创建 channel；已存在则把新 episode 插入到最前。
"""
import argparse
import os
import re
import xml.sax.saxutils as su


def build_channel(feed_title, feed_desc, feed_link):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>{su.escape(feed_title)}</title>
    <link>{su.escape(feed_link)}</link>
    <description>{su.escape(feed_desc)}</description>
    <language>zh-cn</language>
  </channel>
</rss>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--description", default="")
    ap.add_argument("--audio-url", required=True)
    ap.add_argument("--seconds", type=int, default=300)
    ap.add_argument("--date", required=True)
    ap.add_argument("--feed", required=True)
    ap.add_argument("--feed-title", default="我的文章播客")
    ap.add_argument("--feed-link", default="")
    args = ap.parse_args()

    mm, ss = divmod(args.seconds, 60)
    dur = f"{mm:02d}:{ss:02d}"

    item = f"""    <item>
      <title>{su.escape(args.title)}</title>
      <description>{su.escape(args.description)}</description>
      <enclosure url="{su.escape(args.audio_url)}" type="audio/mpeg" />
      <guid isPermaLink="false">{re.sub(r'[^a-zA-Z0-9]+', '-', args.title)[:60]}-{args.date}</guid>
      <pubDate>{args.date} 08:00:00 +0800</pubDate>
      <itunes:duration>{dur}</itunes:duration>
    </item>
"""

    if not os.path.exists(args.feed):
        xml = build_channel(args.feed_title, "把文章自动转成 5 分钟单人讲解播客",
                            args.feed_link or args.audio_url)
    else:
        xml = open(args.feed, encoding="utf-8").read()

    # 把新 item 插到 </channel> 之前（即列表最前）
    if "</channel>" in xml:
        xml = xml.replace("</channel>", item + "  </channel>")
    else:
        xml = xml.replace("</rss>", item + "</rss>")

    os.makedirs(os.path.dirname(os.path.abspath(args.feed)), exist_ok=True)
    with open(args.feed, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"已更新 {args.feed}（新一集：{args.title}）")


if __name__ == "__main__":
    main()
