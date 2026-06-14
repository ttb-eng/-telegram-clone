# Telegram Clone API

仿 Telegram 的实时通讯 API，基于 **FastAPI + PostgreSQL + Redis + WebSocket + AI** 构建。

> 在线演示：http://47.94.175.132/docs （Swagger UI）

---

## 项目亮点

| 亮点 | 说明 |
|------|------|
| AI Bot + 连续对话 | 集成 DeepSeek API，支持多轮上下文记忆 |
| Tool Calling | AI 可调用工具：查时间 / 查天气 / 联网搜索 |
| WebSocket 实时通信 | 消息推送、在线状态、输入状态、离线消息队列 |
| 异步架构 | FastAPI + SQLAlchemy Async + asyncpg 全异步链路 |
| 部署上线 | 云服务器 + systemd + Nginx 反代 + PostgreSQL |

## 技术栈

| 技术 | 用途 |
|------|------|
| **FastAPI** | Web 框架 |
| **SQLAlchemy** (Async) | ORM + asyncpg 驱动 |
| **PostgreSQL** | 生产数据库 |
| **Redis** | 缓存 + 在线状态 + 离线队列 |
| **WebSocket** | 实时消息推送 |
| **JWT** (python-jose) | 用户认证 |
| **bcrypt** (passlib) | 密码哈希 |
| **DeepSeek API** | AI 对话引擎 |
| **Nginx** | 反向代理 |
| **systemd** | 进程守护 + 开机自启 |
| **Docker** | 容器化部署 |

## 项目结构

```
telegram-clone/
├── app/
│   ├── main.py              # 应用入口，路由注册 & CORS
│   ├── config.py            # 配置管理（环境变量）
│   ├── database.py          # 异步 SQLAlchemy 引擎 & 会话
│   ├── redis_client.py      # Redis 异步客户端
│   ├── models/              # SQLAlchemy ORM 模型
│   │   ├── user.py
│   │   ├── friend.py
│   │   └── message.py
│   ├── schemas/             # Pydantic 请求/响应模型
│   │   ├── user.py
│   │   ├── friend.py
│   │   └── message.py
│   ├── api/                 # HTTP API 路由
│   │   ├── auth.py          # 注册/登录
│   │   ├── users.py         # 用户信息
│   │   ├── friends.py       # 好友管理
│   │   ├── messages.py      # 消息发送/历史/搜索/撤回
│   │   └── upload.py        # 文件上传
│   ├── services/            # 业务逻辑层
│   │   ├── auth.py          # JWT 签发 & 验证
│   │   ├── user.py
│   │   ├── friend.py
│   │   ├── message.py       # 含 AI 连续对话上下文
│   │   ├── deepseek.py      # DeepSeek AI 流式回复 + Tool Calling
│   │   └── tools.py         # Tool Calling 工具定义
│   └── ws/
│       └── manager.py       # WebSocket 连接管理
├── tests/                   # pytest 测试
├── docker-compose.yml       # 一键部署
├── Dockerfile
├── requirements.txt
└── .env                     # 环境变量配置
```

## 快速启动

### 方式一：本地开发

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动 PostgreSQL 和 Redis（需 Docker）
docker compose up db redis -d

# 3. 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API 文档：http://localhost:8000/docs

### 方式二：Docker 一键部署

```bash
docker compose up -d --build
```

### 方式三：生产部署

```bash
# systemd 进程管理
systemctl start telegram-clone
systemctl enable telegram-clone    # 开机自启
systemctl status telegram-clone     # 查看状态
```

---

## API 接口

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 注册（phone, username, display_name, password） |
| POST | `/api/auth/login` | 登录（phone, password） |

### 用户

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/users/me` | 获取当前用户信息 |
| PATCH | `/api/users/me` | 更新个人信息 |
| GET | `/api/users/search?q=` | 搜索用户 |
| GET | `/api/users/{id}` | 获取指定用户信息 |

### 好友

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/friends/requests` | 发送好友请求 |
| POST | `/api/friends/requests/{id}/accept` | 接受好友请求 |
| POST | `/api/friends/requests/{id}/reject` | 拒绝好友请求 |
| GET | `/api/friends/requests` | 查看收到的好友请求 |
| DELETE | `/api/friends/{id}` | 删除好友 |
| GET | `/api/friends` | 好友列表 |

### 消息

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/messages` | 发送消息 |
| GET | `/api/messages/{peer_id}?page=1&page_size=50` | 聊天历史（分页） |
| POST | `/api/messages/read/{peer_id}` | 标记已读 |
| DELETE | `/api/messages/{msg_id}` | 撤回消息 |
| GET | `/api/messages/search?q=` | 搜索消息 |
| GET | `/api/conversations` | 会话列表 |

### 文件上传

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/upload` | 上传文件（类型/大小校验） |

### 实时

| 协议 | 路径 | 说明 |
|------|------|------|
| WebSocket | `/ws?token={jwt}` | 实时消息连接 |

### 其他

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/offline-messages` | 拉取离线消息 |
| GET | `/api/online/{user_id}` | 查询用户在线状态 |
| GET | `/api/health` | 健康检查 |

---

## AI Bot

项目内置一个 AI Bot 用户（`ai_bot`），启动时自动创建。发送消息给 `ai_bot` 即可触发 DeepSeek AI 自动回复。

### 连续对话

AI 能记住最近 **20 条** 历史消息作为上下文，实现连贯的多轮对话。

### Tool Calling（函数调用）

AI 可以调用以下工具：

| 工具 | 说明 | 示例 |
|------|------|------|
| `get_time` | 查询指定时区的当前时间 | "现在几点？" |
| `get_weather` | 查询城市天气 | "北京天气怎么样？" |
| `web_search` | 联网搜索最新信息 | "今天有什么新闻？" |

配置方式：在 `.env` 中填入 DeepSeek API Key：

```
DEEPSEEK_API_KEY=sk-your-key-here
```

---

## 部署架构

```
用户浏览器 → Nginx (80端口) → FastAPI (8000) → PostgreSQL + Redis
                                                    ↑
                                              systemd 守护进程
```

- 云服务器：阿里云 ECS（Ubuntu 24.04）
- 进程管理：systemd（开机自启 + 崩溃自动重启）
- 反向代理：Nginx
- 数据库：PostgreSQL（异步 asyncpg）
- 缓存：Redis

## WebSocket 消息格式

**发送消息：**
```json
{
  "type": "message",
  "msg_id": "uuid",
  "payload": {
    "receiver_id": "uuid",
    "content": "Hello!",
    "msg_type": "text"
  }
}
```

**接收消息：**
```json
{
  "type": "new_message",
  "payload": {
    "msg_id": "uuid",
    "sender_id": "uuid",
    "receiver_id": "uuid",
    "content": "Hello!",
    "created_at": "2024-01-01T00:00:00"
  }
}
```

**心跳：**
```json
{"type": "ping"}
→ {"type": "pong"}
```

## 测试

```bash
pytest -v
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | PostgreSQL 连接串 | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis 连接串 | `redis://localhost:6379/0` |
| `SECRET_KEY` | JWT 签名密钥 | (需修改) |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | (可选) |
| `MAX_UPLOAD_SIZE_MB` | 上传文件大小限制 | 20 |

---

## 面试要点

如果你正在准备后端岗位面试，这个项目可以展示以下能力：

1. **AI 应用开发** — 集成 DeepSeek API + 连续对话 + Tool Calling
2. **实时通信** — WebSocket 全双工通信 + 在线状态管理
3. **异步编程** — FastAPI + SQLAlchemy Async + asyncpg 全链路异步
4. **数据库设计** — PostgreSQL 表设计 + SQLAlchemy ORM
5. **部署运维** — systemd + Nginx + 云服务器上线
6. **安全意识** — bcrypt 密码哈希、JWT 鉴权、文件类型校验
