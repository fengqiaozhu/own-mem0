# Mem0 API 扩展开发计划

## 项目概述

当前的 `mcp-mem0` 项目仅实现了基础的记忆管理功能（保存、获取全部、搜索记忆）。基于 Mem0 的完整 API 文档分析，我们需要扩展项目以支持更多的 API 功能，包括用户管理、实体管理、高级搜索、记忆删除等功能。

## 当前项目状态

### 已实现的功能
- `save_memory`: 保存记忆
- `get_all_memories`: 获取所有记忆
- `search_memories`: 搜索记忆

### 缺失的重要功能
- 用户管理（Users）
- 代理管理（Agents）
- 应用管理（Apps）
- 运行管理（Runs）
- 记忆删除功能
- 高级过滤和搜索
- 批量操作
- 记忆历史追踪
- 项目管理

## Mem0 重要 API 分析

### 1. 记忆管理 API (Memory APIs)

#### 1.1 基础 CRUD 操作
- ✅ `add()` - 添加记忆（已实现为 save_memory）
- ✅ `get_all()` - 获取所有记忆（已实现）
- ✅ `search()` - 搜索记忆（已实现）
- ❌ `update()` - 更新记忆
- ❌ `delete()` - 删除特定记忆
- ❌ `get()` - 获取特定记忆

#### 1.2 高级记忆操作
- ❌ `get_all()` with v2 filters - 高级过滤获取记忆
- ❌ `search()` with v2 filters - 高级过滤搜索
- ❌ `history()` - 获取记忆历史
- ❌ `batch_update()` - 批量更新记忆
- ❌ `batch_delete()` - 批量删除记忆

#### 1.3 批量删除操作
- ❌ `delete_all()` - 删除用户所有记忆
- ❌ `reset()` - 重置客户端

### 2. 实体管理 API (Entities APIs)

#### 2.1 用户管理 (Users)
- ❌ `users()` - 获取所有用户
- ❌ `delete_user()` - 删除特定用户
- ❌ `delete_all_users()` - 删除所有用户

#### 2.2 代理管理 (Agents)
- ❌ `agents()` - 获取所有代理
- ❌ `delete_agent()` - 删除特定代理
- ❌ `delete_all_agents()` - 删除所有代理

#### 2.3 应用管理 (Apps)
- ❌ `apps()` - 获取所有应用
- ❌ `delete_app()` - 删除特定应用
- ❌ `delete_all_apps()` - 删除所有应用

#### 2.4 运行管理 (Runs)
- ❌ `runs()` - 获取所有运行
- ❌ `delete_run()` - 删除特定运行
- ❌ `delete_all_runs()` - 删除所有运行

### 3. 项目管理 API (Project Management)

#### 3.1 项目操作
- ❌ `project.get()` - 获取项目详情
- ❌ `project.create()` - 创建新项目
- ❌ `project.update()` - 更新项目设置
- ❌ `project.delete()` - 删除项目

#### 3.2 成员管理
- ❌ `project.get_members()` - 获取项目成员
- ❌ `project.add_member()` - 添加项目成员
- ❌ `project.update_member()` - 更新成员角色
- ❌ `project.remove_member()` - 移除项目成员

## 开发优先级规划

### 第一阶段：核心记忆管理扩展
**优先级：高**

1. **记忆删除功能**
   - `delete_memory(memory_id)` - 删除特定记忆
   - `delete_all_memories(user_id)` - 删除用户所有记忆
   - `delete_memories_by_filter(filters)` - 按条件删除记忆

2. **记忆更新功能**
   - `update_memory(memory_id, text, metadata)` - 更新记忆内容

3. **获取特定记忆**
   - `get_memory(memory_id)` - 获取特定记忆详情

4. **记忆历史**
   - `get_memory_history(memory_id)` - 获取记忆变更历史

### 第二阶段：实体管理
**优先级：中高**

1. **用户管理**
   - `get_all_users()` - 获取所有用户列表
   - `delete_user(user_id)` - 删除特定用户及其记忆
   - `get_user_stats(user_id)` - 获取用户统计信息

2. **代理管理**
   - `get_all_agents()` - 获取所有代理列表
   - `delete_agent(agent_id)` - 删除特定代理及其记忆
   - `get_agent_stats(agent_id)` - 获取代理统计信息

3. **应用和运行管理**
   - `get_all_apps()` - 获取所有应用
   - `get_all_runs()` - 获取所有运行
   - `delete_app(app_id)` - 删除应用
   - `delete_run(run_id)` - 删除运行

### 第三阶段：高级搜索和过滤
**优先级：中**

1. **V2 高级搜索**
   - `search_memories_v2(filters, query)` - 支持复杂过滤条件的搜索
   - 支持逻辑操作符：AND, OR, NOT
   - 支持比较操作符：in, gte, lte, gt, lt, ne, contains, icontains
   - 支持通配符：*

2. **V2 高级获取**
   - `get_all_memories_v2(filters)` - 支持复杂过滤条件的记忆获取

### 第四阶段：批量操作
**优先级：中低**

1. **批量更新**
   - `batch_update_memories(updates)` - 批量更新记忆（最多1000条）

2. **批量删除**
   - `batch_delete_memories(memory_ids)` - 批量删除记忆（最多1000条）

### 第五阶段：项目管理（可选）
**优先级：低**

1. **项目操作**
   - `get_project_info()` - 获取当前项目信息
   - `update_project_settings()` - 更新项目设置

2. **成员管理**
   - `get_project_members()` - 获取项目成员
   - `manage_project_members()` - 管理项目成员

## 技术实现细节

### 1. 文件结构规划

```
src/
├── main.py                 # 主服务器文件
├── utils.py               # 工具函数
├── tools/
│   ├── __init__.py
│   ├── memory_tools.py    # 记忆管理工具
│   ├── entity_tools.py    # 实体管理工具
│   ├── search_tools.py    # 搜索工具
│   └── project_tools.py   # 项目管理工具
└── schemas/
    ├── __init__.py
    ├── memory_schemas.py   # 记忆相关数据模式
    └── entity_schemas.py   # 实体相关数据模式
```

### 2. 新增工具函数示例

#### 2.1 记忆删除工具
```python
@server.tool()
def delete_memory(memory_id: str) -> str:
    """删除特定记忆"""
    
@server.tool()
def delete_all_memories(user_id: str) -> str:
    """删除用户所有记忆"""
    
@server.tool()
def delete_memories_by_filter(filters: dict) -> str:
    """按条件删除记忆"""
```

#### 2.2 实体管理工具
```python
@server.tool()
def get_all_users() -> str:
    """获取所有用户列表"""
    
@server.tool()
def delete_user(user_id: str) -> str:
    """删除特定用户及其所有记忆"""
    
@server.tool()
def get_all_agents() -> str:
    """获取所有代理列表"""
```

#### 2.3 高级搜索工具
```python
@server.tool()
def search_memories_v2(filters: dict, query: str = None, limit: int = 10) -> str:
    """使用V2 API进行高级搜索"""
    
@server.tool()
def get_all_memories_v2(filters: dict, limit: int = 100) -> str:
    """使用V2 API进行高级过滤获取"""
```

### 3. 过滤器支持

支持的过滤字段：
- `user_id`, `agent_id`, `app_id`, `run_id`
- `created_at`, `updated_at`
- `categories`, `keywords`
- `metadata`

支持的逻辑操作符：
- `AND`, `OR`, `NOT`

支持的比较操作符：
- `in`, `gte`, `lte`, `gt`, `lt`, `ne`
- `contains`, `icontains`
- `*` (通配符)

### 4. 错误处理和日志

- 为所有新增工具添加详细的错误处理
- 统一的日志格式
- 参数验证
- 返回值标准化

## 测试计划

### 1. 单元测试
- 每个新增工具函数的单元测试
- 参数验证测试
- 错误处理测试

### 2. 集成测试
- MCP 服务器集成测试
- Mem0 客户端连接测试
- 端到端功能测试

### 3. 性能测试
- 批量操作性能测试
- 高级搜索性能测试
- 内存使用测试

## 部署和文档

### 1. 文档更新
- 更新 README.md
- 添加 API 使用示例
- 创建详细的工具函数文档

### 2. Docker 配置
- 更新 Dockerfile（如需要）
- 更新 docker-compose.yml（如需要）
- 环境变量文档

### 3. 版本管理
- 语义化版本控制
- 变更日志维护
- 向后兼容性考虑

## 预期收益

1. **功能完整性**：提供完整的 Mem0 API 支持
2. **用户体验**：更好的记忆管理和用户管理功能
3. **开发效率**：丰富的工具集提高开发效率
4. **可扩展性**：模块化设计便于后续扩展
5. **企业就绪**：支持项目管理和成员管理功能

## 时间估算

- **第一阶段**：2-3 周
- **第二阶段**：2-3 周
- **第三阶段**：1-2 周
- **第四阶段**：1 周
- **第五阶段**：1-2 周

**总计**：7-11 周

## 风险评估

1. **API 变更风险**：Mem0 API 可能发生变化
2. **性能风险**：批量操作可能影响性能
3. **兼容性风险**：新功能可能影响现有功能
4. **复杂性风险**：过多功能可能增加维护复杂性

## 建议

1. **分阶段实施**：按优先级分阶段实施，确保核心功能优先
2. **充分测试**：每个阶段都要进行充分测试
3. **文档同步**：代码和文档同步更新
4. **社区反馈**：收集用户反馈，调整开发优先级
5. **性能监控**：实施过程中持续监控性能指标

---

*此文档将根据开发进度和需求变化持续更新*