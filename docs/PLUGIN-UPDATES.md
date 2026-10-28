# 插件安装来源与后续升级

## Nikki

本项目 V2.2 起按照 [Nikki 上游推荐的软件源方式](https://github.com/nikkinikki-org/OpenWrt-nikki/blob/main/README.zh.md) 安装。配置逻辑参考 [上游 feed.sh](https://github.com/nikkinikki-org/OpenWrt-nikki/blob/main/feed.sh)，不直接执行网络下载的 shell 脚本。

- 24.10：opkg 源模板为 `https://nikkinikki.pages.dev/openwrt-24.10/{arch_packages}/nikki`。
- 25.12：apk 源模板为 `https://nikkinikki.pages.dev/openwrt-25.12/{arch_packages}/nikki/packages.adb`。
- V3.0 中 arch_packages 取所选设备的官方元数据，并与 ImageBuilder 核对；源缺少对应分支/架构时明确失败，不混装。仅接受最新两代正式版本。

构建时将源加入 ImageBuilder，使用上游公钥检查软件源签名，再安装 Nikki、Mihomo 与中文管理界面。此路径不对 Nikki 包重签名，也不关闭签名检查。上游公钥下载哈希被锁定；公钥轮换时需审查后更新锁文件。

固件保留上游源和公钥：

| 系统 | 源文件 | 公钥 |
| --- | --- | --- |
| opkg | `/etc/opkg/customfeeds.conf` | `/etc/opkg/keys/` 中上游 usign 指纹文件 |
| apk | `/etc/apk/repositories.d/customfeeds.list` | `/etc/apk/keys/nikki.pem` |

因此不必首次启动再添加源。可在 LuCI 的软件包界面刷新列表、选择 Nikki 相关包更新；也可按当前包管理器更新指定组件：

```sh
# 24.10 / opkg：先备份插件配置，再按需执行
opkg update
opkg upgrade mihomo-meta nikki luci-app-nikki luci-i18n-nikki-zh-cn
```

```sh
# 25.12 / apk：先备份插件配置，再按需执行
apk update
apk upgrade mihomo-meta nikki luci-app-nikki luci-i18n-nikki-zh-cn
```

这些命令只针对插件组件，不是整套 OpenWrt 系统升级命令。更新后的插件行为与兼容性仍以上游说明为准。不要把 24.10 源直接改成 25.12 源；系统跨版本升级应重新构建相应固件。

这是 **Nikki 作者的软件源**，不是 OpenWrt 官方软件源。它是滚动源；本次装入的确切版本在 `.manifest` 中，后续构建可能得到更新版本。

## OpenClash

OpenClash 每次构建查询 [作者最新正式发布](https://github.com/vernesong/OpenClash/releases/latest)，按当前包管理器选择 IPK/APK。Mihomo 选择与实际 CPU 匹配的保守 ISA 核心，并核对 ELF 类别、字节序和机器类型。未知架构不回退 amd64。解析后的固定 URL、标签及上游资产 SHA256 记录在 build-info.json；缺少匹配资产或校验值时失败，不降级到旧版。Nikki 仍使用对应分支源的最新可用组件，不强行替换核心。

运行后可使用 OpenClash 自带的插件/核心更新机制，按作者说明操作。本项目不为它添加未经上游确认的软件源，也不把它描述为已从 OpenWrt 官方源安装。更新软件、核心或规则数据前，先备份配置，并遵守这些组件各自的许可证。

第三方版权与源码入口见 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。
