# Article to Podcast · 文章转播客

把网页文章转成单人讲解音频，再通过独立托管仓库留存和分发。时长由信息密度与保留内容决定，不预设固定五分钟。

本仓库提供 **Agent 工作流说明与 Python 脚本**。文章提炼由使用者或 Agent 完成；脚本分别负责正文提取、语音合成与 RSS 更新。

## 工作流

文章 URL → 提取正文 → 人工或 Agent 提炼口播稿 → 合成 MP3 → 审听 → 发布音频与 RSS。

详细步骤见 [SKILL.md](SKILL.md)，提炼约束见 [口播稿提示](references/prompt_compress.md)。

## 本地准备

需要 Python，以及能在终端调用的 `ffmpeg` 和 `ffprobe`。语音合成需要网络连接。

```bash
python -m pip install requests trafilatura beautifulsoup4 edge-tts
```

## 最小使用流程

在仓库根目录执行：

```bash
python scripts/fetch_article.py "https://example.com/article" --format text
```

核对提取结果，再按原文逻辑编写 UTF-8 文件 `script.txt`。保留核心论点及来源，不添加原文没有的结论。需要登录或依赖动态渲染的网页可能无法直接提取。

使用 edge-tts 合成，不需要配置 DashScope 密钥：

```bash
python scripts/tts.py --file script.txt --out episode.mp3 --engine edge-tts --voice zh-CN-YunxiNeural
```

脚本返回音频路径、秒数、文件大小及实际引擎。发布前审听，检查人名、数字、断句与内容保留度。

默认 `auto` 模式会尝试当前脚本配置的 DashScope `qwen-tts`，需要 `DASHSCOPE_API_KEY`；缺少密钥或合成失败时回退 edge-tts。密钥也可由本机 `~/.config/article-podcast/dashscope.key` 读取，不应提交到仓库。具体引擎行为以 [tts.py](scripts/tts.py) 为准。

## RSS 与发布

[make_rss.py](scripts/make_rss.py) 根据音频公网 URL、实际时长和节目元信息更新 feed；[publish_github.sh](scripts/publish_github.sh) 是仓库内的发布辅助脚本。启用 Pages、提交音频和发布 feed 会改变公开内容，执行前应核对目标仓库与文件。

当前 RSS 生成器属于早期实现：日期字符串未转换为 RFC 822，未自动补齐完整频道元信息，重复执行也不会按 episode 去重。上线前需要检查或修正这些字段，不能仅凭 XML 写入成功判断播客客户端兼容。

一个现有托管实例是 [podcast-host](https://github.com/veasil/podcast-host)：生成工具和节目资产分别维护。

## 目录

| 路径 | 用途 |
| --- | --- |
| [SKILL.md](SKILL.md) | Agent 的完整操作流程 |
| [scripts/fetch_article.py](scripts/fetch_article.py) | 正文提取 |
| [scripts/tts.py](scripts/tts.py) | 分段语音合成与 MP3 拼接 |
| [scripts/make_rss.py](scripts/make_rss.py) | RSS 条目生成 |
| [references/prompt_compress.md](references/prompt_compress.md) | 口播稿提炼约束 |
| [feedback.md](feedback.md) | 节奏与详略反馈记录 |

## 当前边界

这是脚本与工作流仓库，尚无一条命令完成所有步骤的流水线。本文命令已与脚本参数核对，未代表已完成真实语音服务或播客客户端的端到端验证。分享问题时请附执行命令、运行环境和脱敏错误信息。
