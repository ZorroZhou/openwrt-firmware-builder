# OpenWrt Firmware Builder V3.0

使用官方 OpenWrt ImageBuilder，在 GitHub Actions 定制固件。设备入口支持官方发布元数据列出的 target/subtarget 和设备 Profile，不再固定 x86；缺少 ImageBuilder、匹配包、资源或预期镜像时明确失败，不混装、不静默省略功能。入口覆盖不等于全部设备已经过实机验收。

## 找设备与构建

1. **Actions → Discover official devices → Run workflow**。输入完整正式版本，或 `latest` / `previous`；检索词留空导出全部设备，也可按品牌、型号或架构筛选。下载 `official-devices` CSV，复制对应 `target`、`profile` 两列。
2. **Actions → Build OpenWrt → Run workflow**。选择同一版本，填写目标与 Profile；默认 `x86/64`、`generic`，ARM64 通用 EFI 示例为 `armsr/armv8`、`generic`。不要拿相似型号或不同硬件修订替代。
3. 成功后下载 Artifacts；勾选 publish_release 则在完整性和适用执行检查后发布 Release。镜像类型、接线与刷写步骤以所选设备官方说明为准，没有通用刷写命令。

[官方 Firmware Selector](https://firmware-selector.openwrt.org/) · [软件包填写示例](docs/PACKAGES.md) · [完整版本菜单](docs/VERSIONS.md)

## 参数

| 参数 | 含义 |
| --- | --- |
| version | 官网最新两代大版本的全部正式小版本，排除 RC/SNAPSHOT |
| target / profile | 官方目标与设备 ID；必须存在于所选版本的官方元数据 |
| rootfs_mb | 固定闪存设备必须 auto，保留官方布局；具有 ext4 磁盘镜像的设备可选 MiB 大小，auto 使用 1024 MiB |
| preset | minimal 保留官方基础包；standard 追加 LuCI HTTPS、基础简体中文、curl、证书 |
| lan_ip | 默认 192.168.1.1，私网 IPv4 主机地址，固定 /24；验证格式、网络/广播地址及 Docker 默认网段冲突 |
| router_mode | main 主路由开启 LAN IPv4 DHCP；bypass 旁路由关闭 LAN DHCPv4、RA、DHCPv6、NDP |
| upstream_gateway / upstream_dns | 旁路由必填：网关为同一 /24 网段另一主机，DNS 以空格分隔；主路由模式留空，保留官方 WAN 配置 |
| docker | 可选 Docker、Dockerman 及中文包；目前仅开放具有官方 ext4 磁盘镜像的 x86_64/arm64，仍须满足实际源与内核依赖 |
| proxy | none / openclash / nikki，互斥；根据实际分支、包管理器、防火墙和 CPU 架构匹配 |
| istore | 默认关闭；目前仅集成 25.12 APK x86_64/arm64 作者签名源，包含中文；不是安装 iStoreOS |
| extra_packages | 追加官方包名，以空格分隔；不接受命令或移除语法 |
| publish_release | 默认关闭；通过构建、检查、上传后才公开，不覆盖旧标签 |

选择 Docker、代理或 iStore 时补齐 LuCI HTTPS 和基础中文。Docker/Nikki 带专用中文包，OpenClash/iStore 检查包内简体中文资源。磁盘功能组合至少 512 MiB；容器数据应规划更充足的存储。固定闪存容量由设备构建规则限制，不能通过扩大分区绕过物理容量。

## 路由模式与登录

两种模式修改已有 network.lan / dhcp.lan，不假设 eth0/eth1，不重划 DSA、交换机或无线拓扑。设备须有官方 LAN 配置；没有 LAN 的设备需要专门适配。

主路由开启 LAN IPv4 DHCP，保留官方 WAN 和 IPv6 默认行为。旁路由设置管理地址、网关和 DNS，关闭 LAN DHCPv4 与 RA/DHCPv6/NDP；**不停止整个 dnsmasq**，保留 DNS/代理依赖。不会更改其他设备网关，也不会自动接管全网流量。接线、主路由 DHCP 分配策略与终端路由需按实际拓扑设置。

全新刷写用户名 **root**，初始密码**未设置**，首次登录自行设置。Release、运行摘要及 ACCESS.md 显示管理地址、模式、DHCP 状态、上游设置和实际组件版本。保留旧配置升级时，以继承的地址、密码和服务设置为准。

## 最新组件与兼容性

- OpenClash 每次解析作者最新正式 Release，按实际 IPK/APK 选包。Mihomo 选择实际 CPU 的保守 ISA 变体，检查 ELF 类别、字节序和机器类型。未知架构、不唯一匹配或没有上游 SHA256 时失败，不回退旧版或 amd64。
- Nikki 从对应 OpenWrt 分支和 arch_packages 的作者签名源安装最新可用包，保留源与公钥。缺源、依赖不满足会失败；核心随该源配套，不混装其他项目的独立核心。
- iStore 验证固定公钥哈希，再由 APK 校验作者源签名，保留官方源。不执行网络安装器、不降低全局签名检查。尚未开放 opkg 路径，因为上游 is-opkg 会在其临时配置中剥除签名检查。iStore 自身后续安装器与应用由上游维护，应用列表不代表逐项兼容全部设备，见 [上游说明](https://github.com/istoreos/istore)。
- Docker 只从所选官方版本的软件源解析组件及内核依赖。构建成功不等于内存、容器驱动、数据盘与实际工作负载均已验收。

每次构建使用干净目录重新解析组件，记录确切 URL、版本与哈希。仅重试 Release 上传不会更新已构建的软件；需要最新组件时重新运行完整构建。

## 官方版本与设备目录

版本源为 [官方 .versions.json](https://downloads.openwrt.org/.versions.json)，保留最新两个实际存在的年号大版本，不假设年份连续。当前 25.12.0–25.12.6、24.10.0–24.10.8，共 16 项。

GitHub 原生输入不能实时联动官网。运行 Refresh version menu，下载 official-version-menu，将三个同路径文件提交到默认分支才更新菜单；此工作流只读仓库。也可执行 `python3 scripts/sync_versions.py` 后提交。构建仍实时验证范围，过期选择被拒绝。

Discover 工作流读取与 Firmware Selector 相同的官方 .overview.json，再读取其中全部目标的 profiles.json，核对两份设备清单一致；任一请求失败就失败，不拿不完整结果冒充全集。各小版本支持设备可能不同，应按实际版本查询。构建前再次核对目标、Profile、架构和镜像类型。

## 校验、模拟器与产物

从所选目标 sha256sums 唯一解析官方 ImageBuilder，支持 tar.xz/tar.zst，经 HTTPS 下载并校验 SHA256。当前未独立验证官方清单 GPG/usign 签名；软件源签名检查保持开启。

x86 generic 检查 BIOS/EFI、ext4/squashfs 四种整盘镜像的 gzip、MBR/GPT、根分区大小与镜像长度。其他设备按官方 Profile 的预期文件和 ImageBuilder 生成的校验清单验证，不套用 x86 磁盘规则。ImageBuilder 不重新编译 initramfs 内核；此类源码构建产物不列为缺失，仍严格检查其 factory/sysupgrade 等拼装产物；只有 initramfs 的设备提前拒绝，需使用源码构建。容量由设备构建规则约束；不宣称已对所有硬件格式逐一逆向解析。

x86/64/generic 使用隔离 QEMU BIOS 启动；armsr/armv8/generic 使用 QEMU virt + ARM64 EFI。其他板级内核不能假装在通用虚拟板启动，仅记录镜像校验及可用的跨架构核心/CLI 检查，不算板级启动或 DHCP/流量测试。实际端口、无线、启动链、闪存与代理/容器流量需在隔离硬件环境验收。失败不发布固件，保存 build.log/smoke.log。

verify.yml 中 **192.168.77.1 是一次性隔离 CI 固件的合成管理地址**，192.168.77.254 是旁路由测试的合成网关/DNS，不属于部署设备。QEMU 使用受限用户网络与快照，不连接生产网络。CI 覆盖两代 x86、ARM64 和固定闪存 MIPS 代表目标，不宣称官网全部设备均完成实机验收。

Artifacts 保留 14 天，CI 产物保留 7 天。内容包含镜像、manifest、build-info.json、device-profile.json、ACCESS.md、官方版本快照、校验清单、注入脚本和第三方来源/许可证。`sha256sum -c SHA256SUMS` 可复核下载内容。Release 先草稿，所有资产上传后才公开。

## 开发与来源

在项目根目录运行 `python3 -m unittest discover -s tests -v`。需要 Python 3.12+ 和 Linux x86-64 构建宿主。设备/网络策略在 scripts/devices.py，设备目录导出在 scripts/discover_devices.py，其余入口见 scripts/ 和 .github/workflows/。证据与限制见 [VALIDATION.md](VALIDATION.md)。

第三方版权和许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 与 licenses/。自写脚本暂未指定许可证，来源引用不是完整对应源码归档。当前公开说明使用通用环境描述；旧提交及既有标签可能保留历史内容，本轮不重写 Git 历史。
