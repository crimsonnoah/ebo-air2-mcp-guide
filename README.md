# EBO Air 2 MCP Guide

> Unofficial community guide and patches for connecting AI agents to the Enabot EBO Air 2 through MCP.

[中文](#中文说明) · [English](#english)

## 中文说明

这个项目记录一套已经在 **EBO Air 2** 上实际验证过的方案，让支持 MCP 的 AI 客户端通过一个受保护的桥接服务控制机器人。

## 从这里开始

- [完整部署教程](docs/deployment-guide.md)
- [Claude Code、Codex 与 API 客户端设置](docs/client-setup.md)
- [故障排查](docs/troubleshooting.md)
- [安全政策](SECURITY.md)
- [脱敏配置示例](examples)

目前已验证：

- 摄像头查看与机器人状态读取
- 自主移动：方向、速度与单次移动时长
- 停止普通轮式移动
- 10 种单次 Skill Actions
- 12 种官方表情
- EBO 麦克风 → 本地 faster-whisper ASR
- Fish Audio TTS → EBO 扬声器
- Claude Code、Codex，以及其他支持 MCP 的客户端

> [!WARNING]
> 这不是 Enabot 官方项目。机器人会在现实空间中移动。第一次测试请把 EBO 放在平坦、开阔、远离楼梯和边缘的地面上，并保持有人看护。

### 已验证的动作

| Action | ID |
|---|---:|
| advance | 1 |
| figure eight | 2 |
| circle | 3 |
| backward | 4 |
| snake moving | 5 |
| z-shaped | 6 |
| rotation | 7 |
| break free | 8 |
| wander | 9 |
| swing | 10 |

这些是机器人自己完成的单次动作，正常情况下无需再调用 stop。

### 已验证的表情

| Expression | ID |
|---|---:|
| happy | 1 |
| like | 2 |
| cute | 3 |
| love you | 4 |
| surprised | 5 |
| confused | 6 |
| depressed | 7 |
| sneering | 8 |
| dizzy | 9 |
| LOVE | 10 |
| patience | 11 |
| giggling | 12 |

### 安全默认值

- 有效移动速度建议从 **20** 开始测试
- 本项目的测试上限：速度 **80**
- 单次移动时长上限：**30 秒**
- 执行动作前先查看摄像头并确认地面安全
- stop 适用于普通 MCP 轮式移动，但不是硬件级急停
- 预设 Skill Action 是一次性动作，不依赖 stop 中断

### 客户端兼容性

| Client | Connection |
|---|---|
| Claude Code | MCP |
| Codex | Streamable HTTP MCP |
| OpenAI Responses API | Remote MCP tool |
| Other agents | Any compatible MCP client |

如果客户端运行在云端，不能直接连接机器人主机上的 127.0.0.1。请使用带身份验证的 HTTPS MCP 地址或安全隧道，并且不要把控制端口无保护地公开到互联网。

### 绝对不要提交到 GitHub

- Enabot 登录邮箱和密码
- App payload/sign keys
- MCP、API 或 Telegram token
- Fish Audio API key / voice ID
- 机器人序列号、MAC、家庭公网 IP
- 真实的 options.json、.env 或服务器日志

公开示例必须使用明显的占位符，例如 YOUR_EBO_EMAIL 与 YOUR_API_TOKEN。

---

## English

This repository documents a tested community setup for connecting MCP-compatible AI clients to an **Enabot EBO Air 2** through a token-protected bridge.

Verified capabilities include camera and state access, adjustable movement, normal movement stop, ten single-cycle Skill Actions, twelve official expressions, local faster-whisper ASR, and Fish Audio TTS playback through EBO.

### Compatibility

- Claude Code through MCP
- Codex through Streamable HTTP MCP
- OpenAI Responses API through a remote MCP server
- Other MCP-compatible agents

Cloud-hosted clients cannot reach a local 127.0.0.1 endpoint. Use authenticated HTTPS or a secure MCP tunnel, and never expose unauthenticated robot controls to the public internet.

### Safety

This is an unofficial project. Test movement on a flat, open floor away from stairs and edges. Keep the robot supervised while validating a new installation. Software stop is not a hardware emergency stop.

## Start here

- [Deployment guide](docs/deployment-guide.md)
- [MCP client setup](docs/client-setup.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Security policy](SECURITY.md)
- [Sanitized examples](examples)

## Project status

The core robot bridge and MCP tools have been validated on EBO Air 2. Deployment, client setup, troubleshooting, and sanitized configuration examples will be added as separate documents.

## Credits and license

This guide builds on the community work in [Playcolors-co/ha-enabot](https://github.com/Playcolors-co/ha-enabot). Preserve upstream copyright and license notices when redistributing modified source files.

Released under the [MIT License](LICENSE). Enabot and EBO are trademarks of their respective owners.
