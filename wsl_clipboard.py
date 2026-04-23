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
import hashlib
import threading
from datetime import datetime

from avif import compress_avif_to_bytes
from upload import upload_file, main as upload_text, gzip_compress_text, wrap_gzip_url
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

seen_hashes = set()
HISTORY_FILE = "clipboard_history.md"


def get_content_hash(content):
    if isinstance(content, bytes):
        return hashlib.sha256(content).hexdigest()
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def append_to_history(content: str):
    """将内容追加到本地 Markdown 文件"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n\n**{timestamp}**\n{content}\n")
    log.info(f"内容已记录到本地历史文件: {HISTORY_FILE}")


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
    text_hash = get_content_hash(text)
    if text_hash in seen_hashes:
        log.info("文本内容重复，跳过")
        return
    seen_hashes.add(text_hash)

    preview = text.strip().replace("\n", "\\n")[:100]
    log.info(f"新文本: {preview}{'...' if len(text.strip()) > 100 else ''}")

    # ---- 修改：判断长度决定存储方式 ----
    stripped_text = text.strip()
    lines = stripped_text.splitlines()
    if len(lines) > 5:
        # 压缩并上传
        compressed_data = gzip_compress_text(stripped_text, filename="clip.md.gz")
        upload_name = f"clip_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md.gz"
        public_url = upload_file(data_bytes=compressed_data, custom_name=upload_name)
        
        if public_url:
            # 记录前五行 + 链接
            preview_lines = "\n".join(lines[:5])
            append_to_history(f"{preview_lines}\n\n...\n\n🔗 {wrap_gzip_url(public_url)}")
        else:
            # 上传失败则记录全文
            append_to_history(stripped_text)
    else:
        # 5行及以下直接记录
        append_to_history(stripped_text)

    pass


def on_new_image_data(img_bytes: bytes, image_path: str):
    """
    [占位函数] 剪贴板出现新图片时调用
    参数 img_bytes: 图片的二进制数据
    参数 image_path: 图片在 WSL 中的路径（用于日志）
    """
    try:
        img_hash = get_content_hash(img_bytes)
        log.info(f"图片事件: {image_path} | Hash: {img_hash[:12]}...")
        
        if img_hash in seen_hashes:
            log.info(f"图片内容重复，跳过: {image_path}")
            return
        seen_hashes.add(img_hash)

        size_kb = len(img_bytes) / 1024
        log.info(f"处理新图片: {image_path} ({size_kb:.1f} KB)")

        # ---- 你的图片处理逻辑写在这里 ----

        print(f"正在压缩 {image_path} -> AVIF ...")
        avif_bytes = compress_avif_to_bytes(img_bytes, quality=80, speed=5)
        compressed_size_kb = len(avif_bytes) / 1024
        print(f"✅ 压缩完成: {compressed_size_kb:.1f} KB (原大小: {size_kb:.1f} KB)")

        public_url = upload_file(
            data_bytes=avif_bytes, custom_name="compressed_image.avif"
        )

        if public_url:
            print(f"\n✅ 上传成功！\n🔗 URL: {public_url}")
            # 可选：将 URL 保存到文件，方便其他工具读取
            with open(".last_upload_url", "w") as f:
                f.write(public_url)
            
            # ---- 修改：不再实时 post，而是记录到本地文件 ----
            append_to_history(f"![图片]({public_url})")
        else:
            print("上传失败")
    except Exception as e:
        log.error(f"处理图片数据失败: {e}")


def process_history_upload():
    """
    读取本地 Markdown，上传获取链接，发布到 Moonchan
    """
    if not os.path.exists(HISTORY_FILE):
        log.info("历史记录文件不存在，跳过上传")
        return False
        
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
        
        if not content:
            log.info("历史记录为空，跳过上传")
            return False
            
        # 1. 压缩并上传 (逻辑同 upload_text)
        compressed_data = gzip_compress_text(content, filename="history.md.gz")
        public_url = upload_file(
            data_bytes=compressed_data, 
            custom_name=f"history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md.gz"
        )
        
        if public_url:
            # 2. 将链接发布到 Moonchan
            post_text(f"🕒 剪贴板历史汇总 ({datetime.now().strftime('%Y-%m-%d %H:%M')}):\n{wrap_gzip_url(public_url)}")
            log.info(f"历史记录已汇总上传: {public_url}")
            
            # 3. 清空本地历史文件
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                f.write("")
            return True
        else:
            log.error("历史汇总上传失败")
            return False
            
    except Exception as e:
        log.error(f"执行历史汇总上传时出错: {e}")
        return False


def upload_history_to_moonchan():
    """
    每小时执行一次的调度循环
    """
    while True:
        # 每 3600 秒运行一次
        threading.Event().wait(3600)
        log.info("正在执行每小时一次的历史记录汇总上传...")
        process_history_upload()


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

    # 启动每小时汇总上传的后台线程
    upload_thread = threading.Thread(target=upload_history_to_moonchan, daemon=True)
    upload_thread.start()
    log.info("后台汇总上传线程已启动 (每小时执行一次)")

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
                
                # 立即读取文件内容，防止在处理过程中被 Go 进程覆盖
                try:
                    if os.path.exists(wsl_img_path):
                        with open(wsl_img_path, "rb") as f:
                            img_data = f.read()
                        on_new_image_data(img_data, wsl_img_path)
                    else:
                        log.warning(f"收到图片事件，但找不到文件: {wsl_img_path}")
                except Exception as e:
                    log.error(f"立即读取图片失败: {e}")

    except KeyboardInterrupt:
        log.info("正在停止监听...")
    finally:
        # 退出时确保杀掉 Go 子进程，防止变成僵尸进程
        process.terminate()
        process.wait()
        log.info("已退出")


if __name__ == "__main__":
    main()
