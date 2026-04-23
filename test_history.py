import os
from wsl_clipboard import append_to_history, process_history_upload, HISTORY_FILE

def test_history_flow():
    print("--- 开始测试历史记录汇总流程 ---")
    
    # 1. 清空之前的历史文件
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            f.write("")
    
    # 2. 模拟记录文本和图片
    print("模拟记录内容...")
    append_to_history("测试文本 1: 这是一个测试内容")
    append_to_history("![测试图片](https://upload.moonchan.xyz/api/test_id/test.avif)")
    append_to_history("测试文本 2: 另一个测试内容")
    
    # 验证文件是否写入
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        content = f.read()
        print(f"当前历史文件内容长度: {len(content)}")
        if "测试文本 1" in content and "![测试图片]" in content:
            print("✅ 本地记录写入成功")
        else:
            print("❌ 本地记录写入失败")
            return
    
    # 3. 执行汇总上传
    print("\n执行汇总上传...")
    success = process_history_upload()
    
    if success:
        print("✅ 汇总上传函数返回成功")
    else:
        print("❌ 汇总上传函数返回失败")
        return
        
    # 4. 验证文件是否被清空
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            print("✅ 历史文件已成功清空")
        else:
            print(f"❌ 历史文件未清空: {content}")

if __name__ == "__main__":
    test_history_flow()
