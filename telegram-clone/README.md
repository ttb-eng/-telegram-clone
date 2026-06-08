# Telegram Clone API

仿 Telegram 的实时通讯 API，基于 FastAPI + PostgreSQL + Redis + WebSocket 构建。

## 项目架构

```
telegram-clone/
├── app/
│   ├── main.py              # 应用入口，路由注册
│   ├── config.py            # 配置管理（环境变量）
│   ├── database.py          # 异步 SQLAlchemy 引擎 & 会话
│   ├── redis_client.py      # Redis 异步客户端
│   ├── models/              # SQLAlchemy ORM 模型
│   │   ├── user.py          # 用户模型
│   │   ├── friend.py        # 好友关系模型
│   │   └── message.py       # 消息模型
│   ├── schemas/             # Pydantic 请求/响应模型
│   │   ├── user.py
│   │   ├── friend.py
│   │   └── message.py
│   ├── api/                 # HTTP API 路由
│   │   ├── auth.py          # 注册/登录
│   │   ├── users.py         # 用户信息
│   │   ├── friends.py       # 好友管理
│   │   └── messages.py      # 消息发送/历史
│   ├── services/            # 业务逻辑层
│   │   ├── auth.py          # JWT & 密码
│   │   ├── user.py
│   │   ├── friend.py
│   │   ├── message.py
│   │   └── deepseek.py      # AI 回复（可选）
│   └── ws/
│       └── manager.py       # WebSocket 连接管理
├── tests/                   # pytest 测试
├── docker-compose.yml       # 一键部署
├── Dockerfile
└── requirements.txt
```

## 快速启动

### 方式一：本地开发

**1. 安装依赖**

```bash
pip install -r requirements.txt
pip install aiosqlite  # 测试用
```

**2. 启动 PostgreSQL 和 Redis**

```bash
docker compose up db redis -d
```

**3. 配置环境变量**

复制 `.env` 文件并修改配置（默认即可本地运行）。

**4. 启动服务**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API 文档：http://localhost:8000/docs

### 方式二：Docker 一键部署

```bash
docker compose up -d --build
```

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
| GET | `/api/friends` | 好友列表 |

### 消息

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/messages` | 发送消息 |
| GET | `/api/messages/{peer_id}?page=1&page_size=50` | 获取聊天历史（分页） |
| POST | `/api/messages/read/{peer_id}` | 标记已读 |

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
pip install aiosqlite
pytest -v
```

## AI 回复（可选）

在 `.env` 中配置 DeepSeek API Key：

```
DEEPSEEK_API_KEY=sk-your-key-here
```

启动后，发送消息给特定 AI 用户将自动触发回复。

## Postman 测试

1. 导入 OpenAPI 文档：`http://localhost:8000/openapi.json`
2. 注册用户 → 获取 token
3. 在 Headers 中添加 `Authorization: Bearer {token}`
4. 测试各接口
