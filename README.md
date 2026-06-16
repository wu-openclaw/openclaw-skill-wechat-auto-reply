# 微信自动回复助手 (WeChat Auto Reply)

> 🤖 让阿财帮你在微信上自动回复消息——后台监听，AI 生成回复，自动发送。

## 功能

- 📩 **实时监听微信消息** — 监控指定聊天窗口
- 🧠 **AI 智能回复** — 用 DeepSeek 生成自然口语化回复
- ⏱️ **随机延迟** — 1-3 秒随机延迟，不像机器人
- 🚫 **黑名单过滤** — 广告、骚扰关键词自动跳过
- 📝 **聊天记录** — 自动保存历史，理解上下文

## 安装

```bash
# 1. 安装依赖
pip install wxauto uiautomation openai

# 2. 从 ClawHub 安装
clawhub install wechat-auto-reply
```

## 使用

### 启动
```bash
python scripts/wechat_reply.py -t "张三"
```

微信搜索栏搜"张三"打开聊天窗口，脚本自动开始监听。

### 运行中命令
| 命令 | 说明 |
|---|---|
| `status` | 查看当前状态 |
| `switch <名字>` | 切换监听对象 |
| `pause` | 暂停自动回复 |
| `resume` | 恢复自动回复 |
| `quit` / Ctrl+C | 退出 |

### 列出会话
```bash
python scripts/wechat_reply.py --list
```

## 前置条件

- ✅ Windows 系统
- ✅ 微信 PC 版已登录（v3.9.x 以上）
- ✅ 要回复的聊天必须在前台（有聊天窗口打开）
- ✅ DeepSeek API Key

## 开源协议

MIT

## 作者

wu @ ClawHub
