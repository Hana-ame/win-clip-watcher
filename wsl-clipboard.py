#!/usr/bin/env python3
"""
wsl-clipboard-fast.py
通过管道接收 Go 守护进程推送的剪贴板事件，实现毫秒级响应
"""

import subprocess
import base64
import os
import sys
import logging

from avif import compress_avif_to_bytes
from upload import upload_file, main as upload_text
from moonchan import MoonchanClient

# ===================== 配置 =====================
# Go 编译出的 exe 所在路径（建议放在 Windows 盘符下，如 C:\Tools）
GO_WATCHER_EXE = "./clip_watcher.exe"

# ===================== 日志 =====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("clipfast")

client = MoonchanClient()


def post_image(p: str):
    client.post_topic(10001, "", "", "", p)


def post_text(text: str):
    client.post_topic(10001, "", "", text, "")


# ==============================
#  占位处理函数 —— 在此编写逻辑
# ==============================


def on_new_text(text: str):
    """
    [占位函数] 剪贴板出现新文本时调用
    """
    preview = text.strip().replace("\n", "\\n")[:100]
    log.info(f"新文本: {preview}{'...' if len(text.strip()) > 100 else ''}")

    # ---- 你的文本处理逻辑写在这里 ----
    final_url = upload_text(text)

    post_text(
        f"{preview}\n{'...' if len(text.strip()) > 100 else ''}[全文]({final_url})"
    )

    pass


def on_new_image(image_path: str):
    """
    [占位函数] 剪贴板出现新图片时调用
    参数 image_path: 图片在 WSL 中的路径（PNG 格式）
    """
    if os.path.exists(image_path):
        size_kb = os.path.getsize(image_path) / 1024
        log.info(f"新图片: {image_path} ({size_kb:.1f} KB)")

        # ---- 你的图片处理逻辑写在这里 ----

        print(f"正在压缩 {image_path} -> AVIF ...")
        avif_bytes = compress_avif_to_bytes(image_path, quality=80, speed=5)

        public_url = upload_file(
            data_bytes=avif_bytes, custom_name="compressed_image.avif"
        )

        if public_url:
            print(f"\n✅ 上传成功！\n🔗 URL: {public_url}")
            # 可选：将 URL 保存到文件，方便其他工具读取
            with open(".last_upload_url", "w") as f:
                f.write(public_url)
            post_image(public_url)
        else:
            print("上传失败")

    else:
        log.warning(f"收到图片事件，但找不到文件: {image_path}")


# --------------------- 辅助函数 ---------------------


def win_path_to_wsl(win_path: str) -> str:
    """将 C:\\Temp\\xxx 转换为 /mnt/c/Temp/xxx"""
    try:
        drive, path = win_path.split(":", 1)
        wsl_path = f"/mnt/{drive.lower()}{path.replace(chr(92), '/')}"
        return wsl_path
    except:
        return win_path


# --------------------- 主进程 ---------------------


def main():
    if not os.path.exists(GO_WATCHER_EXE):
        log.error(f"找不到 Go 监听程序: {GO_WATCHER_EXE}")
        sys.exit(1)

    log.info("=" * 45)
    log.info(" WSL 极速剪贴板监听器已启动 (Go 驱动)")
    log.info(" Ctrl+C 退出")
    log.info("=" * 45)

    # 启动 Go 守护进程，并接管其标准输出
    # 注意：启动 exe 时 WSL 会自动调用 Windows 互操作层
    process = subprocess.Popen(
        [GO_WATCHER_EXE],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )

    try:
        # 逐行阻塞读取 Go 进程的输出
        # print(process.stdout)
        while process.stdout:
            line = process.stdout.readline()
            if not line:
                break  # Go 进程已退出

            header = line.strip()

            if header == "EVENT:TEXT":
                # 下一行是 Base64 编码的文本
                b64_data = process.stdout.readline().strip()
                try:
                    text = base64.b64decode(b64_data).decode("utf-8")
                    on_new_text(text)
                except Exception as e:
                    log.error(f"解析文本失败: {e}")

            elif header == "EVENT:IMAGE":
                # 下一行是 Windows 的图片路径
                win_img_path = process.stdout.readline().strip()
                wsl_img_path = win_path_to_wsl(win_img_path)
                on_new_image(wsl_img_path)

    except KeyboardInterrupt:
        log.info("正在停止监听...")
    finally:
        # 退出时确保杀掉 Go 子进程，防止变成僵尸进程
        process.terminate()
        process.wait()
        log.info("已退出")


if __name__ == "__main__":
    main()
