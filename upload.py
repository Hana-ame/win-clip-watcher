#!/usr/bin/env python3
import sys
import requests
import os
import urllib.parse
import time
import mimetypes
import gzip
import io

def upload_file(file_path: str = None, custom_name: str = None, data_bytes: bytes = None) -> str | None:
    """
    上传文件到 https://upload.moonchan.xyz/api/upload

    参数：
        file_path: 本地文件路径（与 data_bytes 二选一）
        custom_name: 自定义文件名（可选）
        data_bytes: 直接传入文件内容的 bytes（适用于内存数据）

    返回：
        成功时返回公开 URL 字符串，失败返回 None
    """
    api_url = "https://upload.moonchan.xyz/api/upload"

    # 1. 确定文件内容与文件名
    if file_path:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        filename = custom_name or os.path.basename(file_path)
        with open(file_path, 'rb') as f:
            content = f.read()
    elif data_bytes is not None:
        content = data_bytes
        filename = custom_name or f"upload_{int(time.time())}.bin"
    else:
        raise ValueError("必须提供 file_path 或 data_bytes")

    # 2. 确定 Content-Type
    mime_type, encoding = mimetypes.guess_type(filename)
    if encoding == 'gzip' or filename.endswith('.gz'):
        mime_type = 'application/gzip'
    elif not mime_type:
        mime_type = 'application/octet-stream'

    # 3. 发送 PUT 请求
    headers = {
        'Content-Type': mime_type,
        'X-File-Name': urllib.parse.quote(filename)
    }

    try:
        response = requests.put(api_url, headers=headers, data=content)
        response.raise_for_status()
        result = response.json()

        if 'error' in result:
            print(f"服务器返回错误: {result['error'].get('message', 'Unknown error')}")
            return None

        file_id = result.get('id') or (result.get('data') and result['data'].get('id'))
        if not file_id:
            print("服务器响应中没有文件 ID:", result)
            return None

        public_url = f"https://upload.moonchan.xyz/api/{file_id}/{urllib.parse.quote(filename)}"
        return public_url

    except requests.exceptions.RequestException as e:
        print(f"上传请求失败: {e}")
        if e.response is not None:
            print(f"服务器响应: {e.response.text}")
        return None


def gzip_compress_text(text: str, filename: str = "compressed.txt.gz") -> bytes:
    """
    将文本字符串进行 gzip 压缩，返回压缩后的 bytes
    """
    # 将文本转为 UTF-8 bytes
    text_bytes = text.encode('utf-8')
    
    # 使用 gzip 压缩
    compressed_buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=compressed_buffer, mode='wb', filename=filename, mtime=0) as gz:
        gz.write(text_bytes)
    
    return compressed_buffer.getvalue()


def main(original_text:str):
    # 1. 原始文本内容
    #     original_text = """Hello Moonchan!
    # 这是一段测试文本，将被 gzip 压缩后上传。
    # 压缩可以节省带宽和存储空间。
    # """
    
    # 2. 压缩文本
    compressed_data = gzip_compress_text(original_text, filename="example.txt.gz")
    
    # 3. 上传压缩后的文件
    print("正在上传 gzip 压缩文件...")
    uploaded_url = upload_file(
        data_bytes=compressed_data,
        custom_name="example.txt.gz"
    )
    
    if not uploaded_url:
        print("上传失败，退出")
        sys.exit(1)
    
    print(f"上传成功，压缩文件 URL: {uploaded_url}")
    
    # 4. 将上传得到的 URL 作为 url 参数拼接到目标地址
    #    这里假设您需要一个类似 https://upload.moonchan.xyz/api/{file_id}/code_xxx.html 的页面，
    #    但您的例子中该页面的 ID 似乎是另一个独立的上传结果。
    #    为了演示，我们使用一个虚拟的基础 URL，您可以替换为实际的服务地址。
    base_page_url = "https://upload.moonchan.xyz/api/01LLWEUUZMPL5WNGJF3ZBYCDFKBL4KI6SL/code_1776668249395.html"
    # 或者您可以动态生成一个页面 ID（需要根据实际业务逻辑，这里仅作示例）
    # 简单做法：直接构造带查询参数的链接
    final_url = f"{base_page_url}?url={urllib.parse.quote(uploaded_url, safe='')}"
    
    print("\n最终拼接的链接（可将此链接分享给他人）：")
    print(final_url)
    
    # 如果您需要的是“上传一个 gzip 文件，然后用其 URL 替换另一个 API 的 url 参数”，
    # 您可以根据实际需求修改 base_page_url 的生成方式。
    # 例如，用户例子中 base_page_url 本身也是一个上传返回的 HTML 文件 URL，
    # 这意味着您可能需要先上传一个 HTML 模板文件，再传入压缩文件的 URL。
    # 但根据当前描述，我们仅演示压缩上传 + URL 拼接的核心步骤。
    return final_url

# if __name__ == "__main__":
#     main()