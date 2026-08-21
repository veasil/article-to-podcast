---
name: article-to-podcast
description: 把一篇文章（微信文章 / 网页 URL）转成「单人讲解」播客音频，并按「压缩效率」弹性决定时长（高信息密度可讲更久），发布到稳定公网地址、维护 RSS 订阅源。当用户发来文章链接并要「转成播客 / 变成可听的 / 解读 / 听书 / 生成音频」时使用。
---

# Article to Podcast

把文章转成 **单人讲解、忠于原文、压缩效率驱动时长** 的播客，并做系列性留存（稳定公网地址 + RSS）。

## 核心理念：压缩效率，而不是掐表

这个功能存在的意义是 **信息压缩带来的效率提升**：把一篇长文，压成用户吸收成本最低的形式（听 5 分钟 vs 读 30 分钟）。

因此**不设固定时长硬上限**，而是根据「压缩效率」弹性决定：

| 压缩效率 | 说明 | 时长倾向 |
|---|---|---|
| 高（信息密度高、原文有大量可压缩空间） | 长文、干货密集、每句话都值得保留 | 可讲 **6-12 分钟**，讲透 |
| 中 | 常规文章 | 4-6 分钟 |
| 低（原文本来就不长 / 内容稀疏） | 短文、公告、口水文 | 2-4 分钟，短平快 |

**时长决策不是先定再写，而是写完量一量**：先按信息完整性提炼口播稿，再测合成时长，只要时长与信息密度匹配（听众不会觉得拖沓或仓促）即可。

## 压缩效率评估（提炼前先打分）

在提炼口播稿前，先对原文做一次快速评估，输出到口播稿头部注释（不朗读）：

```
原文长度: X 字
口播稿长度: Y 字
压缩率: Y/X
信息密度: 高/中/低（原文干货浓度）
保留度: 按原文顺序保留了哪些核心论点（列出 2-4 个）
时长决策: 预计 X 分钟（依据：密度高且保留度高 → 可稍长）
```

## 何时用

用户发文章链接，想「听」这篇文章，或要「转成播客 / 解读 / 听书版」。

## 流程（按顺序执行）

### 第 1 步：抓取正文

```bash
python3 <skill>/scripts/fetch_article.py "<url>" --format text > /tmp/article.txt
```

- 若输出为空 / 报「正文提取失败」：说明目标站点是登录墙或 JS 渲染（如 x.com / 部分公众号）。
  按优先级尝试：
  1. **fxtwitter API**（X 长文/文章最稳，返回完整 JSON，含 article.content.blocks）：
     ```bash
     curl -s "https://api.fxtwitter.com/<user>/status/<id>" > /tmp/tweet.json
     # 用 Python 提取 article.content.blocks 的 text 拼接为正文
     ```
     vxtwitter（`api.vxtwitter.com`）是备选。
  2. `r.jina.ai`（普通网页/X 均可，但免费层会被 DDoS 保护临时封禁，封了换 1）：
     ```bash
     curl -sL "https://r.jina.ai/<url>" > /tmp/article.md
     ```
  3. nitter 镜像（大多已挂，只作最后尝试）。

读取 `/tmp/article.txt`（或对应文件），得到标题、作者、正文。

### 第 2 步：提炼口播稿（由你，即 LLM，完成）

1. 先按上面「压缩效率评估」打分。
2. 阅读正文，按 `references/prompt_compress.md` 的约束，产出**与压缩效率匹配**的单人讲解口播稿，写入 `/tmp/script.txt`。

要点：忠于原文核心信息、按原文顺序、复用原文关键句、口语化、不编造不评价。

### 第 3 步：合成音频

```bash
python3 <skill>/scripts/tts.py --file /tmp/script.txt \
    --out /workspace/podcast/<标题>.mp3 \
    --voice Cherry --rate +5%
```

- **默认引擎是阿里云 CosyVoice（qwen-tts）**，中文自然度高、有真实语气。API key 从环境变量 `DASHSCOPE_API_KEY` 或 `~/.config/article-podcast/dashscope.key` 读取。
- **自动回退**：没配置 key 或 CosyVoice 失败时，自动用 edge-tts（免费）。
- **音色**：CosyVoice 用 `Cherry`（女声·清亮，默认）/ `coffee`（男声·醇厚）/ `longxiaochun`（男声·沉稳）/ `longwan`（女声·温暖）。传 `zh-CN-*` 前缀（如 `zh-CN-XiaoxiaoNeural`）会切到 edge-tts。
- 输出 JSON 里的 `seconds` 就是时长。**校验逻辑：时长应与信息密度匹配**——
  - 密度高但被压到 2 分钟 → 说明过度压缩，回第 2 步补充内容；
  - 密度低却讲 8 分钟 → 说明注水，回第 2 步删减。
- 若用户明确要「5 分钟内」等硬性要求，才按用户要求限制时长。

### 第 4 步：发布到稳定公网地址

**推荐用 GitHub Pages（不要用 Release）**。Release 的音频链接会 302 跳转 + `application/octet-stream` + 签名过期，
Apple 播客会报 "can't be played"。Pages 直链是 200 + `audio/mp3` + 永久有效，播客 App 全兼容。

流程：
```bash
# 1. 启用 Pages（从 main 分支）
gh api -X POST repos/<owner>/<repo>/pages -f "source[branch]=main" -f "source[path]=/"

# 2. 把 mp3 提交到仓库 audio/ 目录（用 git，不用 gh api——api 传大文件会 "Argument list too long"）
#    先配置 git 凭据：gh auth setup-git
#    音频 URL = https://<owner>.github.io/<repo>/audio/<文件名>.mp3
```

- **`gh auth setup-git`** 是让 git push 走 token 认证的关键（否则 Windows 下 git push 卡凭据）。
- 若用户有自己的服务器 / OSS / NAS：跳过本步，改用用户提供的上传方式，拿到公网 URL 即可。
- **不要**用临时预览链接当最终地址——用户要的是系列性留存。

### 第 5 步：更新 RSS（系列性订阅）

```bash
python3 <skill>/scripts/make_rss.py \
    --title "<文章标题>" \
    --description "单人讲解 | <作者>" \
    --audio-url "$URL" \
    --seconds <时长秒数> \
    --date "$(date +%Y-%m-%d)" \
    --feed /workspace/podcast/podcast.xml
```

把 `podcast.xml` 托管到同一公网地址（提交到 GitHub 仓库根目录，Pages 直链）后，即可用任意播客 App（小宇宙 / Apple Podcasts / Audiobookshelf）订阅。

**Apple 播客必需的 RSS 标签**（缺失会导致校验失败/无法播放）：
- `<itunes:author>`、`<itunes:owner>`（含 name + email）
- `<itunes:category text="...">`、`<itunes:explicit>false</itunes:explicit>`
- `<itunes:image href="...">`（封面，须 http 直链，不能 302）
- 每条 item：`<itunes:duration>`、`<itunes:episodeType>full</itunes:episodeType>`
- `<pubDate>` 必须是 **RFC 822** 格式（如 `Sat, 22 Aug 2026 08:00:00 +0800`）

提交到仓库（用 git push；或 gh api 但需带 `sha`）：
```bash
gh repo clone <owner>/<repo> && cd <repo>
cp /workspace/podcast/podcast.xml ./podcast.xml
git add podcast.xml && git commit -m "update RSS" && git push origin main
```

### 第 6 步：回报 + 反馈闭环

返回：音频公网 URL、RSS 地址、时长、压缩效率评估（压缩率 + 保留度）。

**主动询问用户反馈**（这是设计的一部分，不是客套）：
- 这段讲解节奏合适吗？太快 / 太慢 / 太长 / 太短？
- 哪些地方讲多了 / 讲漏了？
- 你更喜欢长一点讲透，还是短一点精炼？

把反馈记录到本地 `feedback.md`（`<skill>/feedback.md`），作为下次决策的输入。用户持续的反馈，就是这个功能保持弹性的「调节旋钮」。

## 依赖

```bash
pip3 install edge-tts requests trafilatura beautifulsoup4
# ffmpeg 需可用（拼接音频 + CosyVoice wav→mp3 转码）
```

- **CosyVoice（默认 TTS）**：无需 pip 包，直接 HTTP 调 DashScope API。需配置 key（环境变量 `DASHSCOPE_API_KEY` 或 `~/.config/article-podcast/dashscope.key`）。
- **edge-tts（兜底）**：`pip3 install edge-tts`。

## 关键约束

- **弹性时长**：不设固定硬上限，以「压缩效率 / 信息密度」为准；用户有明确时长要求时以用户为准。
- 忠于原文：压缩而非改写，不添加原文没有的观点。
- 系列性留存：每次都要落到**稳定公网地址**并追加 RSS，不能只给临时链接。
- 持续反馈：每次运行回报后收集用户反馈，写入 feedback.md，反哺下次时长/详略决策。
