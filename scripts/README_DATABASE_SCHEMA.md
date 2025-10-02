# Database Schema Configuration System

## 概述 Overview

FlightCheckPy现在使用集中的JSON配置文件来管理数据库结构，统一所有迁移操作。

FlightCheckPy now uses a centralized JSON configuration file to manage database schema and unify all migration operations.

---

## 文件结构 File Structure

```
scripts/
├── database_schema.json          # 集中的数据库结构配置 Centralized schema config
├── database_migration.py         # 统一的迁移脚本 Unified migration script
├── schema_utils.py               # 结构工具类 Schema utilities
├── command_processor.py          # 使用统一迁移器 Uses unified migrator
├── hbpr_list_processor.py        # 使用JSON配置 Uses JSON config
├── hbpr_info_processor.py        # 使用JSON配置 Uses JSON config
└── commands_migration.py         # (已废弃可删除) Deprecated, can be removed
```

---

## 核心文件 Core Files

### 1. `database_schema.json`
集中的数据库结构配置文件，包含所有表的完整定义。

Centralized database schema configuration file containing complete definitions for all tables.

**结构 Structure:**
```json
{
  "version": "1.0",
  "tables": {
    "table_name": {
      "columns": [
        {"name": "column_name", "type": "TYPE", "constraint": "CONSTRAINT"}
      ],
      "indexes": [
        {"name": "index_name", "columns": ["col1", "col2"]}
      ]
    }
  }
}
```

**包含的表 Included Tables:**
- `flight_info` - 航班信息 Flight information
- `hbpr_full_records` - 完整HBPR记录（含39个字段） Full HBPR records (39 fields)
- `hbpr_simple_records` - 简单HBPR记录 Simple HBPR records
- `missing_numbers` - 缺失的HBNB号码 Missing HBNB numbers
- `duplicate_record` - 重复记录备份 Duplicate record backups
- `commands` - 命令记录（带版本控制） Commands with versioning

---

### 2. `database_migration.py`
统一的数据库迁移类，从JSON配置读取结构并执行迁移。

Unified database migration class that reads schema from JSON and executes migrations.

**主要类 Main Class:**
```python
class DatabaseMigrator:
    def __init__(self, conn: sqlite3.Connection, schema_file: str = None)
    def migrate_database(self, silent: bool = False) -> Dict[str, Any]
    def migrate_hbpr_table(self) -> bool
    def migrate_commands_table(self) -> bool
    def verify_migration(self) -> bool
    def get_schema_version(self) -> str
```

### 3. `schema_utils.py`
数据库结构工具类，提供从JSON生成CREATE TABLE语句等功能。

Database schema utility class that provides functions to generate CREATE TABLE statements from JSON.

**主要类 Main Class:**
```python
class SchemaUtils:
    def __init__(self, schema_file: str = None)
    def generate_create_table_sql(self, table_name: str) -> str
    def generate_all_create_table_sql(self) -> Dict[str, str]
    def get_table_columns(self, table_name: str) -> List[str]
    def get_table_indexes(self, table_name: str) -> List[Dict[str, Any]]
    def generate_create_indexes_sql(self, table_name: str) -> List[str]
    def get_all_table_names(self) -> List[str]
    def get_schema_version(self) -> str
```

**使用方法 Usage:**
```python
from scripts.database_migration import DatabaseMigrator
from ui.common import get_hbpr_database_client

db_client = get_hbpr_database_client()
conn = db_client.get_connection()
migrator = DatabaseMigrator(conn)

# 执行迁移 Execute migration
result = migrator.migrate_database()
if result['success']:
    print("迁移成功 Migration successful")

# 验证结构 Verify schema
if migrator.verify_migration():
    print("结构完整 Schema is complete")

# 获取版本 Get version
version = migrator.get_schema_version()
```

---

## UI集成 UI Integration

迁移功能已集成到Database Management页面。

Migration features are integrated into the Database Management page.

**位置 Location:** `ui/database/management.py`

**功能按钮 Feature Buttons:**
1. **🚀 一键迁移数据库** - 自动检测并迁移到最新版本
   - Auto-detect and migrate to latest version
2. **🔍 验证数据库结构** - 检查结构完整性
   - Check schema integrity
3. **ℹ️ 结构信息** - 显示当前结构版本
   - Display current schema version

---

## 迁移流程 Migration Process

### 自动迁移 Automatic Migration

1. 加载 `database_schema.json` 配置
   Load `database_schema.json` configuration
2. 检查每个表是否存在
   Check if each table exists
3. 对比现有列与配置中的列
   Compare existing columns with configured columns
4. 添加缺失的列
   Add missing columns
5. 创建必要的索引
   Create necessary indexes
6. 更新默认值
   Update default values
7. 自动保存数据库
   Auto-save database

### 手动迁移 Manual Migration

```python
from scripts.database_migration import DatabaseMigrator

# 使用自定义schema文件 Use custom schema file
migrator = DatabaseMigrator(conn, schema_file='path/to/custom_schema.json')
result = migrator.migrate_database(silent=False)
```

---

## 优势 Advantages

### ✅ 集中管理 Centralized Management
- 所有表结构定义在一个JSON文件中
  All table structures defined in one JSON file
- 易于查看和维护
  Easy to view and maintain

### ✅ 一致性 Consistency
- 所有脚本使用相同的配置源
  All scripts use the same configuration source
- 避免重复定义
  Avoid duplicate definitions

### ✅ 版本控制 Version Control
- JSON文件包含版本号
  JSON file includes version number
- 便于跟踪结构变化
  Easy to track schema changes

### ✅ 扩展性 Extensibility
- 添加新表只需修改JSON
  Add new tables by modifying JSON only
- 无需修改多个Python文件
  No need to modify multiple Python files

### ✅ 一键操作 One-Click Operation
- UI界面提供一键迁移按钮
  UI provides one-click migration button
- 自动完成所有迁移步骤
  Automatically completes all migration steps
- 所有脚本都使用统一配置
  All scripts use unified configuration

---

## 如何添加新字段 How to Add New Fields

### 步骤 Steps:

1. **编辑 `database_schema.json`**
   ```json
   {
     "tables": {
       "hbpr_full_records": {
         "columns": [
           {"name": "new_field", "type": "TEXT", "constraint": ""}
         ]
       }
     }
   }
   ```

2. **在UI中点击"一键迁移数据库"**
   Click "One-Click Migration" in UI
   
3. **完成！新字段已添加**
   Done! New field is added

---

## 兼容性 Compatibility

### 旧脚本 Legacy Scripts

`commands_migration.py` 现已被集成到 `database_migration.py` 中，可以安全删除。

`commands_migration.py` is now integrated into `database_migration.py` and can be safely removed.

### CommandProcessor

`CommandProcessor.migrate_to_timeline()` 现在调用统一的 `DatabaseMigrator`，保持向后兼容。

`CommandProcessor.migrate_to_timeline()` now calls the unified `DatabaseMigrator`, maintaining backward compatibility.

---

## 故障排除 Troubleshooting

### 问题：迁移失败
**Problem: Migration fails**

**解决方案 Solutions:**
1. 检查数据库连接是否正常
   Check if database connection is working
2. 查看错误信息中的具体失败原因
   Check error message for specific failure reason
3. 验证JSON格式是否正确
   Verify JSON format is correct
4. 确保数据库文件有写入权限
   Ensure database file has write permissions

### 问题：JSON解析错误
**Problem: JSON parsing error**

**解决方案 Solutions:**
1. 使用JSON验证器检查语法
   Use JSON validator to check syntax
2. 确保所有字符串使用双引号
   Ensure all strings use double quotes
3. 检查逗号和括号是否匹配
   Check commas and brackets match

---

## 未来计划 Future Plans

- [ ] 支持表之间的外键关系定义
      Support foreign key relationships between tables
- [ ] 添加数据迁移脚本（不仅是结构）
      Add data migration scripts (not just schema)
- [ ] 支持回滚到旧版本结构
      Support rollback to older schema versions
- [ ] 导出当前数据库结构为JSON
      Export current database schema to JSON

---

## 联系 Contact

如有问题或建议，请在项目中提出Issue。

For questions or suggestions, please create an Issue in the project.

