# B站音频下载器 (bilibili-audio-downloader)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个基于 `yt-dlp` + `ffmpeg` 的 tkinter 图形界面工具，用于下载 B 站视频的音频并转码成 MP3。

A Python/Tkinter-based GUI tool that downloads the audio track from Bilibili videos and converts it to MP3, built on `yt-dlp` + `ffmpeg`.

## 功能特点 / Features

- **视频信息预览**：粘贴链接后获取标题、UP主、时长与封面图，确认无误再下载。

- **多档码率**：可选原始质量（不转码，保留 m4a/flac）或 MP3 128k / 192k / 320k。

- **合集多 P 支持**：自动按「序号 - 标题」命名，避免合集内同名视频互相覆盖。

- **进度与日志**：实时进度条与日志输出；多 P 切换时进度自动重置，已存在的文件自动跳过。

- **单文件打包**：可用 PyInstaller 打包成独立可执行程序。

- **Video info preview**: Fetch title, uploader, duration and cover image after pasting a link.

- **Bitrate options**: Keep the original quality (no re-encode, preserves m4a/flac) or convert to MP3 128k / 192k / 320k.

- **Multi-part support**: Names files as "index - title" so same-named videos in a collection don't overwrite each other.

- **Progress and logs**: Live progress bar and log output; progress resets between parts, existing files are skipped.

- **Single-file build**: Can be packaged into a standalone executable with PyInstaller.

---

## 依赖 / Dependencies

| 组件 | 说明 |
| --- | --- |
| Python 3.8+ | 仅用标准库，无需 `pip install` 任何包 |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp/releases) | 实际下载，必须安装并在 `PATH` 中 |
| ffmpeg | 转码与封面缩略图处理 |

```bash
# Ubuntu / Debian
sudo apt install ffmpeg
pip install -U yt-dlp
```

程序启动时会检查 `yt-dlp` 是否可用，缺失会直接提示。

The app checks for `yt-dlp` on startup and warns if it's missing.

---

## 使用指南 / How to Use

### 快速开始 / Quick Start

```bash
python3 哔哩哔哩音频下载器.py
```

### 操作步骤 / Steps

1. 粘贴视频链接，点「获取视频信息」确认标题和 UP主无误。
2. 选码率、选保存目录（默认 `~/Music`）。
3. 合集视频可勾选「下载全部P」，单 P 视频该选项会自动禁用。
4. 点「开始下载」，进度和日志实时显示。

1. Paste the video link and click 「获取视频信息」 to check the title and uploader.
2. Choose a bitrate and an output directory (defaults to `~/Music`).
3. Tick 「下载全部P」 for collections; the option is disabled automatically for single videos.
4. Click 「开始下载」 and watch the progress bar and log.

---

## 打包 / Building

先修正 `B站音频下载器.spec` 里的脚本路径，然后：

```bash
pyinstaller --noconfirm B站音频下载器.spec
```

生成的单文件程序在 `dist/` 下。注意 `yt-dlp` 和 `ffmpeg` 不会被打进包里，目标机器仍需自行安装。

---

## 说明 / Notes

默认只在需要转码时调用 ffmpeg，选「原始质量」则直接保存源音频，不重编码、不失真。

封面预览需要能访问 B 站 CDN，部分网络环境下可能加载失败，这不影响下载功能。

---

## License

MIT