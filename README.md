# Flight Check --- Python 版本 0.61

## 项目简介

主要用于解析和验证 **HBPR** 数据

## 快速开始

### 环境准备

1. **下载项目**
   ```bash
   git clone https://github.com/gostnort/FlightCheckPy
   cd FlightCheckPy
   ```

2. **创建虚拟环境**
   ```bash
   python -m venv .venv
   .venv/scripts/activate  # Windows
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

### 运行应用

#### Web 界面
```bash
streamlit run ui/main.py
```
纯命令行会带有console messages。
  - 可以运行``start_ui.bat`` 这个是带有内网服务的启动命令。
  - 可以运行``start_ui.py`` 这个是没有console，提供了任务托盘图标的启动程序。

**注意**: 首次运行时会显示登录界面，需要管理员提供的有效凭据。

## 版本更新

### v0.61 新特性
- 🔐 **新增安全登录系统**: SHA256 加密的用户认证
- 🌐 Streamlit Web 界面
- 🗄️ 改进的数据库管理系统
- 🛡️ 分类的错误处理和报告
- 📊 数据源改为HBPR
- ✏️ 手动HBPR输入功能
- 🔄 记录替换
- 📈 自动缺失号码表更新
- 🫧 实时显示处理统计和缺失数据信息
- 💾 支持 CSV 和 Excel 格式的数据导出

### v0.51 特性
- 基于 PySide6 的桌面应用
- 行李限额信息解析优化
- 批量处理功能
- 数据源为PR

## 使用说明

1. **安全登录**: 使用管理员提供的凭据登录系统
2. **准备数据**: 确保 HBPR 数据文件格式正确
3. **选择界面**: 根据需要选择桌面应用或 Web 界面
4. **处理数据**: 使用相应的处理功能解析和验证数据
5. **查看结果**: 检查处理结果和错误报告
6. **导出数据**: 将处理结果导出为所需格式
7. **安全登出**: 使用完毕后及时登出系统

## 支持格式

- **输入**: HBPR 文本记录
- **输出**: CSV, 数据库记录
- **数据库**: SQLite

## 系统要求

- Windows Python 3.12
- 推荐使用虚拟环境

