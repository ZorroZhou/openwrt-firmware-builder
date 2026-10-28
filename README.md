# OpenWrt Firmware Builder V2.1

在 GitHub Actions 中选择版本、分区、管理 IP、Docker 和代理插件，使用**官方 OpenWrt ImageBuilder**组装 x86-64 固件。保留官方内核及软件源；第三方插件独立锁定版本。平台暂只支持 x86-64。

## 使用方法

打开仓库 **Actions → Build OpenWrt → Run workflow**，选择参数后运行。首次使用推荐 `最新大版本 / 1024 / standard`，其他功能按需开启。运行摘要、Artifact 的 `ACCESS.md` 和 Release 正文都会列出实际版本、管理地址及初始登录说明。

| 参数 | 含义 |
| --- | --- |
| version | `最新大版本` / `上一大版本` / `上两个大版本`，每次运行从官网解析对应最新稳定补丁 |
| target | 仅 `x86-64`，对应官方目标 `x86/64` 和 Profile `generic` |
| rootfs_mb | 256 / 512 / 1024 / 2048 / 4096 MiB；Docker 或代理至少 512 MiB，推荐 1024 以上 |
| preset | `minimal`=官方基础包；`standard`=基础包追加 LuCI HTTPS、基础简体中文、curl、证书，推荐普通用户选择 |
| lan_ip | 留空使用 `192.168.1.1`；或填写私网 IPv4，例如 `192.168.31.100`，固定 /24；下载前校验 |
| docker | Docker + 中文 Dockerman + 中文 LuCI HTTPS，默认关闭 |
| proxy | `none` / `openclash` / `nikki`，互斥；Nikki 目前仅有锁定的 24.10/25.12 兼容包，23.05 选择 Nikki 会提前拒绝 |
| extra_packages | 可留空；常用包名、用途和复制示例见 [软件包速查](docs/PACKAGES.md)；最多 64 个，只允许添加包 |
| publish_release | 默认关闭；开启后在构建和上传成功后发布独立 GitHub Release |

这些预设都是“追加包”，不会裁剪官方基础系统。`minimal` 本身不额外安装网页界面；开启 Docker、代理或手动追加 LuCI 组件时，会补齐 LuCI HTTPS 和基础中文。Docker 带 `luci-i18n-dockerman-zh-cn`；Nikki 带 `luci-i18n-nikki-zh-cn`；OpenClash 的简体中文资源随上游包提供，构建会检查其存在。语言显示遵循浏览器/LuCI 自动语言设置。

开启代理时自动补充相应防火墙后端的透明代理依赖和 `dnsmasq-full`，移除精简版 `dnsmasq`。包依赖由当前版本 ImageBuilder 解析，缺包或冲突会失败。

成功后在运行页面 **Artifacts** 下载固件，保留 14 天。开启 Release 发布时，还可在仓库 **Releases** 下载。固件包包含 BIOS/EFI 两种引导、ext4/squashfs 两种文件系统，共四个完整磁盘镜像。

管理 IP 只改变 LAN 的 IPv4 地址和 /24 掩码，不自动配置旁路由网关、DNS、WAN 或关闭 DHCP。它是通用路由固件定制，不是完整的旁路由配置向导。不要让新测试虚拟机与家庭主路由同时在同一 LAN 提供 DHCP。

GitHub 原生输入框不能实时做自定义地址校验；工作流启动后、下载工具前，会拒绝错误格式、IPv6、网址、带端口/掩码的输入、公网/回环地址，以及 /24 中 `.0`、`.255`。开启 Docker 时还会拒绝其默认 `172.17.0.0/16` 网段。校验不能检测你真实网络中是否已有设备占用这个地址。

全新写入固件的初始用户名为 **root**，密码**未设置（空密码）**；首次登录后自行设置。项目不放入共享默认密码，也不会把个人密码发布到 Release。保留旧配置升级时，地址和密码以原配置为准。登录依据见 [官方初次登录说明](https://openwrt.org/docs/guide-quick-start/walkthrough_login)。

代理插件和核心已预装，但首次启动保持关闭。进入 LuCI 导入自己的配置/订阅，检查网络和 DNS 后再启用。项目不接收订阅密钥，不把订阅或密码放入 Actions 参数、日志和公开 Release。OpenClash 的规则数据库、面板等运行数据按其配置在使用时获取。

Docker 的镜像、容器数据同样占用磁盘；512 MiB 只是构建门槛。生产使用应规划较大数据盘，并在运行系统中配置 Docker 数据目录。

4096 MiB 根分区会增加构建临时空间需求，Runner 磁盘不足时构建会失败；这种情况应减少分区大小或使用磁盘更大的 Runner，而不是跳过产物检查。

## 官方版本与包管理器

版本源为官方 Firmware Selector 使用的同类发布数据：[`.versions.json`](https://downloads.openwrt.org/.versions.json)。排除 SNAPSHOT/RC，按实际存在的年号大版本排序，只保留最新三代，并选各代最高稳定补丁；不假设年号连续，也不猜测下载目录。官网不可用或结构异常时失败，不使用过期备用版本。

截至 2026-10-28 的解析结果：

| 选择 | 实际版本 | 包管理器 | 防火墙 | 官方目录 |
| --- | --- | --- | --- | --- |
| 最新大版本 | 25.12.6 | apk / APK | fw4 / nftables | [x86/64](https://downloads.openwrt.org/releases/25.12.6/targets/x86/64/) |
| 上一大版本 | 24.10.8 | opkg / IPK | fw4 / nftables | [x86/64](https://downloads.openwrt.org/releases/24.10.8/targets/x86/64/) |
| 上两个大版本 | 23.05.6 | opkg / IPK | fw4 / nftables | [x86/64](https://downloads.openwrt.org/releases/23.05.6/targets/x86/64/) |

以后新大版本正式发布时，窗口自动前移，无需改菜单。实际管理器和防火墙读取 ImageBuilder `.config`，并结合安装清单核对，而不是按年号硬猜。fw3/iptables 与 fw4/nftables 的 OpenClash 依赖分开选择，Nikki 要求 fw4。新版本缺少已锁定的第三方包时会明确拒绝，不拿旧版本的包混装。

保留三代构建入口不等于这三代都仍获得安全维护。23.05 已经 EOL；请查看 [官方维护状态](https://openwrt.org/docs/guide-developer/security)，生产使用优先选择仍受支持的版本。项目不能承诺上游或第三方组件没有漏洞。

下载流程先获取所选版本官方 `sha256sums`，严格匹配唯一 ImageBuilder 文件名（支持 `.tar.zst` / `.tar.xz`），再下载并验证 SHA256。目录不存在、清单缺项、哈希不符时失败，不自动回退其他版本。清单通过官方 HTTPS 获取；目前没有独立验证其 GPG/usign 签名。

安全解压保留路径越界检查；官方归档中指向构建服务器的少量宿主工具链接，在解压后绑定到 Runner 本地工具或归档内脚本。解压后读取 `.config` 核对包管理器，并在其中持久化 `CONFIG_TARGET_ROOTFS_PARTSIZE`。不将 MiB 数值错误地传给内部以字节计算的 `ROOTFS_PARTSIZE`。

## 第三方插件锁定

`configs/plugins.lock.json` 保存上游固定 Release URL、版本和 SHA256。构建不调用第三方在线安装脚本，不使用 `/latest/` 下载地址，不混用 IPK 和 APK。

| 组件 | 锁定版本 | 来源 |
| --- | --- | --- |
| OpenClash | v0.48.002 | [vernesong/OpenClash](https://github.com/vernesong/OpenClash/releases/tag/v0.48.002) |
| OpenClash Mihomo 核心 | v1.19.33，amd64-v1 | [MetaCubeX/mihomo](https://github.com/MetaCubeX/mihomo/releases/tag/v1.19.33) |
| Nikki（含 mihomo-meta） | v1.26.2，分别下载 24.10/25.12 的 x86_64 归档 | [nikkinikki-org/OpenWrt-nikki](https://github.com/nikkinikki-org/OpenWrt-nikki/releases/tag/v1.26.2) |

IPK 放入 ImageBuilder 本地包目录。APK 在上游文件哈希验证通过后，用 ImageBuilder 临时生成的本地密钥签名，再由本地软件源安装。官方源签名检查保持启用；私钥不会加入固件或产物。升级插件时应更新锁文件并重跑构建与启动测试，不能只换文件后缀或跳过依赖。

构建记录保存锁定下载信息、参数、额外包和源码提交，但官方软件源会变化，因此不能承诺不同日期构建得到逐字节相同的固件。

## 验证和发布

手动工作流执行单元测试、参数验证、依赖安装、构建、镜像检查和产物上传。参数通过环境变量传入；自定义包只允许包名，不直接拼成 shell 命令。

产物检查要求四个非空镜像、正确 gzip CRC、BIOS MBR 或 EFI GPT、实际根分区大小、镜像长度以及非空 manifest；还检查请求安装的包确实出现在 manifest 中。兼容 gzip 后附加的 OpenWrt fwtool 元数据。检查通过后生成：

- 四个 `combined*.img.gz` 整盘镜像。
- 软件包 `.manifest`。
- `build-info.json`：输入、工具及插件版本、哈希、源码提交和运行编号。
- `ACCESS.md`：本次固件的管理 IPv4、网页入口、root 用户名、初始密码状态及保留旧配置时的说明；Release 正文与构建摘要也显示这些内容。
- `official-versions.json`：本次使用的官方版本数据快照。
- `uci-defaults.txt`：实际注入的一次性设置脚本，便于审查。
- `imagebuilder-sha256sums.txt`：官方原始校验清单。
- `SHA256SUMS`：此次产物的校验值，不包含自身。

解压下载的 Artifact 后，Linux 下执行 `sha256sum -c SHA256SUMS`。

`Verify firmware builds` 检查最新三个官方大版本与支持的代理选项（23/Nikki 明确不支持），覆盖三代 Docker，并注入测试管理 IP 和额外包。CI 使用隔离 QEMU 快照启动 ext4 BIOS 镜像，检查 LAN IP、网卡、核心和代理关闭状态；Docker 组合还启动 daemon 并等待 `docker info` 成功。测试日志及产物保留 7 天。EFI/squashfs 通过结构检查，尚不等于四种镜像都经过实际启动。

可选 Release 使用单独的发布任务，只有此任务获得仓库写权限。下载本次构建 Artifact 后重新核对文件清单和 SHA256，先建立草稿，全部资产上传成功才公开。标签包含 OpenWrt 版本、运行编号和重试次数，不覆盖旧 Release；发布失败会保留草稿供诊断，Artifact 仍可下载。不需要额外 PAT。

普通手动构建失败时尽力保存 `build.log`；早期失败可能还未产生该文件，请查看 Actions 日志。本地构建拒绝已有 `work/` 和 `dist/`，避免旧产物混入。

## 开发与验收

源码入口和配置：

```text
.github/workflows/build.yml    手动参数与可选发布
.github/workflows/verify.yml   三代版本的兼容构建与启动检查
configs/plugins.lock.json     第三方下载锁定
scripts/build.py              验证、下载、注入、构建、产物检查
scripts/smoke.py              隔离 QEMU 启动检查
scripts/release.py            完整性复核与草稿发布
tests/                        功能与失败路径测试
docs/PACKAGES.md               常用官方包名、用途与填写示例
```

在项目根目录运行 `python3 -m unittest discover -s tests -v`。脚本需要 Python 3.12+，构建宿主为 Linux x86-64；Actions 会安装已列明的依赖。当前验证证据和限制见 [VALIDATION.md](VALIDATION.md)。

源码不包含远程主机或 VM101 凭据，不连接或修改现有 ImmortalWrt。下载的固件应先在新建隔离虚拟机验证；CI 启动测试不能替代 J4125 实际网卡、存储、Docker 容器和代理流量测试。
