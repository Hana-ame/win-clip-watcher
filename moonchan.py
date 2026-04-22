#!/usr/bin/env python3
import requests
import sys
import json
import os
import pickle
import argparse
from typing import Dict, Any, Optional


class MoonchanClient:
    """Moonchan 论坛 API 客户端"""

    BASE_URL = "https://vps.moonchan.xyz/api/v2/"
    DEFAULT_COOKIE_FILE = "moonchan_cookies.txt"

    def __init__(self, cookie_file: str = DEFAULT_COOKIE_FILE):
        """
        初始化客户端，加载或获取会话 Cookie。

        Args:
            cookie_file: 用于保存/加载 Cookie 的文件路径
        """
        self.cookie_file = cookie_file
        self.session = self._get_session()

    def _get_session(self) -> requests.Session:
        """创建并配置 requests.Session，从文件加载 Cookie 或访问 /cookie 端点获取"""
        session = requests.Session()

        # 尝试从文件加载已有的 Cookie
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, 'rb') as f:
                    session.cookies.update(pickle.load(f))
                return session
            except Exception:
                # 文件损坏或无法读取，重新获取
                pass

        # 获取新的 auth cookie
        try:
            r = session.get(self.BASE_URL + "cookie", timeout=10)
            r.raise_for_status()
            # 保存 Cookie 供后续使用
            with open(self.cookie_file, 'wb') as f:
                pickle.dump(session.cookies, f)
        except Exception as e:
            print(f"Error getting cookie: {e}")

        return session

    def list_board(self, bid: int, pn: int = 0) -> Dict[str, Any]:
        """
        列出板块中的主题列表。

        Args:
            bid: 板块 ID
            pn: 页码（从 0 开始）

        Returns:
            API 返回的 JSON 数据
        """
        url = f"{self.BASE_URL}?bid={bid}&tid=0&pn={pn}"
        r = self.session.get(url, timeout=10)
        r.raise_for_status()
        return r.json()

    def read_topic(self, bid: int, tid: int) -> Dict[str, Any]:
        """
        阅读指定主题的所有回复。

        Args:
            bid: 板块 ID
            tid: 主题 ID

        Returns:
            API 返回的 JSON 数据
        """
        url = f"{self.BASE_URL}?bid={bid}&tid={tid}"
        r = self.session.get(url, timeout=10)
        r.raise_for_status()
        return r.json()

    def post_topic(self, bid: int, nickname: str, title: str, content: str, attachment: str = "") -> Dict[str, Any]:
        """
        发布新主题。

        Args:
            bid: 板块 ID
            nickname: 昵称
            title: 主题标题
            content: 正文内容
            attachment: 可选的附件 URL

        Returns:
            API 返回的 JSON 或成功状态字典
        """
        url = f"{self.BASE_URL}?bid={bid}&tid=0"
        payload = {
            "id": "",
            "no": 0,
            "n": nickname,
            "t": title,
            "txt": content,
            "p": attachment
        }
        r = self.session.post(url, json=payload, timeout=10)
        r.raise_for_status()
        # 成功时可能返回空响应体
        return {"status": "success", "code": r.status_code} if r.text == "" else r.json()

    def reply_topic(self, bid: int, tid: int, nickname: str, content: str, attachment: str = "") -> Dict[str, Any]:
        """
        回复已有主题。

        Args:
            bid: 板块 ID
            tid: 主题 ID
            nickname: 昵称
            content: 回复内容
            attachment: 可选的附件 URL

        Returns:
            API 返回的 JSON 或成功状态字典
        """
        url = f"{self.BASE_URL}?bid={bid}&tid={tid}"
        payload = {
            "id": "",
            "no": 0,
            "n": nickname,
            "t": "",
            "txt": content,
            "p": attachment
        }
        r = self.session.post(url, json=payload, timeout=10)
        r.raise_for_status()
        return {"status": "success", "code": r.status_code} if r.text == "" else r.json()


def main():
    """命令行入口，使用 MoonchanClient 类执行命令"""
    parser = argparse.ArgumentParser(description="Moonchan Forum API Helper")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # list 命令
    list_parser = subparsers.add_parser("list", help="List topics in a board")
    list_parser.add_argument("bid", type=int, help="Board ID")
    list_parser.add_argument("--pn", type=int, default=0, help="Page number")

    # read 命令
    read_parser = subparsers.add_parser("read", help="Read a topic")
    read_parser.add_argument("bid", type=int, help="Board ID")
    read_parser.add_argument("tid", type=int, help="Topic ID")

    # post 命令
    post_parser = subparsers.add_parser("post", help="Post a new thread")
    post_parser.add_argument("bid", type=int, help="Board ID")
    post_parser.add_argument("n", help="Nickname")
    post_parser.add_argument("t", help="Title")
    post_parser.add_argument("txt", help="Content")
    post_parser.add_argument("--p", default="", help="Optional attachment URL")

    # reply 命令
    reply_parser = subparsers.add_parser("reply", help="Reply to a topic")
    reply_parser.add_argument("bid", type=int, help="Board ID")
    reply_parser.add_argument("tid", type=int, help="Topic ID")
    reply_parser.add_argument("n", help="Nickname")
    reply_parser.add_argument("txt", help="Content")
    reply_parser.add_argument("--p", default="", help="Optional attachment URL")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    client = MoonchanClient()

    try:
        if args.command == "list":
            result = client.list_board(args.bid, args.pn)
        elif args.command == "read":
            result = client.read_topic(args.bid, args.tid)
        elif args.command == "post":
            result = client.post_topic(args.bid, args.n, args.t, args.txt, args.p)
        elif args.command == "reply":
            result = client.reply_topic(args.bid, args.tid, args.n, args.txt, args.p)
        else:
            parser.print_help()
            sys.exit(1)

        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()