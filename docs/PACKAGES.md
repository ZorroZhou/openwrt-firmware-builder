# 额外官方软件包速查

不知道填什么时，**留空即可**。`standard` 已包含中文 LuCI HTTPS、curl 和基础证书；Docker、OpenClash、Nikki 请直接用各自选项，不必重复填写。

额外包是“在基础预设上追加”，不替换基础系统。填写包名，用空格分隔，不填写版本号、`.ipk`/`.apk` 后缀、安装命令或下载链接。

| 用途 | 可填写包名 | 说明 |
| --- | --- | --- |
| 查看 CPU/内存/进程 | `htop` | 交互式终端进程查看 |
| 测试局域网吞吐 | `iperf3` | 需另一台设备运行测试端，不代表互联网测速 |
| 轻量抓包 | `tcpdump-mini` | 用于网络排查；完整 tcpdump 与精简版不要同时添加 |
| DNS 排查 | `bind-dig` | 提供 dig 命令 |
| 磁盘分区信息 | `lsblk` | 查看块设备结构 |
| 挂载配置管理 | `block-mount` | 提供 OpenWrt 挂载配置支持 |
| ext 文件系统工具 | `e2fsprogs` | 使用前了解相应操作的影响 |

可直接复制的网络排查组合：

```text
htop iperf3 tcpdump-mini bind-dig
```

如果只想多装一个进程查看工具，填 `htop` 就够了。包越多，空间和依赖越多；不必把表格全部安装。

## 查找更多包

- [OpenWrt 官方软件包说明与索引入口](https://openwrt.org/packages/start)。
- [官方 Firmware Selector](https://firmware-selector.openwrt.org/)：选择对应版本和 x86/64 Generic 后，可查看默认 Installed Packages。
- [官方版本列表](https://downloads.openwrt.org/.versions.json)：确认当前完整版本。
- [官方下载目录](https://downloads.openwrt.org/releases/)：进入该版本 `packages/x86_64/` 查看 `base`、`packages`、`luci` 等软件源。内核模块位于对应 `targets/x86/64/` 的软件源中，必须匹配内核。

`luci-app-*` 一般是网页管理插件，中文翻译通常是对应的 `luci-i18n-*-zh-cn`，但并非所有插件或所有版本都有翻译包。通过额外包添加 LuCI 组件时，本项目会补齐 LuCI HTTPS 和基础中文；自选插件的翻译包请按官方索引确认后一起添加。

内置 Docker 选项已经带中文 Dockerman；内置 Nikki 已选择中文翻译包；OpenClash 的中文资源随其上游软件包提供。它们不需要在额外包栏重复填写。

不同版本可用包名及依赖可能变化。构建时由该版本官方源解析；包不存在或冲突时会明确失败，不会悄悄省略。安装来源、已安装包清单和校验值保存在固件 Artifact 中。
