#!/usr/bin/env python3
"""
微信自动回复 v3 —— 文字+语音都处理
- 文字消息 -> DeepSeek AI 回复
- 语音/图片/表情 -> 统一回复"好的收到"
- 检测逻辑：对比剪贴板内容 + 消息行数变化
"""
import os
import sys
import time
import random
import threading
import argparse
import pyperclip
import pyautogui
import keyboard as kb
import win32gui
import win32con
from datetime import datetime
from openai import OpenAI

API_KEY = os.environ.get("OPENAI_API_KEY")
API_BASE = "https://api.deepseek.com/v1"
MODEL = "deepseek-chat"

REPLY_DELAY_MIN = 2.0
REPLY_DELAY_MAX = 5.0
POLL_INTERVAL = 2
MAX_CONTINUOUS = 5

BLACKLIST = ["TD", "退订", "广告", "骚扰"]
VOICE_FALLBACKS = [
    "好的收到",
    "收到~",
    "知道了，收到",
    "好的",
    "嗯嗯收到",
    "好嘞收到",
]

client = OpenAI(api_key=API_KEY, base_url=API_BASE)

def generate_reply(message, history=None):
    system_prompt = """你叫阿财，帮主人回复微信消息。
规则：
1. 简短（1-3句话），口语化中文
2. 不知道就说"我回头确认一下"
3. 只输出回复内容，不加解释"""
    
    context = "聊天记录：\n"
    if history:
        ctx = []
        for h in history[-8:]:
            ctx.append(f"{'我' if h['from']=='me' else '对方'}: {h['text']}")
        context += "\n".join(ctx[-6:]) + "\n"
    context += f"对方刚说：{message}\n回复："
    
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

def activate_wechat():
    win32gui.ShowWindow(788776, win32con.SW_RESTORE)
    time.sleep(0.2)
    try:
        win32gui.SetForegroundWindow(788776)
    except:
        pass
    time.sleep(0.3)

def search_contact(name):
    activate_wechat()
    pyautogui.hotkey('ctrl', 'f')
    time.sleep(0.2)
    pyautogui.write(name, interval=0.05)
    time.sleep(0.3)
    pyautogui.press('enter')
    time.sleep(0.5)

def send_message(text):
    pyperclip.copy(text)
    time.sleep(0.2)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.2)
    pyautogui.press('enter')

def get_chat_content():
    """获取聊天框完整内容"""
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.2)
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(0.3)
    return pyperclip.paste()

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--target", default="黄洁芮5.5")
    args = parser.parse_args()
    
    target = args.target
    log(f"目标: {target}")
    
    # 搜索并进入聊天
    search_contact(target)
    log("已进入聊天")
    
    # 缓存初始内容
    last_content = get_chat_content()
    last_content_hash = hash(last_content)
    log(f"初始缓存: {len(last_content)} 字符")
    
    stop_flag = threading.Event()
    kb.add_hotkey('ctrl+shift+x', stop_flag.set)
    
    history = []
    reply_count = 0
    consecutive = 0
    voice_reply_count = 0
    
    log("开始监听，Ctrl+Shift+X 停止")
    
    try:
        while not stop_flag.is_set():
            time.sleep(POLL_INTERVAL)
            
            # 检查新消息
            activate_wechat()
            current = get_chat_content()
            current_hash = hash(current)
            
            if current_hash == last_content_hash:
                consecutive = 0
                continue
            
            # 内容变了，有新消息
            last_content_hash = current_hash
            
            # 判断是新文字还是语音/图片
            # 如果文字长度增加很多 -> 文字消息
            # 如果长度没变或只增加一点点 -> 语音/图片/表情
            diff = len(current) - len(last_content) if last_content else len(current)
            last_content = current
            
            # 提取新内容中的最后几条消息
            lines = [l for l in current.strip().split('\n') if l.strip()]
            
            # 尝试找到新增的行
            # 简洁处理：取最后2行作为新消息
            new_msgs = lines[-2:] if len(lines) >= 2 else lines
            
            has_text = False
            for msg in new_msgs:
                msg = msg.strip()
                # 过滤掉时间戳格式的行
                if not msg or any(k in msg for k in BLACKLIST):
                    continue
                # 时间戳行形如 "12:00" 或 "2024/1/1"
                if len(msg) < 15 and (':' in msg or '/' in msg):
                    continue
                if len(msg) < 2:
                    continue
                
                # 检查是否是真正的文本消息（不是语音标记）
                # 微信复制时语音消息的文本表示可能是空或者 [语音]
                if diff <= 3 and len(msg) < 5:
                    # 可能是语音/图片
                    log(f"检测到非文本消息（长度变化: {diff}），回通用回复")
                    reply = random.choice(VOICE_FALLBACKS)
                    log(f"语音回复: {reply}")
                    delay = random.uniform(REPLY_DELAY_MIN, REPLY_DELAY_MAX)
                    time.sleep(delay)
                    activate_wechat()
                    send_message(reply)
                    history.append({"from": "me", "text": reply})
                    reply_count += 1
                    voice_reply_count += 1
                    consecutive += 1
                    log(f"已回复 ✓ (共{reply_count}条, 其中语音{voice_reply_count})")
                    has_text = True
                    break
                elif len(msg) >= 3:
                    # 文字消息
                    if consecutive >= MAX_CONTINUOUS:
                        log(f"连续回复已达上限")
                        consecutive = 0
                        break
                    
                    log(f"收到: {msg[:50]}")
                    history.append({"from": target, "text": msg})
                    
                    reply = generate_reply(msg, history)
                    log(f"回复: {reply[:60]}")
                    
                    delay = random.uniform(REPLY_DELAY_MIN, REPLY_DELAY_MAX)
                    time.sleep(delay)
                    activate_wechat()
                    send_message(reply)
                    history.append({"from": "me", "text": reply})
                    reply_count += 1
                    consecutive += 1
                    log(f"已回复 ✓ (共{reply_count}条)")
                    has_text = True
                    break
            
            if not has_text:
                # 可能是其他类型消息（图片、文件等）
                log(f"未识别消息类型，跳过")
            
            # 更新缓存
            time.sleep(1)
            activate_wechat()
            last_content = get_chat_content()
            last_content_hash = hash(last_content)
            
    except KeyboardInterrupt:
        pass
    
    print(f"\n👋 停止。共回复 {reply_count} 条（语音 {voice_reply_count} 条）")

if __name__ == "__main__":
    main()
