#!/usr/bin/python3
"""Optional local connection helper; the normal session opens Alice directly."""

import fcntl
from pathlib import Path
import subprocess
import tkinter as tk
import urllib.request


def main():
    state = Path.home() / ".local/share/desk-companion"
    lock = (state / "welcome.lock").open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return
    app = tk.Tk()
    app.title("Desk Companion · Group 2")
    app.geometry("780x540")
    app.configure(padx=28, pady=24)
    tk.Label(app, text="Desk Companion", font=("sans", 25, "bold")).pack(anchor="w")
    tk.Label(app, justify="left", wraplength=720, font=("sans", 13), text=(
        "Alice 已准备好。\n\n"
        "打开桌面即可开始对话，日历和事务保留在同一工作空间。\n"
        "语音入口和 Alice 唤醒开关位于对话区。"
    )).pack(anchor="w", pady=16)
    status = tk.StringVar(value="正在检查本地服务…")
    tk.Label(app, textvariable=status, wraplength=720, justify="left").pack(anchor="w")

    def launch(url):
        profile = Path.home() / ".local/state/desk-companion/chromium"
        profile.mkdir(parents=True, exist_ok=True, mode=0o700)
        subprocess.Popen(["chromium", "--no-first-run", f"--user-data-dir={profile}", f"--app={url}"])

    buttons = tk.Frame(app)
    buttons.pack(anchor="w", pady=16)
    actions = [
        ("打开 Alice", lambda: launch("http://127.0.0.1:8831/?surface=device&lang=zh")),
        ("打开完整工作区", lambda: launch("http://127.0.0.1:8831/?lang=zh")),
        ("网络设置", lambda: subprocess.Popen(["nm-connection-editor"])),
    ]
    for i, (label, command) in enumerate(actions):
        tk.Button(buttons, text=label, command=command, padx=14, pady=9).grid(row=i // 2, column=i % 2, padx=(0, 10), pady=5, sticky="w")

    def check():
        try:
            with urllib.request.urlopen("http://127.0.0.1:8831/api/health", timeout=1) as response:
                ready = response.status == 200
        except OSError:
            ready = False
        status.set("本地服务已启动。Local service ready." if ready else "本地服务尚未就绪。可在终端查看：journalctl --user -u desk-companion -n 50")
        app.after(4000, check)

    app.after(500, check)
    app.mainloop()
    lock.close()


if __name__ == "__main__":
    main()
