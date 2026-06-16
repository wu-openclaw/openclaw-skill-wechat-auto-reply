---
name: wechat-auto-reply
description: 微信自动回复助手——监控微信消息，用 DeepSeek 自动生成回复
version: 1.0.0
author: wu
homepage: https://github.com/wu-openclaw/openclaw-skill-wechat-auto-reply
tags: [wechat, weixin, auto-reply, chinese, automation]
---

# 微信自动回复助手

用 AI 自动回微信消息。监听指定聊天窗口，收到新消息后用 DeepSeek 生成回复并发送。

## 前置条件

- **Windows 系统**（wxauto 只在 Windows 上工作）
- **微信 PC 版已登录**，要回复的聊天窗口保持打开
- Python 3.x，已安装 wxauto：`pip install wxauto uiautomation`

## 使用方式

### 1. 安装依赖
```bash
pip install wxauto uiautomation
```

### 2. 启动自动回复
```bash
cd scripts
python wechat_reply.py -t "聊天对象名称"
```

`-t` 参数填微信里显示的联系人或群名。

### 3. 停止
按 `Ctrl+C` 停止。

---

## 功能说明

- 监控指定聊天窗口，有新消息时自动读取
- 调用 DeepSeek API 分析消息并生成回复
- 自动发送回复到微信
- 支持设置回复延迟（避免回复太快显得像机器人）
- 支持黑名单关键词（遇到"广告"、"骚扰"等词不回复）
- 日志记录所有收发内容

## 安全提示

- 不要用于骚扰、诈骗或任何违法目的
- 自动回复可能违反微信用户协议，风险自负
- 建议先用自己的小号测试
