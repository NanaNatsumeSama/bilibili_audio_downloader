#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B站(哔哩哔哩)音频下载器 — tkinter 图形界面，基于 yt-dlp + ffmpeg。"""

import json
import os
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import tkinter as tk
import tkinter.font as tkfont
import urllib.request
from tkinter import filedialog, messagebox, ttk

YTDLP = shutil.which("yt-dlp") or os.path.expanduser("~/.local/bin/yt-dlp")
FFMPEG = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
FONT = "Noto Sans CJK SC"

BITRATES = [
    ("原始质量（不转码，保留 m4a/flac）", "original"),
    ("MP3 128k", "128"),
    ("MP3 192k", "192"),
    ("MP3 320k", "320"),
]
DEFAULT_BITRATE = "MP3 192k"

PCT_RE = re.compile(r"\[download\]\s+([\d.]+)%")
ERR_RE = re.compile(r"^ERROR:")
ALREADY_RE = re.compile(r"already been downloaded")
POST_RE = re.compile(r"\[(ExtractAudio|Merger|PostProcess|VideoConvertor|FfmpegPostProcessor)\]")
TMPDEST_RE = re.compile(r"^\[download\] Destination:")


def fmt_time(secs):
    secs = int(secs or 0)
    return f"{secs // 60:02d}:{secs % 60:02d}"


class App:
    def __init__(self, root):
        self.root = root
        self.q = queue.Queue()
        self.meta = None
        self.running = False
        self.thumb_img = None

        root.title("B站音频下载器")
        root.geometry("580x660")
        root.minsize(540, 600)

        style = ttk.Style()
        try:
            style.theme_use("clam")
            for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
                tkfont.nametofont(name).configure(family=FONT, size=10)
        except tk.TclError:
            pass

        self._build_ui()
        if not os.path.isfile(YTDLP):
            self._fatal(f"找不到 yt-dlp：{YTDLP}\n请先安装并加入 PATH。")
        else:
            root.after(80, self._poll)

    # ---------------- UI ----------------
    def _build_ui(self):
        pad = {"padx": 10, "pady": 5}

        url_frame = ttk.LabelFrame(self.root, text="视频链接")
        url_frame.pack(fill="x", **pad)
        self.url_var = tk.StringVar()
        ttk.Entry(url_frame, textvariable=self.url_var).grid(
            row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=6)
        ttk.Button(url_frame, text="获取视频信息", command=self.fetch_info).grid(
            row=1, column=0, padx=(8, 4), pady=6, sticky="w")
        ttk.Button(url_frame, text="粘贴", command=self.paste_url).grid(
            row=1, column=1, padx=4, pady=6, sticky="w")
        url_frame.columnconfigure(1, weight=1)

        pre = ttk.LabelFrame(self.root, text="视频预览")
        pre.pack(fill="both", expand=True, **pad)
        pre.columnconfigure(1, weight=1)
        self.thumb_lbl = ttk.Label(pre, text="暂无封面", anchor="center", relief="groove")
        self.thumb_lbl.grid(row=0, column=0, rowspan=3, padx=8, pady=8, sticky="nw")
        self.info_lbls = {}
        for row, (key, label) in enumerate((("title", "标题"), ("uploader", "UP主"), ("duration", "时长"))):
            ttk.Label(pre, text=f"{label}:").grid(row=row, column=1, sticky="ne", pady=(10, 0) if row == 0 else 6)
            lbl = ttk.Label(pre, text="-", wraplength=330, anchor="w", justify="left")
            lbl.grid(row=row, column=2, sticky="nw", pady=(10, 0) if row == 0 else 6)
            self.info_lbls[key] = lbl

        opt = ttk.LabelFrame(self.root, text="下载设置")
        opt.pack(fill="x", **pad)
        opt.columnconfigure(1, weight=1)
        ttk.Label(opt, text="码率:").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        self.bitrate_var = tk.StringVar(value=DEFAULT_BITRATE)
        ttk.Combobox(opt, textvariable=self.bitrate_var, state="readonly", width=28,
                     values=[n for n, _ in BITRATES]).grid(row=0, column=1, sticky="w", padx=4, pady=6)
        self.all_parts_var = tk.BooleanVar(value=False)
        self.all_parts_chk = ttk.Checkbutton(opt, text="下载全部P(合集所有分P)", variable=self.all_parts_var,
                                             command=self._sync_parts)
        self.all_parts_chk.grid(row=0, column=2, columnspan=2, sticky="w", padx=8, pady=6)

        ttk.Label(opt, text="保存到:").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.dir_var = tk.StringVar(value=os.path.expanduser("~/Music"))
        ttk.Entry(opt, textvariable=self.dir_var).grid(row=1, column=1, sticky="ew", padx=4, pady=6)
        ttk.Button(opt, text="浏览…", command=self.browse_dir).grid(row=1, column=2, padx=8, pady=6)

        self.dl_btn = ttk.Button(self.root, text="开始下载", command=self.start_download)
        self.dl_btn.pack(fill="x", **pad)

        prog = ttk.Frame(self.root)
        prog.pack(fill="x", **pad)
        self.progress = ttk.Progressbar(prog, maximum=100, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True)
        self.pct_lbl = ttk.Label(prog, text="0%", width=6)
        self.pct_lbl.pack(side="left", padx=(6, 0))

        log_frame = ttk.LabelFrame(self.root, text="日志")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log_text = tk.Text(log_frame, height=8, wrap="word", state="disabled",
                                font=(FONT, 9))
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True, padx=6, pady=6)

        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(self.root, textvariable=self.status_var, anchor="w",
                  relief="sunken").pack(fill="x", side="bottom")

    # ---------------- 小工具 ----------------
    def _fatal(self, msg):
        messagebox.showerror("错误", msg)
        self.set_status("不可用")
        self.dl_btn.config(state="disabled")

    def set_status(self, msg):
        self.status_var.set(msg)

    def log(self, msg):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        # 只保留最近 500 行，避免长时间运行后 Text 无限膨胀
        if int(self.log_text.index("end-1c").split(".")[0]) > 500:
            self.log_text.delete("1.0", "101.0")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def put(self, kind, payload):
        self.q.put((kind, payload))

    def paste_url(self):
        try:
            self.url_var.set(self.root.clipboard_get().strip())
        except tk.TclError:
            messagebox.showwarning("提示", "剪贴板为空或不可用")

    def browse_dir(self):
        d = filedialog.askdirectory(initialdir=self.dir_var.get() or None, title="选择保存位置")
        if d:
            self.dir_var.set(d)

    def _sync_parts(self):
        """只有确实是多 P 视频时才允许勾选“下载全部P”。"""
        count = (self.meta or {}).get("playlist_count") or 1
        self.all_parts_chk.config(state="normal" if count > 1 else "disabled")
        if count <= 1:
            self.all_parts_var.set(False)

    # ---------------- 获取信息 ----------------
    def fetch_info(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("提示", "请先输入视频链接")
            return
        if self.running:
            messagebox.showinfo("提示", "当前有下载任务进行中")
            return
        self.set_status("正在获取视频信息…")
        self.info_lbls["title"].config(text="获取中…")
        threading.Thread(target=self._fetch_worker, args=(url,), daemon=True).start()

    def _fetch_worker(self, url):
        try:
            proc = subprocess.run([YTDLP, "-J", "--no-playlist", "--no-warnings", url],
                                  capture_output=True, text=True, timeout=120)
            err = proc.stderr or ""
            if proc.returncode != 0:
                lines = [l for l in err.splitlines() if ERR_RE.match(l)]
                raise RuntimeError("\n".join(lines or err.strip().splitlines()[-3:]) or "获取失败")
            data = json.loads(proc.stdout)
            self.put("info", data)
        except Exception as e:
            self.put("error", f"获取信息失败:\n{e}")

    # ---------------- 下载 ----------------
    def start_download(self):
        url = self.url_var.get().strip()
        outdir = self.dir_var.get().strip()
        if not url or not outdir:
            messagebox.showwarning("提示", "请填写链接和保存位置")
            return
        if self.running:
            messagebox.showinfo("提示", "已有下载任务在进行中")
            return
        try:
            os.makedirs(outdir, exist_ok=True)
        except OSError as e:
            messagebox.showerror("错误", f"无法创建目录:\n{e}")
            return

        br = next((k for name, k in BITRATES if name == self.bitrate_var.get()), "192")
        # 多 P 时加序号前缀，避免同名文件互相覆盖
        multi = self.all_parts_var.get() and (self.meta or {}).get("playlist_count", 1) > 1
        name_tpl = "%(playlist_index)02d - %(title)s.%(ext)s" if multi else "%(title)s.%(ext)s"

        cmd = [YTDLP, "--newline", "--no-warnings", "--no-overwrites",
               "-P", outdir, "-o", name_tpl]
        if not self.all_parts_var.get():
            cmd.append("--no-playlist")
        cmd += ["-f", "ba"] if br == "original" else \
               ["-x", "--audio-format", "mp3", "--audio-quality", br + "k"]
        cmd.append(url)

        self.running = True
        self.dl_btn.config(state="disabled")
        self.progress["value"] = 0
        self.pct_lbl.config(text="0%")
        self.log("-" * 40)
        self.log(f"开始下载: {url}\n保存到: {outdir}")
        self.set_status("下载中…")
        threading.Thread(target=self._download_worker, args=(cmd,), daemon=True).start()

    def _download_worker(self, cmd):
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, bufsize=1, errors="replace")
            for raw in proc.stdout:
                line = raw.strip()
                if not line:
                    continue
                if TMPDEST_RE.match(line):
                    self.put("progress", 0.0)
                    self.put("status", "下载中…")
                m = PCT_RE.search(line)
                if m:
                    self.put("progress", min(float(m.group(1)), 100.0))
                    continue
                self.put("log", line)
                if ALREADY_RE.search(line):
                    self.put("log", "· 文件已存在，已跳过")
                elif POST_RE.search(line):
                    self.put("status", "正在转码/封装…")
            proc.wait()
            self.put("done", proc.returncode)
        except Exception as e:
            self.put("error", f"下载异常:\n{e}")

    # ---------------- 队列轮询 ----------------
    def _poll(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "progress":
                    self.progress["value"] = payload
                    self.pct_lbl.config(text=f"{payload:.0f}%")
                elif kind == "status":
                    self.set_status(str(payload))
                elif kind == "log":
                    self.log(str(payload))
                elif kind == "info":
                    self._apply_info(payload)
                elif kind == "thumb":
                    self._apply_thumb(payload)
                elif kind == "error":
                    self._finish()
                    self.set_status("出错")
                    self.log("[!] " + str(payload))
                    messagebox.showerror("错误", str(payload))
                elif kind == "done":
                    self._finish()
                    if payload == 0:
                        self.progress["value"] = 100
                        self.pct_lbl.config(text="100%")
                        self.set_status("完成")
                        self.log("✔ 下载完成")
                        messagebox.showinfo("完成", f"下载完成！\n已保存到:\n{self.dir_var.get()}")
                    else:
                        self.set_status("下载失败")
                        self.log("[!] 下载失败（见上方日志）")
                        messagebox.showerror("错误", "下载失败，请查看日志")
        except queue.Empty:
            pass
        except tk.TclError:
            return  # 窗口已销毁
        except Exception as e:
            self.log("[!] 界面异常: " + str(e))
            self._finish()
        finally:
            try:
                self.root.after(80, self._poll)
            except tk.TclError:
                pass

    def _finish(self):
        self.running = False
        self.dl_btn.config(state="normal")

    # ---------------- 信息与封面 ----------------
    def _apply_info(self, data):
        self.meta = data
        self.info_lbls["title"].config(text=data.get("title") or "-")
        self.info_lbls["uploader"].config(text=data.get("uploader") or data.get("channel") or "-")
        secs = data.get("duration") or 0
        self.info_lbls["duration"].config(text=fmt_time(secs))
        self._sync_parts()
        self.log(f"[信息] {data.get('title')} — {data.get('uploader')} — {fmt_time(secs)}")
        self.set_status("信息已获取，可开始下载")
        if data.get("thumbnail"):
            threading.Thread(target=self._thumb_worker, args=(data["thumbnail"],), daemon=True).start()
        else:
            self.thumb_lbl.config(text="无封面")

    def _thumb_worker(self, thumb_url):
        png = None
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                src = os.path.join(tmpdir, "thumb.img")
                png = os.path.join(tmpdir, "thumb.png")
                req = urllib.request.Request(thumb_url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=30) as r, open(src, "wb") as f:
                    f.write(r.read())
                subprocess.run([FFMPEG, "-y", "-i", src, "-vf",
                                "scale=220:-1:force_original_aspect_ratio=decrease",
                                "-frames:v", "1", png], capture_output=True, timeout=60)
                data = open(png, "rb").read() if os.path.exists(png) and os.path.getsize(png) else None
            self.put("thumb", data)
        except Exception:
            self.put("thumb", None)

    def _apply_thumb(self, png_bytes):
        if not png_bytes:
            self.thumb_lbl.config(text="封面加载失败")
            return
        path = os.path.join(tempfile.gettempdir(), "bili_thumb.png")
        try:
            with open(path, "wb") as f:
                f.write(png_bytes)
            self.thumb_img = tk.PhotoImage(file=path)
            self.thumb_lbl.config(image=self.thumb_img, text="")
        except tk.TclError:
            self.thumb_lbl.config(text="封面加载失败")
        finally:
            try:
                os.remove(path)
            except OSError:
                pass


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()