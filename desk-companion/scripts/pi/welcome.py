#!/usr/bin/python3
"""Local first-start helper. Credentials stay on this device, never in a URL."""

import fcntl
import json
from pathlib import Path
import subprocess
import tkinter as tk
from tkinter import messagebox
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
        "树莓派首次使用 / First start\n\n"
        "软件已离线安装。先连接网络，再打开页面。\n"
        "VTC-Student：PEAP / MSCHAPv2；输入自己的 CNA 用户名和密码。\n"
        "保留 CA 证书验证及 vtc.edu.hk 域名；如学校更改证书，请向 IT 核实。\n\n"
        "麦克风、摄像头、唤醒词与机械输出不会自动启动。\n"
        "语音在点击麦克风后才调用 Qwen 并计费。"
    )).pack(anchor="w", pady=16)
    status = tk.StringVar(value="正在检查本地服务…")
    tk.Label(app, textvariable=status, wraplength=720, justify="left").pack(anchor="w")

    def launch(url):
        profile = Path.home() / ".local/state/desk-companion/chromium"
        profile.mkdir(parents=True, exist_ok=True, mode=0o700)
        subprocess.Popen(["chromium", "--no-first-run", f"--user-data-dir={profile}", f"--app={url}"])

    def credentials():
        try:
            value = json.loads((state / "credentials.json").read_text())
            messagebox.showinfo("本机页面登录 / Local login", f"Username: {value['username']}\nPassword: {value['password']}\n\n保存在本机私有目录；请勿发到聊天或 Git。")
        except (OSError, ValueError, KeyError):
            messagebox.showerror("尚未就绪", "本地账户尚未初始化。查看服务诊断。")

    buttons = tk.Frame(app)
    buttons.pack(anchor="w", pady=16)
    actions = [
        ("学校 Wi-Fi 设置", lambda: subprocess.Popen(["nm-connection-editor", "--edit=c0a12d72-834c-4b80-b454-70f9adac9137"])),
        ("查看本机登录信息", credentials),
        ("打开桌面页面", lambda: launch("http://127.0.0.1:8831/?surface=device&lang=zh")),
        ("打开完整工作区", lambda: launch("http://127.0.0.1:8831/?lang=zh")),
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
