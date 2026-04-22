#!/usr/bin/env python3
from PIL import Image
import pillow_avif   # 确保已安装: pip install pillow pillow-avif-plugin
import io

from upload import upload_file

# 假设上面的 upload_file 函数已经定义在同一文件中
# 或者从另一个模块导入

def compress_avif_to_bytes(image_path: str, quality: int = 75, speed: int = 6) -> bytes:
    """将图片压缩为 AVIF 格式并返回 bytes 对象"""
    img = Image.open(image_path)
    with io.BytesIO() as output:
        img.save(output, format='AVIF', quality=quality, speed=speed)
        return output.getvalue()

def main():
    input_image = "wsl_clipboard_temp.png"   # 你的原始图片路径

    # 1. 读取并压缩为 AVIF
    print(f"正在压缩 {input_image} -> AVIF ...")
    avif_bytes = compress_avif_to_bytes(input_image, quality=80, speed=5)

    # 2. 上传到服务器（自定义文件名）
    public_url = upload_file(
        data_bytes=avif_bytes,
        custom_name="compressed_image.avif"
    )

    if public_url:
        print(f"\n✅ 上传成功！\n🔗 URL: {public_url}")
        # 可选：将 URL 保存到文件，方便其他工具读取
        with open(".last_upload_url", "w") as f:
            f.write(public_url)
    else:
        print("上传失败")

if __name__ == "__main__":
    main()