#!/usr/bin/env python3
"""
微信自动回复——监听消息，用 DeepSeek 生成回复。
依赖：pip install wxauto uiautomation openai
"""

import os
import sys
import time
import json
import argparse
from datetime import datetime
from openai import OpenAI

# ── 配置 ────────────────────────────────────────
# DeepSeek API（从 openclaw.json 的 env 里取，或环境变量）
API_KEY = os.environ.get("OPENAI_API_KEY", "sk-d9d35320a0b24edebd43b0bd3a52518a")
API_BASE = "https://api.deepseek.com/v1"
MODEL = "deepseek-chat"

# 回复延迟范围（秒），别太快显得像机器人
REPLY_DELAY_MIN = 1.0
REPLY_DELAY_MAX = 3.0

# 遇到这些关键词的消息不回复
BLACKLIST = ["TD", "退订", "广告", "骚扰", "[图片]", "[表情]", "对方正在输入"]

# 你自己的名字/昵称（回复时会按这个角色说话）
MY_NAME = "阿财（AI自动回复）"

# ── DeepSeek 调用 ───────────────────────────────
client = OpenAI(api_key=API_KEY, base_url=API_BASE)

def generate_reply(contact_name, message, history=None):
    """用 DeepSeek 生成微信回复"""
    system_prompt = f"""你是 {MY_NAME}，正在帮你的主人回复微信消息。

你的人设：松弛、有分寸、不讨好、不油腻、不土不傻。是一个高情商但不过度热情的正常人。

回复规则：
1. 字数越少越好，能三个字说完不要五个字
2. 对方随意你就随意，对方冷淡你就更冷淡
3. 禁止以下表达（一出现就很假）：
   - "哈哈" "是的呢" "好滴" "嗯嗯" "好的呀" "可！" —— 太讨好
   - "这个真的超棒" "哇塞" "绝了" —— 太浮夸
   - "有什么需要随时找我" "希望能帮到你" —— 太客服
   - 叠词卖萌（"等等我哦" "好哒"）—— 太土
4. 自然的口语，像跟朋友发微信，不是写作文
5. 偶尔可以打错字、不加标点，像真人
6. 对方问不知道的事：不回假大空，直接说"不知道"或"我问问"
7. 对方说废话（表情包、哈哈哈）：可以已读不回的感觉，或者回个"嗯"
8. 只输出回复内容，不加解释"""
    
    context = f"正在和 {contact_name} 聊天。\n"
    if history:
        for h in history[-6:]:  # 只保留最近6条
            role = "对方" if h["from"] != "me" else "我"
            context += f"{role}: {h['text']}\n"
    context += f"\n对方刚说：{message}\n\n请回复："
    
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            temperature=0.8,  # 稍微加点随机性，显得自然
            max_tokens=200
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[!] DeepSeek 调用失败: {e}")
        return None

# ── 微信监听 ─────────────────────────────────────
def should_reply(msg_text):
    """判断是否应该回复这条消息"""
    if not msg_text or len(msg_text.strip()) == 0:
        return False
    for keyword in BLACKLIST:
        if keyword in msg_text:
            return False
    return True

def log(msg, level="INFO"):
    """日志"""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")

def show_help():
    """显示使用帮助"""
    print("""
╔══════════════════════════════════════════╗
║     微信自动回复 - 阿财 💰              ║
║                                         ║
║  使用方法：                              ║
║  ─ 先用微信搜索栏搜聊天对象名            ║
║  ─ 按 Ctrl+C 停止                        ║
║                                         ║
║  命令（运行时输入）：                    ║
║    status  — 查看状态                    ║
║    switch <名字> — 切换聊天对象          ║
║    pause   — 暂停自动回复                ║
║    resume  — 恢复自动回复                ║
║    quit    — 退出                        ║
╚══════════════════════════════════════════╝
""")

def main():
    parser = argparse.ArgumentParser(description="微信自动回复")
    parser.add_argument("-t", "--target", help="聊天对象名称（微信里显示的名字）")
    parser.add_argument("-d", "--delay", type=float, default=None, help="固定回复延迟（秒）")
    parser.add_argument("--list", action="store_true", help="列出当前微信打开的聊天窗口")
    args = parser.parse_args()
    
    # 导入 wxauto
    try:
        from wxauto import WeChat
        import uiautomation as auto
    except ImportError:
        print("请先安装依赖：pip install wxauto uiautomation")
        sys.exit(1)
    
    wx = WeChat()
    
    show_help()
    
    # ── 选择聊天对象 ────────────────────────────
    target = args.target
    if args.list:
        print("当前微信会话列表（前20个）：")
        for i, s in enumerate(wx.GetSessionList()[:20], 1):
            print(f"  {i}. {s}")
        sys.exit(0)
    
    while not target:
        sessions = wx.GetSessionList()
        print("\n当前微信会话：")
        for i, s in enumerate(sessions[:15], 1):
            print(f"  {i}. {s}")
        choice = input("\n输入序号或直接输入聊天对象名：").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(sessions):
                target = sessions[idx]
        else:
            target = choice
    
    log(f"开始监听 → {target}")
    
    # ── 主循环 ──────────────────────────────────
    paused = False
    history = []  # 聊天记录
    last_msg_time = None
    
    print(f"\n🚀 开始自动回复 {target}\n按提示操作（Ctrl+C 停止）\n")
    
    try:
        while True:
            if paused:
                time.sleep(1)
                continue
            
            # 获取新消息
            try:
                msgs = wx.GetAllMessage(savepic=False)
            except Exception:
                time.sleep(0.5)
                continue
            
            if not msgs:
                time.sleep(0.5)
                continue
            
            for msg in msgs:
                name = msg[0]  # 发送者名字
                text = msg[1]  # 消息文本
                msg_time = msg[2]  # 时间
                
                # 过滤非目标联系人 和 已处理的消息
                if name != target:
                    continue
                if msg_time == last_msg_time:
                    continue
                if not should_reply(text):
                    log(f"跳过（不回复）: {name}: {text[:40]}")
                    continue
                
                last_msg_time = msg_time
                log(f"收到 → {name}: {text}")
                history.append({"from": name, "text": text})
                
                # 生成回复
                reply = generate_reply(target, text, history)
                if not reply:
                    log("生成回复失败，跳过", "ERROR")
                    continue
                
                log(f"准备回复: {reply}")
                
                # 随机延迟
                if args.delay:
                    delay = args.delay
                else:
                    import random
                    delay = random.uniform(REPLY_DELAY_MIN, REPLY_DELAY_MAX)
                time.sleep(delay)
                
                # 发送回复
                try:
                    wx.SendMsg(reply, target)
                    history.append({"from": "me", "text": reply})
                    log(f"已回复 ✓")
                except Exception as e:
                    log(f"发送失败: {e}", "ERROR")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print(f"\n\n👋 阿财已停止。共回复 {sum(1 for h in history if h['from'] == 'me')} 条消息。")
        sys.exit(0)

if __name__ == "__main__":
    main()
