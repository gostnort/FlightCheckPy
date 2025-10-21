# FlightCheckPy v0.63 - 从演示版到生产版的工程变更

## 版本对标

本文档对比 **v0.6 (演示版)** 与 **v0.63 (最终版)**，说明实际工程实现与初始设计的偏离。

---

## 整体架构变更

### v0.6 设计理念
- 单进程内存数据库
- 简单的 HBPR/PR 解析
- 基础的数据验证
- UI 组件松散耦合

### v0.63 实际实现
- **远程数据库服务** - 引入独立的数据库端口服务器
- **分层数据处理** - 专用的处理器、验证器、清理器
- **完整的数据迁移系统** - DatabaseMigrator 处理架构演变
- **紧密的系统集成** - 各模块间的依赖和调用链路

---

## 核心模块演变

### 1. 数据库层

#### v0.6 预期
```
单一 SQLite 文件
├─ hbpr_records 表
└─ commands 表
```

#### v0.63 实现
```
多层数据库架构
├─ 本地数据库 (hbpr_database.py)
│  ├─ flight_info
│  ├─ hbpr_full_records (含30+个 CHbpr 处理字段)
│  ├─ hbpr_simple_records
│  ├─ duplicate_record (完整的版本控制)
│  └─ commands (带版本历史)
├─ 远程数据库客户端 (remote_db/)
│  ├─ memdb_port_server - 独立进程
│  ├─ hbpr_database_client - 网络通信
│  └─ remote_sqlite_adapter - 协议转换
├─ 自动化迁移系统 (database_migration.py)
│  └─ DatabaseMigrator 处理版本升级
└─ 9 个数据库 VIEWs (统计、验证、异常检测)
```

**新增字段数:** 从 ~5 个基础字段 → 35+ 个结构化字段

| 字段类别 | v0.6 | v0.63 | 变化 |
|---------|------|-------|------|
| 乘客信息 | name, seat | name, seat, boarding_number, class, destination, pnr | +5 |
| 行李数据 | bag_info | bag_piece, bag_weight, bag_allowance, expc_piece, expc_weight, asvc_piece, fba_piece, ifba_piece | +8 |
| ASVC 数据 | (无) | asvc_msg, asvc_seat | +2 |
| 票务数据 | (无) | tkne, ff, inbound_flight, outbound_flight | +4 |
| 证件数据 | (无) | pspt_name, pspt_exp_date, is_ca_flyer, has_infant | +4 |
| 验证结果 | (无) | is_validated, is_valid, error_* (5个), validated_at | +7 |
| 版本控制 | (无) | bol_duplicate, is_deleted | +2 |

---

### 2. 数据处理流程

#### v0.6 预期流程 (线性)
```
上传文件
  ↓
解析 HBPR/PR
  ↓
存储到数据库
  ↓
完成
```

#### v0.63 实际流程 (多阶段)
```
上传文件
  ↓
文件类型检测 (detect_file_type)
  ├─ HBPR 路线
  │  └─ HbprProcessor.parse_file_content()
  │
  └─ PR 路线
     ├─ split_commands()
     ├─ merge_pr_sections() [v0.63 新增]
     ├─ extract_tkne_from_pr()
     ├─ find_hbpr_header_by_tkne()
     └─ convert_pr_to_hbpr() [复杂的转换逻辑]
  ↓
内容清理 (clean_hbpr_record_content)
  ├─ 移除二进制/十六进制伪影
  ├─ 处理重复标题 [v0.63 新增]
  └─ 规范化文本
  ↓
存储到数据库 (create_full_record/create_simple_record)
  ├─ 重复检查 (check_hbnb_exists)
  ├─ 版本备份 (auto_backup_before_replace)
  └─ 三种存储策略:
     ├─ 新记录：直接创建
     ├─ 更新：备份原件 + 创建新版本
     └─ 重复：创建带时间戳的副本
  ↓
CHbpr 处理 (v0.63 核心增强)
  ├─ HBNB 号提取
  ├─ 乘客信息提取
  ├─ 结构化数据提取
  ├─ ASVC 消息捕获 [v0.63 新增]
  ├─ ASVC 座位提取 [v0.63 新增，正则表达式: SEAT/[A-Z]\s(\d{1,2}[A-Z])]
  ├─ 行李验证
  ├─ 证件验证
  ├─ 名字验证
  ├─ 签证检查
  ├─ 常旅客检查
  ├─ 连接航班提取
  └─ 错误分类 (5 大类)
  ↓
数据库更新 (update_with_chbpr_results)
  ├─ 字段迁移检查 (_add_chbpr_fields)
  ├─ 35+ 个字段的 UPDATE 语句
  ├─ 结构化数据参数绑定
  └─ 事务提交
  ↓
自动保存 (trigger_auto_save)
  └─ 内存数据库同步到磁盘
```

---

### 3. 数据验证策略

#### v0.6 预期
- 基础格式校验
- 简单的错误消息

#### v0.63 实现
```
多层次验证系统

第 1 层：文件级验证
  ├─ 文件类型检测
  ├─ 航班信息提取
  └─ 内容清理

第 2 层：记录级验证
  ├─ HBPR 格式校验 (regex patterns)
  ├─ HbprProcessor 格式验证
  ├─ CHbpr 字段验证
  └─ 重复检查

第 3 层：字段级验证
  ├─ 乘客信息验证 (name, seat, class)
  ├─ 行李验证 (piece, weight, allowance)
  ├─ 证件验证 (passport expiry, validity)
  ├─ 签证验证 (nationality 检查)
  ├─ 名字验证 (乘客名字匹配)
  └─ 常旅客验证

第 4 层：错误分类
  ├─ Baggage (行李相关)
  ├─ Passport (证件相关)
  ├─ Name (名字相关)
  ├─ Visa (签证相关)
  └─ Other (其他关键错误)

第 5 层：统计汇总
  ├─ 总错误数
  ├─ 各类别错误
  └─ 验证结果存储
```

---

### 4. PR 命令处理

#### v0.6 预期
- 简单的 PR 解析
- 直接转换为 HBPR

#### v0.63 实现
```
完整的 PR 处理流程

输入: PR 命令
  ↓
split_commands() - 按 > 符号分割
  ├─ 提取命令类型 (e.g., REBK, DOCO)
  ├─ 提取 TKNE 票号
  └─ 按航班分组
  ↓
merge_pr_sections() - 合并重复头部 [v0.63 新增关键功能]
  ├─ 识别相同头部的多个 PR 段
  ├─ 移除重复的 PR 行标志 (-)
  ├─ 合并命令内容
  └─ 生成单一 PR 命令
  ↓
extract_tkne_from_pr() - 提取票号
  ├─ 正则匹配 TKNE/
  └─ 获取 13 位票号
  ↓
find_hbpr_header_by_tkne() - 查找对应 HBPR 记录
  ├─ 在数据库中搜索 TKNE
  ├─ 获取原始 HBPR 头部
  └─ 验证航班信息
  ↓
convert_pr_to_hbpr() - 合成新 HBPR
  ├─ 组合原始 HBPR 头部
  ├─ 追加 PR 命令内容
  └─ 生成完整 HBPR 记录
  ↓
输出: 完整的 HBPR 格式
```

**关键差异:** PR 处理从简单转换变成复杂的融合系统

---

### 5. 错误处理策略

#### v0.6 预期
- 简单的 try/catch
- 用户级错误消息

#### v0.63 实现
```
分层错误处理

级别 1 - 系统错误 (抛出异常)
  └─ 数据库连接失败、文件读写等

级别 2 - 验证错误 (记录分类)
  ├─ Baggage errors (超重、超数量)
  ├─ Passport errors (证件过期)
  ├─ Name errors (名字不匹配)
  ├─ Visa errors (缺少签证)
  └─ Other errors (关键业务错误)

级别 3 - 数据一致性错误 (警告但不中止)
  ├─ 座位不匹配 (asvc_seat ≠ seat)
  ├─ 重复乘客
  ├─ 重复座位
  └─ 缺失登机号

级别 4 - 用户交互错误 (Streamlit UI)
  ├─ success / error / warning / info
  ├─ 可展开的详情框
  └─ 进度条显示
```

---

## 数据库管理的演变

### v0.6 预期
- 静态表结构
- 手工版本管理

### v0.63 实现

#### 自动化迁移系统
```python
DatabaseMigrator
  ├─ 读取 database_schema.json (中央配置)
  ├─ 检查现有表结构
  ├─ 比对预期架构
  ├─ 自动添加缺失表
  ├─ 自动添加缺失列
  ├─ 自动创建 VIEWs
  └─ 版本一致性保证
```

#### 9 个数据库 VIEWs (统计和异常检测)
| VIEW | 用途 | v0.6 | v0.63 |
|------|------|------|-------|
| `vw_discontinuous_hbnb` | 缺失 HBNB 号 | ✗ | ✓ |
| `vw_home_accepted_counts` | 已接受乘客统计 | ✗ | ✓ |
| `vw_home_flags` | 删除乘客统计 | ✗ | ✓ |
| `vw_deleted_boarding_numbers` | 删除登机号列表 | ✗ | ✓ |
| `vw_hbnb_range` | HBNB 号码范围 | ✗ | ✓ |
| `vw_missing_boarding_numbers` | 缺失登机号 | ✗ | ✓ |
| `vw_duplicate_seats` | 重复座位 | ✗ | ✓ |
| `vw_duplicate_names` | 重复乘客名字 | ✗ | ✓ |
| `vw_asvc_seat_mismatches` | 座位不匹配 | ✗ | ✓ [v0.63新增] |

---

## 关键功能新增

### v0.63 中未在 v0.6 中存在的功能

#### 1. 完整的记录版本控制
```python
duplicate_record 表
├─ id (自增)
├─ hbnb_number (关键)
├─ original_hbnb_id (外键)
├─ record_content
└─ created_at (时间戳)
```
- 自动备份原记录
- 支持记录完整历史
- 时间戳追溯

#### 2. ASVC 座位提取和验证
```python
CHbpr.__GetAsvcSeat()
├─ 输入: ASVC 消息行
├─ 正则: r"SEAT/[A-Z]\s(\d{1,2}[A-Z])"
├─ 输出: 座位号 (e.g., "47J")
└─ 应用: 与 PAX 座位对比验证
```

#### 3. 命令版本管理
```sql
commands 表
├─ command_full (完整命令字符串)
├─ command_type (REBK/DOCO/等)
├─ version (版本号)
├─ parent_id (关联原始命令)
├─ is_latest (最新版本标志)
└─ 索引: (command_full, version), (parent_id), (is_latest)
```

#### 4. 远程数据库服务
```
memdb_port_server.py
├─ 独立的进程
├─ TCP 端口服务 (51201-51203)
├─ 多用户支持
├─ 认证机制
└─ 数据隔离
```

---

## 性能和扩展性

### v0.6 预期
- 单进程处理
- 小规模数据集 (~1000 条记录)

### v0.63 实现

#### 处理能力
| 指标 | v0.6 | v0.63 |
|------|------|-------|
| 单批处理 | ~100 条 | ~1000+ 条 |
| 记录历史 | 不支持 | 完整版本链 |
| 并发用户 | 1 | 多用户独立实例 |
| 数据一致性 | 基础 | 多层验证 |

#### 架构扩展性
- 从单进程 → 远程服务架构
- 从内存数据库 → 磁盘持久化 + 远程访问
- 从松散耦合 → 紧密集成系统

---

## 代码结构的转变

### v0.6 预期
```
scripts/
├─ hbpr_processor.py
├─ pr_processor.py
└─ database.py
```

### v0.63 实现
```
scripts/
├─ hbpr_file_processor.py (HBPR 文件解析)
├─ hbpr_info_processor.py (CHbpr 信息提取)
├─ pr_processor.py (PR 命令处理)
├─ record_processor.py (记录级处理)
├─ command_processor.py (命令处理)
├─ hbpr_database.py (数据库操作)
├─ database_migration.py (自动迁移)
├─ schema_utils.py (SQL 生成工具)
├─ database_schema.json (架构配置)
├─ data_cleaner.py (数据清理)
└─ excel_processor.py (Excel 导入)

remote_db/
├─ memdb_port_server.py (数据库服务)
├─ hbpr_database_client.py (客户端)
├─ db_port_client.py (端口通信)
└─ remote_sqlite_adapter.py (协议适配)

ui/
├─ process_records/
│  ├─ add_hbprs.py (HBPR/PR 导入)
│  ├─ edit_hbpr.py (记录编辑)
│  ├─ add_commands.py (命令添加)
│  ├─ edit_command.py (命令编辑)
│  └─ ...
├─ database/
│  ├─ hbpr.py (HBPR 管理页)
│  ├─ export.py (数据导出)
│  ├─ sort.py (排序查询)
│  └─ ...
└─ components/
   ├─ flight_summary.py
   ├─ home_flight_sheet.py
   ├─ main_stats.py
   └─ ...
```

**模块数:** 从 3 个 → 20+ 个专用模块

---

## 文件大小和复杂度

| 文件 | v0.6 预期 | v0.63 实现 | 行数 | 复杂度 |
|------|---------|---------|------|--------|
| hbpr_info_processor.py | ~200 行 | 853 行 | +353% | CHbpr 完整验证系统 |
| hbpr_database.py | ~300 行 | 1186 行 | +295% | 多层数据操作 + 迁移 |
| pr_processor.py | ~100 行 | ~350 行 | +250% | PR 合并 + 转换逻辑 |
| hbpr_file_processor.py | ~150 行 | ~280 行 | +87% | 文件解析 + 清理 |

---

## 部署和维护

### v0.6 预期
- 单一可执行文件
- 本地数据库文件
- 无特殊依赖

### v0.63 实现

#### 启动流程
```
1. 启动 memdb_port_server (远程数据库)
   ├─ 监听 51201-51203 端口
   └─ 初始化用户隔离实例

2. 用户认证
   ├─ SHA256 密码验证
   └─ 获取数据库客户端

3. 数据库初始化
   ├─ DatabaseMigrator 检查架构
   ├─ 自动添加缺失表/列/VIEWs
   └─ 加载飞行信息

4. 启动 Streamlit UI
   └─ 连接到已初始化的数据库
```

#### 依赖项
- Python 3.12.0
- SQLite 3.25.0+ (ROW_NUMBER() 支持)
- Streamlit (UI 框架)
- Pandas (数据处理)
- 可选: Gemma3 API (AI 编码功能)

---

## 预期偏离的工程原因

### 1. 数据完整性需求
**预期:** 基础数据存储  
**实现:** 35+ 个字段的结构化数据  
**原因:** HBPR 信息复杂，需要多维验证

### 2. 并发访问支持
**预期:** 单用户单进程  
**实现:** 远程数据库服务 + 多用户隔离  
**原因:** 实际使用场景需要多人协作

### 3. 数据历史追溯
**预期:** 覆盖写入  
**实现:** 完整的版本控制 + 时间戳  
**原因:** 审计和问题追踪需求

### 4. 自动化维护
**预期:** 静态表结构  
**实现:** DatabaseMigrator + 自动迁移  
**原因:** 避免手工维护 + 向后兼容

### 5. PR 命令处理
**预期:** 简单转换  
**实现:** 完整的合并、查询、融合系统  
**原因:** 实际 PR 命令复杂且经常重复

---

## 总结

从 v0.6 (演示版) 到 v0.63 (最终版)，系统演变从简单的单进程文件处理工具，变成了：

- **多层级数据处理和验证系统**
- **分布式数据库架构**
- **完整的版本控制和历史追溯**
- **自动化的数据库迁移**
- **企业级的错误分类和恢复**

这些变化反映了实际工程需求与初始设计预期的差异，但保持了系统的核心功能和可维护性。

---

**版本** v0.63  
**对标** v0.6 (演示版)  
**发布日期** 2025-10-21  
**状态** Production
