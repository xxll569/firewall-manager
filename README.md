# 防火墙管理工具

基于 macOS **pf** 包过滤防火墙的轻量 Web 管理界面，用 Flask 驱动，无需依赖任何第三方防火墙客户端。

## 功能

- 查看 pf 防火墙的启用/禁用状态，一键切换
- 10 个常用服务（SSH / HTTP / HTTPS / MySQL / Redis 等）快速开放，再点即关
- 自定义规则：指定端口、协议（TCP/UDP）、方向（入站/出站）、来源 IP 或子网
- 规则列表实时展示，支持逐条删除
- 原始 pf 输出诊断面板

## 前置条件

| 要求 | 说明 |
|------|------|
| macOS | 使用系统内置的 `pfctl` 命令，仅支持 macOS |
| Python 3.8+ | 运行 Flask 服务 |
| sudo 权限 | 写入 `/etc/pf.anchors/fw-manager` 及重载 pf 规则需要 |

## 安装

```bash
# 进入工具目录
cd firewall-manager

# 创建虚拟环境（可选）
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
# 或
pip3 install -r requirements.txt
```

## 启动

```bash
sudo python app.py
#或
sudo python3 app.py
```

浏览器打开 **http://127.0.0.1:5001**

> 服务监听在 localhost，不会暴露到外网。

## 工作原理

所有规则写入独立 anchor 文件 `/etc/pf.anchors/fw-manager`，不修改系统默认 pf 规则。
首次添加规则时，会自动在 `/etc/pf.conf` 末尾注册 anchor 引用：

```
anchor "fw-manager"
load anchor "fw-manager" from "/etc/pf.anchors/fw-manager"
```

规则格式示例：

```
pass in proto tcp from any to any port 80
pass in proto tcp from 192.168.1.0/24 to any port 22
```

## 目录结构

```
firewall-manager/
├── app.py              # Flask 后端，端口 5001
├── firewall_core.py    # pf 操作核心逻辑
├── requirements.txt
├── static/
│   ├── app.js          # 前端交互
│   └── style.css       # 样式
└── templates/
    └── index.html      # 页面模板
```

## 注意事项

- macOS 重启后 pf 规则不会自动恢复，需要重新加载或配置 launchd
- `pf` 在 macOS 上默认处于**禁用**状态，需手动点击启用后规则才会生效
- 修改 `/etc/pf.conf` 需要 root 权限，操作前建议备份原文件
