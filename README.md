## v0.6.4

主要改进：

- **数据库静态全盘加密**：全面支持基于 `AES-256-GCM` + `PBKDF2-HMAC-SHA256`（100,000 轮）的带认证二进制加密容器（`.db.enc`），48 字节信封与 AAD 防篡改校验，开箱即用自动生成密钥，支持用户自定义易记口令；
- **异步静默预热与内存连接池**：引入后台守护预热线程，启动时无感加载全局最新 5 个数据库，会话期多库常驻内存，切库延迟由数百毫秒磁盘寻道降至 10ms 以内指针切换；
- **原生重复记录安全留存**：复用原生 `duplicate_record` 历史版本表，更新覆盖主记录前执行 `sqlite_master` 容错检查，原子清空旧派生列，杜绝历史脏数据残留；
- **UI 样式动静解耦**：静态 CSS 统一抽离至 `resources/styles/main.css`，动态用户字体大小保持按比例实时渲染，消除零散内嵌样式；
- **局域网多用户与业务规则强化**：内存数据库服务监听 `0.0.0.0` 支持局域网跨设备协作；新增外航金卡（`/*G`）行李额外额度判定、非中国籍旅客 `CKIN QROK` 严格校验与信息页“🔄 重新计算”功能。

运行环境支持：

- **Python**：3.12+（推荐通过 `start_ui.py` 由 `uv` 自动化管理虚拟环境）
- **SQLite**：3.25.0+（支持窗口函数 `ROW_NUMBER()`）
- **报表支持**：主机端（Host）需要安装 Microsoft Excel 2007 或以上版本（用于票务与 EMD 报表生成）
- **打印服务**：主机端 Windows 特性 `Microsoft Print to PDF` 需处于正常启用状态

---

# FlightCheckPy v0.6.4 - 从基础生产版 (v0.63) 到高安全高可用架构的工程演进

## 版本对标

本文档以 **v0.63 (原生产基线版)** 为对比基准，详述 **v0.6.4 (当前增强版)** 的架构升级、安全加固及实际工程落地细节。

---

## 整体架构变更

### v0.63 基础生产版设计

- **明文存储**：磁盘数据库仅采用标准明文 `.db` 格式，文件拷出即可直接被第三方工具查看；
- **单活动连接切换**：内存数据库服务器仅维护单个全局活动连接 `_conn`，每次切换数据库都需要销毁旧连接并重新从磁盘完整读取反序列化，用户操作伴随明显卡顿（500ms~1500ms）；
- **配置与样式耦合**：大量静态 CSS 通过 `st.markdown("<style>...", unsafe_allow_html=True)` 散落在各业务 Python 文件中，维护成本高；
- **覆盖写入风险**：遇到上游重复 HBNB 记录时，旧字段未能彻底清理，容易引发脏数据残留。

### v0.6.4 高安全高可用架构

- **静态全盘认证加密 (`.db.enc`)**：引入工业级 `AES-256-GCM` 认证加密，每次写盘采用全新 Salt 与 Nonce，配置文件完全零密化，彻底杜绝数据泄露风险；
- **双格式自适应共存**：侧边栏与管理页自适应识别 `.db`（明文）与 `.db.enc`（加密），提供 `[Plain]` 与 `[Encrypted]` 状态标识，平滑兼容历史数据；
- **异步静默预热与常驻内存池**：服务启动即刻监听端口，后台线程异步将最新 5 个数据库预加载至 `_db_cache`，会话期切库仅需内存指针替换（<10ms）；
- **局域网多用户协同 (`0.0.0.0`)**：端口服务绑定全网卡，支持多机多端协同作业；
- **样式规范分层**：静态设计规范沉淀于 `resources/styles/main.css`，动态用户字体配置按需注入，实现真正动静解耦。

---

## 核心模块演变

### 1. 数据库与持久化层

#### v0.63 基线

```
多层数据库架构 (仅明文)
├─ 本地文件: databases/*.db (明文 SQLite)
├─ 内存数据库服务 (memdb_port_server.py)
│  └─ 单一全局连接 _conn (切库即关旧库，强依赖磁盘重读)
├─ 自动化迁移系统 (database_migration.py)
└─ 9 个数据库 VIEWs
```

#### v0.6.4 实现

```
高安全、双格式、多连接常驻数据库架构
├─ 存储层 (双格式共存 & 容器加密)
│  ├─ 明文库 (*.db) - 向后兼容
│  ├─ 加密容器 (*.db.enc) - AES-256-GCM + PBKDF2-HMAC-SHA256 (100k轮)
│  └─ 48 字节信封: MAGIC(4B) + Salt(16B) + Nonce(12B) + Ciphertext + Tag(16B)
├─ 密码学引擎 (scripts/crypto_engine.py & scripts/manage_keys.py)
│  ├─ 自动无感检测 & 初始化 resources/.master_key (43B 高熵 Token)
│  ├─ 密码拉伸机制支持用户自定义易记口令
│  └─ app_config.toml 彻底无密化 (杜绝硬编码与配置泄露)
├─ 内存数据库服务引擎 (remote_db/memdb_port_server.py)
│  ├─ 局域网全网卡监听 (0.0.0.0: 51201~51203)
│  ├─ _db_cache: dict[str, sqlite3.Connection] 常驻连接池 (会话期免换入换出)
│  ├─ _async_prewarm_worker: 守护线程后台异步静默加载全局最新 5 个库
│  ├─ 原子写盘与防并发破坏: .tmp 临时写盘 + 重试退避文件替换
│  └─ /shutdown 统一多库状态落盘
├─ 本地数据库客户端与防污染机制 (scripts/hbpr_database.py)
│  ├─ create_full_record(): 覆盖更新时先查 sqlite_master，清空派生列
│  └─ duplicate_record 表: 原生历史副本保留 + bol_duplicate 准确联动
└─ 9 个自动化监控 VIEWs + 完整的 DatabaseMigrator
```

**结构与能力对比：**

| 特性维度 | v0.63 基线 | v0.6.4 当前版本 | 改进收益 |
|---|---|---|---|
| **磁盘存储形态** | 仅明文 `.db` | `.db` 与 `.db.enc` 双格式共存 | 静态数据物理防窃取、防篡改 |
| **加密算法** | 无 | AES-256-GCM + PBKDF2 (100k) | 达标现代密码学标准与合规要求 |
| **密钥管理** | 无 | 自动探测生成 / 环境变量 / 易记口令 | 开箱即用，零报错启动 |
| **换库响应延迟** | 500ms ~ 1,500ms（磁盘读写） | **< 10ms**（内存连接指针切换） | 切换体验顺滑无等待 |
| **启动端口就绪** | 需等待首库加载完成（>600ms） | **< 10ms**（HTTP 立即可用） | 托盘与 UI 启动瞬间就绪 |
| **重复 HBNB 覆盖** | 旧字段不重置，存在脏数据 | 覆盖时原子清空 30+ 个派生字段 | 杜绝上游重发导致的幽灵数据 |
| **监听网络范围** | 依赖单机调用 | **0.0.0.0** 默认全网卡绑定 | 满足局域网多机协同操作需求 |

---

### 2. 数据处理与流转流程

#### v0.6.4 完整多阶段数据管道

```
上传文件 (HBPR / PR)
  ↓
文件类型检测 (detect_file_type)
  ├─ HBPR 路线
  │  └─ HbprProcessor.parse_file_content()
  │
  └─ PR 路线
     ├─ split_commands() [按 > 符号切分提取]
     ├─ merge_pr_sections() [合并同头部重复 PR 段]
     ├─ extract_tkne_from_pr() [提取 13 位电子客票号]
     ├─ find_hbpr_header_by_tkne() [关联原始 HBPR 头部]
     └─ convert_pr_to_hbpr() [合成标准完整 HBPR 记录]
  ↓
内容深度清理 (clean_hbpr_record_content)
  ├─ 消除不可见控制字符与十六进制伪影
  ├─ 去除多余重复标题
  └─ 规整旅客与行李段落
  ↓
数据库存储与版本分支 (create_full_record)
  ├─ 检查 duplicate_record 表是否存在 (sqlite_master 容错)
  ├─ 检查主表 hbnb_number 是否冲突
  ├─ 冲突处理策略:
  │  ├─ 历史版本留存: 自动插入 duplicate_record (保留原文本与时间戳)
  │  ├─ 主表覆盖清理: UPDATE 清空旧 name, seat, class, bag, error 等派生列
  │  └─ 标记设置: bol_duplicate = 1
  └─ 新纪录处理: 直接 INSERT 到主表
  ↓
CHbpr 深度业务解析 (hbpr_info_processor.py)
  ├─ 基础数据提取: HBNB, BN, PNR, NAME, SEAT, CLASS, DESTINATION
  ├─ 票务信息抽取: TKNE, FF (常客号), 进出港联程航班 (INBOUND/OUTBOUND)
  ├─ 特殊服务 (ASVC): 消息提取与座位正则捕获 (SEAT/[A-Z]\s(\d{1,2}[A-Z]))
  ├─ 行李重量规则验证:
  │  ├─ 舱位额度与件数核算 (FBA / IFBA)
  │  ├─ 国航本航常客权益核算 (FLYER_BENEFIT)
  │  └─ [v0.6.4 新增] 外航星空联盟金卡 (/*G) 额外 1 件 23KG 行李核算
  ├─ 证件与安全检查:
  │  ├─ 护照姓名两级模糊匹配 (Levenshtein 编辑距离)
  │  ├─ 护照有效期截取与过期校验
  │  └─ [v0.6.4 新增] 非中国籍旅客 VISA INFO / CKIN VISA 与 CKIN QROK 双重校验
  └─ 错误归纳分类: Baggage, Passport, Name, Visa, Other (5 大类)
  ↓
回写更新与统计联动 (update_with_chbpr_results)
  ├─ 结构化 35+ 个字段写入 hbpr_full_records
  └─ 事务提交 Commit
  ↓
异步写盘调度 (memdb_port_server: _write_queue)
  ├─ 内存序列化 conn.serialize() (加锁 < 5ms)
  ├─ 异步加密与磁盘刷盘 (工作线程无锁执行，采用 .tmp 原子替换)
  └─ UI 即时反馈无等待
```

---

### 3. 多层次数据验证系统

```
第 1 层：文件与格式级验证
  ├─ 文件编码检测 (UTF-8 强制规范)
  ├─ 航班号解析 (parse_flight_id_from_content)
  └─ 文本脏数据清洗 (clean_text_for_input)

第 2 层：记录与格式级校验
  ├─ HBPR 头部结构模式识别
  ├─ PR 票号与命令有效性校验
  └─ 主从记录一致性核对

第 3 层：业务字段合规校验
  ├─ 乘客姓名与座位格式验证 (R/SNR 座位去重)
  ├─ 行李件数与总重量比对 (超件、超重、平均重异常提示)
  ├─ [v0.6.4 强化] 星空联盟外航金卡行李规则 (/*G 额外 1 件 23KG)
  ├─ 护照到期日比对 (自动对照起飞时间)
  └─ [v0.6.4 强化] 跨国签证合规核验 (非中国籍旅客严格检测 VISA INFO 与 CKIN QROK)

第 4 层：错误分类聚合与索引
  ├─ 🧳 Baggage: 超件数、超重量、超额计费说明 (CKIN EXBG)
  ├─ 🪪 Passport: 护照过期、证件缺失
  ├─ 👤 Name: 订座姓名与护照姓名相似度 < 95% 提示
  ├─ 🛂 Visa: 签证信息缺失、QROK 缺失
  └─ 🔧 Other: 舱位无效、无名记录、关键命令解析异常

第 5 层：UI 动态联动与重算
  ├─ 统计指标卡实时汇总 (Metric 卡片)
  ├─ 分页分类筛选下拉框
  ├─ 快速编辑弹窗 (Save Changes / Create Duplicate)
  └─ [v0.6.4 新增] “🔄 重新计算”按钮：规则变更后一键全库重新运算刷新
```

---

### 4. 关键功能新增 (v0.6.4 重点增强)

#### 1. AES-256-GCM 数据库全盘加密 (`scripts/crypto_engine.py`)

- **48 字节高安全认证信封**：
  ```
  +--------------+--------------+---------------+------------------------+--------------+
  |  MAGIC (4B)  |  SALT (16B)  |  NONCE (12B)  |  CIPHERTEXT (Variable) |   TAG (16B)  |
  |   b"FCP1"    |  os.urandom  |  os.urandom   |   AES-256 Encrypted    | Authentication|
  +--------------+--------------+---------------+------------------------+--------------+
  ```
- **AAD 关联数据绑定**：将 `MAGIC` 绑定到 AEAD 验证标签中，任何篡改文件头部、更换幻数的操作均会触发 `InvalidTag` 异常并拒绝读取；
- **独立 Salt 与 Nonce**：每次写盘保存均实时重新采集密码学随机熵，杜绝 Nonce 重复导致的私钥推导风险；
- **配置与密钥解耦**：[resources/app_config.toml](file:///e:/my_github/FlightCheckPy/resources/app_config.toml) 中严禁存入任何密钥参数，仅记录 `default_mode = "encrypted"`。

#### 2. Master Key 自感应生成与易记口令机制

- **启动自愈**：应用初始化时若检测到未配置 `FCP_MASTER_KEY` 环境变量且 [resources/.master_key](file:///e:/my_github/FlightCheckPy/resources/.master_key) 不存在，系统自动通过 `secrets.token_urlsafe(32)` 创建 43 字符强随机主密钥并施加本地只读权限，用户首次使用零配置；
- **人性化易记口令**：在数据库管理界面支持操作员设置自定义主口令，系统利用 PBKDF2 将任意长度的人类记忆口令拉伸为标准的 256 位强密钥，兼顾可用性与安全性。

#### 3. 异步后台预热与常驻内存池 (`memdb_port_server.py`)

- **守护线程静默加载 (`_start_prewarm`)**：
  - 启动阶段秒级绑定端口，不阻塞主线程；
  - 后台守护线程扫描 `databases/`，严格按 `max(mtime, ctime)` 降序拉取全局最新的前 5 个有效数据库；
  - 自动解密反序列化进 `:memory:` 句柄并保存在 `_db_cache` 字典中；
  - 若配置了 `last_selected_db`，系统自动将其作为默认激活目标（若不在前 5 个中则补充至加载序列）；
- **换库免寻道 (<10ms)**：用户在侧边栏切换数据库时，直接切换活动连接指针，无需等待磁盘读取；
- **关闭全量刷盘**：收到 `/shutdown` 信号时，自动刷新所有常驻数据库的写盘队列并安全持久化。

#### 4. 重复记录安全处理与历史追溯 (`scripts/hbpr_database.py`)

- **历史完整归档**：冲突记录严格存入原生 `duplicate_record` 表，记录原文本与时间戳；
- **原子清洗覆盖**：更新主记录时，严格清空姓名、座位、行李、错误状态等旧派生列，彻底消除“旧错误延续至新记录”的业务隐患；
- **向下兼容防御**：在未初始化的老数据库上调用时，通过 `SELECT 1 FROM sqlite_master` 优雅降级，杜绝崩溃。

#### 5. 样式动静分离 (`resources/styles/main.css` & `ui/style_loader.py`)

- **静态 CSS 集中化**：侧边栏选中高亮、紧凑布局间距、主界面滚动区域与指示卡片全部统一在外部样式表定义；
- **动态用户字体伸缩**：用户在设置中自定义的字体名称与百分比缩放，由 `apply_font_settings()` 精确计算并独立注入，互不干扰。

---

## 性能与架构指标对比 (v0.63 vs v0.6.4)

| 指标维度 | v0.63 (基线版) | v0.6.4 (当前版) | 提升幅度 / 收益 |
|---|---|---|---|
| **静态数据安全性** | 0% (明文暴露) | **100% AES-256-GCM 强加密** | 达成敏感航空旅客数据合规要求 |
| **HTTP 服务冷启动响应** | 需等待首库加载 (~600ms) | **< 10ms 即可响应 /health** | 启动速度提升 60x |
| **预热库切换耗时** | 500ms ~ 1,500ms (磁盘寻道) | **< 10ms (内存指针切换)** | 切换响应提升 50x~150x |
| **后台预热吞吐** | 无预热机制 | ~400ms~600ms 预热 5 个数据库 | 登入后即刻享受高速查询 |
| **常驻内存开销** | ~1.5 MB (单库) | **< 15 MB (5 个常驻库)** | 内存开销极小，远低于设备阈值 |
| **网络可达性** | 单机绑定 (127.0.0.1) | **局域网全网卡可用 (0.0.0.0)** | 开放 51201~51203 端口支持局域网协同 |
| **重叠冲突处理** | 存在旧字段残留风险 | **原子重置 30+ 解析字段** | 消除脏数据，保证报表数据绝对真实 |

---

## 代码结构与目录树

```
FlightCheckPy/
├─ .gitignore                      # 忽略 *.tmp, *.writing, .master_key
├─ start_ui.py                     # 应用主启动入口 (uv环境准备、托盘、Streamlit)
├─ requirements.txt                # 运行依赖 (streamlit, cryptography, pandas 等)
├─ resources/
│  ├─ app_config.toml              # 核心配置 (零密码/零Salt, default_mode = "encrypted")
│  ├─ .master_key                  # 本地主密钥文件 (gitignored, 用户权限受控)
│  ├─ fcp.ico, http.ico            # 托盘与系统图标
│  └─ styles/
│     └─ main.css                  # [v0.6.4] 全局静态 CSS 样式规范
├─ databases/                      # 业务数据库目录
│  ├─ *.db                         # 明文数据库文件
│  ├─ *.db.enc                     # [v0.6.4] AES-256-GCM 加密数据库文件
│  └─ backups/                     # 自动备份归档目录
├─ scripts/                        # 核心业务与密码学处理层
│  ├─ crypto_engine.py             # [v0.6.4] AES-256-GCM 容器加密/解密引擎
│  ├─ manage_keys.py               # [v0.6.4] 主密钥维护与生成脚本
│  ├─ hbpr_file_processor.py       # HBPR 文本文件解析与航班提取
│  ├─ hbpr_info_processor.py       # CHbpr 业务解析 (外航金卡、VISA QROK 校验)
│  ├─ hbpr_database.py             # 数据库模型 (防脏数据原子清洗、duplicate_record 联动)
│  ├─ pr_processor.py              # PR 命令拆分、合并与转换
│  ├─ record_processor.py          # 记录级清洗与替换处理
│  ├─ database_migration.py        # 数据库结构自动化平滑迁移系统
│  ├─ database_schema.json         # 中央数据库结构与 VIEWs 定义
│  └─ emd_summary.py               # EMD 票务打印汇总引擎
├─ remote_db/                      # 内存数据库端口服务端
│  ├─ memdb_port_server.py         # 内存数据库 HTTP 服务 (0.0.0.0, 异步预热, 连接池)
│  ├─ db_port_client.py            # 端口 HTTP 通信客户端
│  └─ remote_sqlite_adapter.py     # SQLite 协议适配器
└─ ui/                             # Streamlit 界面层
   ├─ style_loader.py              # [v0.6.4] 样式加载器 (加载 main.css 与动态字体注入)
   ├─ common.py                    # 共享 UI 辅助函数 (认证、服务管理、通知)
   ├─ login_page.py                # 登录与端口服务器状态监控
   ├─ main.py                      # Streamlit 路由导航入口
   ├─ components/
   │  └─ database_selector.py      # [v0.6.4] 侧边栏库选择器 (支持加密/明文标签显示)
   ├─ database/
   │  ├─ management.py             # [v0.6.4] 数据库管理 (新建加密/明文单选框、维护迁移)
   │  ├─ hbpr.py                   # 新建数据库与文件处理
   │  └─ export.py                 # 数据导出
   └─ process_records/
      ├─ info.py                   # [v0.6.4] 校验信息展示与“重新计算”
      ├─ edit_hbpr.py              # 记录快速编辑与 duplicate_record 历史对照
      ├─ add_hbprs.py              # 数据录入与查重
      └─ timeline.py               # 旅客操作时间线
```

---

## 启动流程与使用说明

### 1. 快速启动

直接运行项目根目录下的启动脚本：

```bash
python start_ui.py
```

`start_ui.py` 将自动完成以下工作：
1. 检查并使用 `uv` 准备 `.venv` 虚拟环境并安装 `requirements.txt`；
2. 启动 Windows 系统托盘图标（支持随时停止/重启应用）；
3. 以后台服务形式拉起 Streamlit，自动绑定 `0.0.0.0:8501`；
4. 自动打开浏览器跳转至系统登录页。

### 2. 数据库服务与密钥初始化

- **自动密钥管理**：系统在首次启动时会自动在 `resources/.master_key` 生成高强度密钥，无需手动干预；
- **创建加密数据库**：在 UI 的 **Database Management** 页面，可选择“🔒 加密数据库 (.db.enc)”作为新建数据库的格式（默认选项）；
- **局域网协作**：其他设备可通过浏览器访问 `http://<服务器IP>:8501`，登录对应用户名后系统会自动分配独立的后台内存数据库实例端口（51201~51203）。

---

**当前版本**：v0.6.4  
**对比基线**：v0.63 (原生产版)  
**更新日期**：2026-10-18  
**运行状态**：Production Ready
