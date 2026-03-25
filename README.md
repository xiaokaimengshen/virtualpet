<h1 align="center">
  猫猫桌宠 | Virtualpet
</h1>

<p align="center">
  猫猫桌宠 (Virtualpet) 是一个基于 PySide6 的桌面宠物开发框架，致力于为开发者提供创造桌面宠物的底层软件。
</p>

<p align="center">
  <a>
    <img src="https://img.shields.io/github/license/ChaozhongLiu/DyberPet.svg">
  </a>
  <a style="text-decoration:none">
    <img src="https://img.shields.io/github/downloads/ChaozhongLiu/DyberPet/total.svg"/>
  </a>
  <a style="text-decoration:none">
    <img src="https://img.shields.io/badge/python-3.9+-blue.svg" />
  </a>
  <a style="text-decoration:none">
    <img src="https://img.shields.io/badge/DyberPet-v0.7.7-green.svg"/>
  </a>
</p>

<p align="center">
简体中文 | <a href="README_EN.md">English</a>
</p>

![Interface](https://raw.githubusercontent.com/ChaozhongLiu/DyberPet/main/docs/DyberPet.png)

目前项目正在开发桌宠新功能，非常需要更多伙伴的加入。  
如果你有意向加入，请在b站搜索私信我(小恐龙_QAQ)。欢迎一起构建框架 🥰

如果你喜欢这个桌宠程序，请点击右上角的 ⭐ STAR，这对我们有很大的激励。

03-25-2026: v0.8.0 程序源码已上传，程序也已打包上传，有任何问题欢迎向我反馈。

## 下载与运行教程
### 1. 下载项目
1. 打开仓库主页：<https://github.com/xiaokaimengshen/virtualpet>
2. 点击 `Code` -> `Download ZIP`
3. 解压到本地任意目录

### 2. 安装依赖（Windows/macOS 通用）
建议使用 Python 3.9+，并在项目根目录执行：

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS:

```bash
source .venv/bin/activate
```

安装依赖：

```bash
pip install --upgrade pip
pip install tendo pyside6==6.5.2 PySide6-Fluent-Widgets==1.5.4 pynput apscheduler
```

### 3. 启动程序
在项目根目录执行：

```bash
python run_DyberPet.py
```

Windows 也可以直接双击 `run_debug.bat` 启动调试运行。

## 素材与模组合集
[这里](docs/collection.md)收录了现有角色、物品模组和迷你宠物，其介绍及下载链接。  
欢迎下载并通过 App 导入。

## 用户手册
猫猫桌宠使用说明：

1. 使用说明查看：右键桌宠 -> 使用说明。
2. 首次启动建议先启用联网大模型并配置 API 密钥。  
配置路径：右键桌宠 -> 系统 -> 设置 -> AI 大模型。
3. 互动方式：点击、拖拽桌宠。  
点击桌宠有概率获得啵币或触发特殊事件。
4. 属性值：
- 等级：每过一段时间自动变化。
- 饱食度：会缓慢消耗，桌宠饿的时候概率自己吃饭，建议手动喂食。饱食度为零时，桌宠死亡，无法恢复数据。
- 好感度：互动、吃饭等可增加好感度，能解锁更多动作与玩法。
5. 右键后的操作：
- 角色面板：状态、背包、商店、任务、动画、日记。
- 系统：开机自启、语音、大模型、关于。

## 开发者文档

### 素材开发
研究中...

### 功能开发
开发中...

## 更新日志
<details>
  <summary>版本更新列表</summary>

**v0.8.0 - 03/25/2026**
> 版号更新、新增开发日志，使用教程  
> UI 界面优化、参数优化  
> 角色面板-背包食物允许拖动喂食  
> 角色面板-新增日记本  
> 系统-新增开机自启动选项 + 版本功能迁移与优化  
> 修复移至侧边栏时气泡框显示正上方而被挡住问题  
> 修复侧边栏错位吸附问题

**v0.7.8 - 03/23/2026**  
先锋测试版发布

</details>

## 致谢
- 源码框架基于呆啵宠物 [呆啵宠物 | DyberPet](https://github.com/ChaozhongLiu/DyberPet#GPL-3.0-1-ov-file)，感谢作者大大 [ChaozhongLiu](https://t.bilibili.com/1174719726373306402?share_source=pc_native) 的指导和帮助。


