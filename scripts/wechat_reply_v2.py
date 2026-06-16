#!/usr/bin/env python3
"""
微信自动回复 v2——使用纯键盘模拟（兼容新版Qt5微信）
依赖：pip install pyautogui keyboard openai pyperclip
"""
import os
import sys
import time
import random
import json
import threading
import argparse
import pyperclip
import pyautogui
import keyboard as kb
import win32gui
import win32con
from datetime import datetime
from openai import OpenAI

# ── 配置 ────────────────────────────────────────
API_KEY = os.environ.get("OPENAI_API_KEY")
API_BASE = "https://api.deepseek.com/v1"
MODEL = "deepseek-chat"

REPLY_DELAY_MIN = 1.5
REPLY_DELAY_MAX = 4.0
POLL_INTERVAL = 2        # 检查新消息的间隔（秒）
MAX_CONTINUOUS = 3       # 连续回复最大条数，避免死循环

BLACKLIST = ["TD", "退订", "广告", "骚扰"]

MY_NAME = "阿财（AI自动回复）"

# 微信窗口信息
HWND = 788776
# 窗口矩形
WINDOW_RECT = (750, 217, 1646, 892)

# ── DeepSeek 调用 ───────────────────────────────
client = OpenAI(api_key=API_KEY, base_url=API_BASE)

def generate_reply(contact_name, message, history=None):
    system_prompt = f"""你是 {MY_NAME}，正在帮你的主人回复微信消息。
回复规则：
1. 简短自然，像真人聊天（1-3 句话即可，不要长篇大论）
2. 用口语化的中文，不要英文（除非消息里有英文）
3. 如果对方问不知道的问题，说"我回头确认一下"
4. 如果对方发的是问候（"在吗"、"hi"），简单回复"在的"或"在呢"
5. 不要主动推销、不要问"有什么需要帮忙的吗"这类客服话术
6. 根据对方的语气调整自己的语气
7. 只输出回复内容，不要加任何解释、前缀、后缀"""
    
    context = f"正在和 {contact_name} 聊天。\n"
    if history:
        for h in history[-6:]:
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
            temperature=0.8,
            max_tokens=200
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        log(f"DeepSeek 调用失败: {e}", "ERROR")
        return None

# ── 微信控制 ────────────────────────────────────
def activate_wechat():
    """激活微信窗口"""
    try:
        win32gui.ShowWindow(HWND, win32con.SW_RESTORE)
        time.sleep(0.2)
        win32gui.SetForegroundWindow(HWND)
    except:
        pass
    time.sleep(0.3)

def search_contact(name):
    """在微信中搜索联系人"""
    activate_wechat()
    # Ctrl+F 打开搜索
    pyautogui.hotkey('ctrl', 'f')
    time.sleep(0.3)
    # 输入联系人名称
    pyautogui.write(name, interval=0.05)
    time.sleep(0.5)
    # 回车进入聊天
    pyautogui.press('enter')
    time.sleep(0.5)

def send_message(text):
    """发送微信消息"""
    # 复制到剪贴板
    pyperclip.copy(text)
    time.sleep(0.2)
    # Ctrl+V 粘贴
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.3)
    # 回车发送
    pyautogui.press('enter')

def get_last_message():
    """获取聊天框最后一条消息（通过全选+复制到剪贴板）"""
    # 先点击聊天框（默认当前在聊天框里了）
    # 全选消息区域
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.1)
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(0.2)
    content = pyperclip.paste()
    return content

def get_new_messages_since(last_content):
    """获取自上次检查以来的新消息"""
    current = get_last_message()
    if not current or current == last_content:
        return None
    # 简单提取：如果内容变多，取新增加的部分
    # 更可靠：看最后几行
    lines = current.strip().split('\n')
    if last_content:
        old_lines = last_content.strip().split('\n')
        new_lines = lines[len(old_lines):]
        if new_lines:
            return '\n'.join(new_lines)
    return current

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")

# ── 主循环 ──────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="微信自动回复 v2")
    parser.add_argument("-t", "--target", default="黄洁芮5.5", help="聊天对象名称")
    parser.add_argument("--dry-run", action="store_true", help="只搜索不回复（测试用）")
    args = parser.parse_args()
    
    target = args.target
    log(f"目标联系人: {target}")
    
    # 先搜索联系人进入聊天
    log(f"正在搜索并打开 '{target}' 的聊天...")
    search_contact(target)
    log(f"已进入聊天，开始监听")
    
    if args.dry_run:
        log("DRY RUN 模式：仅测试连接，不回复")
        time.sleep(2)
        content = get_last_message()
        print(f"\n--- 当前聊天内容 ---\n{content}\n--- 结束 ---")
        return
    
    # ── 监视循环 ──────────────────────────────
    last_content = get_last_message()
    log(f"初始消息已缓存（{len(last_content or '')} 字符）")
    
    history = []
    reply_count = 0
    consecutive_replies = 0
    paused = False
    
    print(f"\n🚀 开始自动回复 {target}")
    print("按 Ctrl+Shift+X 紧急停止\n")
    
    # 注册热键
    stop_flag = threading.Event()
    kb.add_hotkey('ctrl+shift+x', stop_flag.set)
    
    try:
        while not stop_flag.is_set():
            if paused:
                time.sleep(1)
                continue
            
            # 激活微信并获取新消息
            activate_wechat()
            current = get_last_message()
            
            if current and current != last_content:
                # 找到新消息，提取新增内容
                log(f"检测到新消息")
                last_content = current
                
                # 提取最后一段对话（简化版）
                lines = current.strip().split('\n')
                new_msg = lines[-1] if lines else ""
                
                if not new_msg or any(k in new_msg for k in BLACKLIST):
                    log(f"跳过（黑名单）: {new_msg[:30]}")
                    continue
                
                log(f"收到: {new_msg[:50]}")
                history.append({"from": target, "text": new_msg})
                
                # 检查连续回复上限
                if consecutive_replies >= MAX_CONTINUOUS:
                    log(f"已达连续回复上限 {MAX_CONTINUOUS}，暂停一轮")
                    consecutive_replies = 0
                    time.sleep(5)
                    continue
                
                # 生成回复
                reply = generate_reply(target, new_msg, history)
                if not reply:
                    log(f"生成回复失败，跳过")
                    continue
                
                log(f"回复: {reply[:60]}")
                
                # 随机延迟
                delay = random.uniform(REPLY_DELAY_MIN, REPLY_DELAY_MAX)
                time.sleep(delay)
                
                # 发送
                activate_wechat()
                send_message(reply)
                history.append({"from": "me", "text": reply})
                reply_count += 1
                consecutive_replies += 1
                log(f"已回复 ✓ (共{reply_count}条)")
                
                # 更新缓存
                time.sleep(1)
                activate_wechat()
                last_content = get_last_message()
            else:
                # 没有新消息，重置计数器
                consecutive_replies = 0
            
            time.sleep(POLL_INTERVAL)
        
        log("用户手动停止")
    except KeyboardInterrupt:
        pass
    
    print(f"\n\n👋 阿财已停止。共回复 {reply_count} 条消息。")

if __name__ == "__main__":
    main()
