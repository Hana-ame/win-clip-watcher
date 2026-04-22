package main

import (
	"context"
	"encoding/base64"
	"fmt"
	"os"
	"path/filepath"

	"golang.design/x/clipboard"
)

func main() {
	// 初始化剪贴板 API
	err := clipboard.Init()
	if err != nil {
		panic(err)
	}

	// 创建上下文和监听通道
	ctx := context.Background()
	textCh := clipboard.Watch(ctx, clipboard.FmtText)
	imageCh := clipboard.Watch(ctx, clipboard.FmtImage)

	// 确保图片临时目录存在
	// tempDir := `C:\Temp`
	tempDir := `.`
	os.MkdirAll(tempDir, os.ModePerm)

	// 阻塞监听
	for {
		select {
		case textData := <-textCh:
			// 监听到文本：转为 Base64 输出，避免多行文本破坏 stdout 的逐行读取
			fmt.Println("EVENT:TEXT")
			fmt.Println(base64.StdEncoding.EncodeToString(textData))
			os.Stdout.Sync() // 强制刷新缓冲区，确保 Python 立即收到

		case imgData := <-imageCh:
			// 监听到图片：保存到 Windows 临时目录，并输出路径
			imgPath := filepath.Join(tempDir, "wsl_clipboard_temp.png")
			err := os.WriteFile(imgPath, imgData, 0644)
			if err == nil {
				fmt.Println("EVENT:IMAGE")
				fmt.Println(imgPath)
				os.Stdout.Sync()
			}
		}
	}
}
