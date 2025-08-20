# MCP-Mem0: AI智能体的长期记忆

一个集成了 [Mem0](https://mem0.ai) 的 [模型上下文协议 (MCP)](https://modelcontextprotocol.io) 服务器，为AI智能体提供持久化记忆功能。

## 概述

这个MCP服务器使AI智能体能够使用语义搜索存储、检索和搜索记忆，支持可配置的嵌入模型和维度。

## 功能特性

服务器提供三个核心的记忆管理工具：

1. **`save_memory`**: 将任何信息存储到长期记忆中，并进行语义索引
2. **`get_all_memories`**: 检索所有存储的记忆以获得全面的上下文
3. **`search_memories`**: 使用语义搜索查找相关记忆

## 系统要求

- Python 3.12+
- PostgreSQL 数据库（用于向量存储）
- LLM提供商的API密钥（OpenAI、OpenRouter 或 Ollama）
- Docker 和 Docker Compose（可选，用于容器化部署）

## 安装方式

### 方式一：直接安装

1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

2. 基于 `.env.example` 创建 `.env` 文件：
   ```bash
   cp .env.example .env
   ```

3. 在 `.env` 文件中配置环境变量

### 方式二：使用 Docker

1. 使用 Docker Compose 启动：
   ```bash
   docker-compose up -d
   ```

2. 或者构建并运行 Docker 镜像：
   ```bash
   docker build -t mcp-mem0 .
   docker run -d --env-file .env -p 8050:8050 mcp-mem0
   ```

## 配置说明

在 `.env` 文件中配置以下环境变量：

| 变量名 | 描述 | 示例 |
|----------|-------------|----------|
| `TRANSPORT` | 传输协议 (sse 或 stdio) | `sse` |
| `HOST` | 使用SSE传输时绑定的主机地址 | `0.0.0.0` |
| `PORT` | 使用SSE传输时监听的端口 | `8050` |
| `LLM_PROVIDER` | LLM提供商 (openai, openrouter 或 ollama) | `openai` |
| `LLM_BASE_URL` | LLM API的基础URL | `https://api.openai.com/v1` |
| `LLM_API_KEY` | LLM提供商的API密钥 | `sk-...` |
| `LLM_CHOICE` | 要使用的LLM模型 | `gpt-4o-mini` |
| `EMBEDDING_MODEL_CHOICE` | 要使用的嵌入模型 | `text-embedding-3-small` |
| `EMBEDDING_DIMS` | 嵌入维度（可选，自动检测） | `1536` |
| `DATABASE_URL` | PostgreSQL连接字符串 | `postgresql://user:pass@host:port/db` |

## 运行服务器

### SSE传输方式

```bash
# 在 .env 中设置 TRANSPORT=sse，然后：
python src/main.py
```

### Stdio传输方式

使用stdio传输时，MCP客户端将在需要时自动启动服务器。

## 与MCP客户端集成

### Claude Desktop

#### SSE配置

在Claude Desktop配置文件 (`claude_desktop_config.json`) 中添加：

```json
{
  "mcpServers": {
    "mem0": {
      "transport": "sse",
      "url": "http://localhost:8050/sse"
    }
  }
}
```

#### Stdio配置

```json
{
  "mcpServers": {
    "mem0": {
      "command": "python",
      "args": ["path/to/src/main.py"],
      "env": {
        "TRANSPORT": "stdio",
        "LLM_PROVIDER": "openai",
        "LLM_BASE_URL": "https://api.openai.com/v1",
        "LLM_API_KEY": "YOUR-API-KEY",
        "LLM_CHOICE": "gpt-4o-mini",
        "EMBEDDING_MODEL_CHOICE": "text-embedding-3-small",
        "EMBEDDING_DIMS": "1536",
        "DATABASE_URL": "YOUR-DATABASE-URL"
      }
    }
  }
}
```

#### Docker配置

如果使用Docker运行，可以这样配置：

```json
{
  "mcpServers": {
    "mem0": {
      "command": "docker",
      "args": ["run", "--rm", "--env-file", "/path/to/.env", "-p", "8050:8050", "mcp-mem0"],
      "env": {
        "TRANSPORT": "sse"
      }
    }
  }
}
```

## 特性

- **可配置的嵌入模型**: 支持OpenAI和Ollama嵌入模型
- **自动检测维度**: 根据选择的模型自动设置嵌入维度
- **自定义基础URL**: 通过LLM_BASE_URL支持自定义API端点
- **灵活的传输协议**: 支持SSE和stdio两种传输协议
- **Docker支持**: 提供完整的Docker和Docker Compose支持
- **语义搜索**: 基于向量相似度的智能记忆检索
- **智能连接管理**: 自动管理数据库连接，防止连接泄漏

## 连接管理器

本项目包含一个简化的连接管理器，用于优化mem0ai客户端的连接管理，防止连接泄漏。

### 主要功能

- **自动连接管理**: 自动创建和复用mem0ai客户端连接
- **连接池机制**: 支持多个客户端实例的连接复用
- **定期清理**: 自动清理空闲连接
- **上下文管理**: 提供Python上下文管理器，确保连接正确释放

### 使用方法

#### 推荐方式：使用上下文管理器

```python
from src.connection_manager import managed_mem0_client

# 自动管理客户端生命周期
with managed_mem0_client("my_client") as client:
    # 使用客户端进行操作
    result = client.add("这是一条记忆", user_id="user123")
    memories = client.search("记忆", user_id="user123")
# 客户端会自动清理
```

#### 手动管理方式

```python
from src.connection_manager import get_connection_manager

manager = get_connection_manager()

# 启动定期清理
manager.start_periodic_cleanup()

try:
    # 获取客户端
    client = manager.get_client("my_client")
    
    # 使用客户端
    result = client.add("记忆内容", user_id="user123")
    
finally:
    # 释放客户端
    manager.release_client("my_client")
    
    # 应用关闭时清理所有连接
    manager.cleanup_all()
    manager.stop_periodic_cleanup()
```

### 最佳实践

1. **优先使用上下文管理器**: `managed_mem0_client` 确保连接正确释放
2. **应用关闭时清理**: 确保在应用关闭时调用 `cleanup_all()`

## 使用示例

### 保存记忆
```python
# 通过MCP客户端调用
save_memory("用户喜欢在周末看科幻电影")
```

### 搜索记忆
```python
# 搜索相关记忆
search_memories("用户的娱乐偏好", limit=5)
```

### 获取所有记忆
```python
# 获取完整的记忆上下文
get_all_memories()
```

## 故障排除

### 常见问题

1. **数据库连接失败**
   - 确保PostgreSQL服务正在运行
   - 检查DATABASE_URL格式是否正确
   - 验证数据库用户权限

2. **API密钥错误**
   - 确认LLM_API_KEY和EMBEDDER_API_KEY正确
   - 检查API密钥是否有足够的权限

3. **嵌入维度不匹配**
   - 设置正确的EMBEDDING_DIMS值
   - 确保向量存储中的维度配置一致

4. **Docker相关问题**
   - 确保Docker和Docker Compose已正确安装
   - 检查端口8050是否被占用
   - 验证.env文件路径和权限

5. **连接管理问题**
   - **连接泄漏**: 确保使用上下文管理器或正确调用 `release_client()`
   - **连接数过多**: 确保应用正确释放不再使用的客户端
   - **客户端创建失败**: 检查数据库连接和配置文件是否正确

## 开发

### 本地开发设置

1. 克隆仓库：
   ```bash
   git clone <repository-url>
   cd mcp-mem0
   ```

2. 创建虚拟环境：
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或
   venv\Scripts\activate     # Windows
   ```

3. 安装开发依赖：
   ```bash
   pip install -r requirements.txt
   ```

### 测试

运行测试套件：
```bash
python -m pytest tests/
```

#### 基本测试

运行基本的MCP服务器测试：

```bash
# 测试MCP服务器
python -m pytest tests/ -v
```

## 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件。

## 贡献

欢迎贡献！请随时提交Pull Request或创建Issue。

## 支持

如果您遇到问题或有疑问，请：

1. 查看本README的故障排除部分
2. 搜索现有的Issues
3. 创建新的Issue并提供详细信息

## 相关链接

- [Mem0 官方文档](https://docs.mem0.ai/)
- [模型上下文协议 (MCP)](https://modelcontextprotocol.io)
- [Claude Desktop](https://claude.ai/desktop)
