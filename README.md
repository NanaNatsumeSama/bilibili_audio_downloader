# B站音频下载器

一个基于 `yt-dlp` + `ffmpeg` 的 tkinter 图形界面工具，用来下载 B 站视频的音频并转码成 MP3。

## 功能

- 粘贴链接获取视频信息（标题 / UP主 / 时长 / 封面预览）
- 码率可选：原始质量（不转码，保留 m4a/flac）或 MP3 128k / 192k / 320k
- 支持合集多 P 下载，自动按 `序号 - 标题` 命名避免同名覆盖
- 实时进度条 + 日志输出，多 P 切换时进度自动重置
- 已存在的文件自动跳过，不做静默覆盖
- 单文件打包成可执行程序（PyInstaller）

## 依赖

| 组件 | 说明 |
| --- | --- |
| Python 3.8+ | 仅用标准库，无需 pip 安装任何包 |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp/releases) | 实际下载，必须安装并在 `PATH` 中 |
| ffmpeg | 转码与封面缩略图处理 |

```bash
# Ubuntu / Debian
sudo apt install ffmpeg
pip install -U yt-dlp
```

程序启动时会检查 `yt-dlp` 是否可用，缺失会直接提示。

## 运行

```bash
python3 哔哩哔哩音频下载器.py
```

## 打包

先修正 `B站音频下载器.spec` 里的脚本路径，然后：

```bash
pyinstaller --noconfirm B站音频下载器.spec
```

生成的单文件程序在 `dist/` 下。注意 `yt-dlp` 和 `ffmpeg` 不会被打进包里，目标机器仍需自行安装。

## 使用说明

1. 粘贴视频链接，点「获取视频信息」确认标题和 UP主无误
2. 选码率、选保存目录（默认 `~/Music`）
3. 合集视频可以勾「下载全部P」，单 P 视频该选项会自动禁用
4. 点「开始下载」，进度和日志实时显示

默认只在需要转码时调 ffmpeg，选「原始质量」则直接保存源音频，不重编码、不失真。

## 说明

封面预览需要能访问 B 站 CDN，部分网络环境下可能加载失败，这不影响下载功能。

## License

MIT