# OpenWrt Firmware Builder V3.1

使用官方 OpenWrt ImageBuilder，在 GitHub Actions 定制固件。设备入口支持官方发布元数据列出的 target/subtarget 和设备 Profile，缺少 ImageBuilder、匹配包、资源或预期镜像时明确失败，不混装、不静默省略功能。入口覆盖不等于全部设备已经过实机验收。

## Actions 流程说明

**只想生成固件，使用 Build OpenWrt 即可，其余流程无需先运行。**

| 左侧流程（点击可进入） | 用来做什么 | 什么时候使用 | 运行后的结果 |
| --- | --- | --- | --- |
| [Build OpenWrt](https://github.com/ZorroZhou/openwrt-firmware-builder/actions/workflows/build.yml) | 按版本、设备、分区和插件选项生成固件 | 日常构建，手动点击 Run workflow | 检查通过后提供固件 Artifacts；勾选 publish_release 才发布 Release |
| [Discover official devices](https://github.com/ZorroZhou/openwrt-firmware-builder/actions/workflows/devices.yml) | 从官网查询某版本支持的设备，可按品牌/型号筛选 | 想核对设备支持情况或导出清单时；构建前不必运行 | official-devices 下载包，包含 CSV 和 JSON；不生成固件、不更新下拉菜单 |
| [Refresh version menu](https://github.com/ZorroZhou/openwrt-firmware-builder/actions/workflows/refresh-versions.yml) | 重新获取官网最新两代版本，并刷新版本和设备菜单文件 | 官网发布新版本/设备，仓库菜单需要更新时；主要供维护者使用 | official-version-menu 下载包；须将其中四个同路径文件提交到 main，页面菜单才会更新，不自动改仓库、不生成固件 |
| [Verify firmware builds](https://github.com/ZorroZhou/openwrt-firmware-builder/actions/workflows/verify.yml) | 自动检查代码、失败路径与代表性平台/插件组合 | 相关代码或工作流变更后自动运行；主要供开发验收 | 各组合检查结果、日志与临时测试固件；不发布 Release，不代表全部硬件实机验证 |

左侧流程页用于查看运行记录及手动触发。每个流程运行后，点开一条记录，在 **Summary（摘要）** 查看用途说明；右侧具体任务日志可定位失败步骤。无需为了看说明启动构建，直接阅读本表即可。

## 找设备与构建

1. **Actions → Build OpenWrt → Run workflow**，选择 OpenWrt 版本和设备型号。设备下拉框显示品牌/型号、目标平台与 Profile，自动绑定后两项，无需手填设备 ID。默认选择 x86 通用设备。
2. 菜单合并两代最新小版本的官方设备目录，目前共 1969 项；选择其他小版本时，构建前实时核对是否支持该设备，不支持则明确失败。请匹配准确型号和硬件修订。Discover official devices 仍可用于检索官方目录，无需先运行它才能构建。
3. 成功后下载 Artifacts；勾选 publish_release 则在完整性和适用执行检查后发布 Release。镜像类型、接线与刷写步骤以所选设备官方说明为准，没有通用刷写命令。

[官方 Firmware Selector](https://firmware-selector.openwrt.org/) · [软件包填写示例](docs/PACKAGES.md) · [完整版本菜单](docs/VERSIONS.md)

## 参数

| 参数 | 含义 |
| --- | --- |
| version | 官网最新两代大版本的全部正式小版本，排除 RC/SNAPSHOT |
| device | 选择品牌/设备型号，自动绑定官方目标与 Profile；必须存在于所选版本 |
| rootfs_mb | 固定闪存设备必须 auto，保留官方布局；具有 ext4 磁盘镜像的设备可选 MiB 大小，auto 使用 1024 MiB |
| preset | minimal 保留官方基础包；standard 追加 LuCI HTTPS、基础简体中文、curl、证书 |
| lan_ip | 默认 192.168.1.1，私网 IPv4 主机地址，固定 /24；验证格式、网络/广播地址及 Docker 默认网段冲突 |
| docker | 可选 Docker、Dockerman 及中文包；目前仅开放具有官方 ext4 磁盘镜像的 x86_64/arm64，仍须满足实际源与内核依赖 |
| proxy | none / openclash / nikki，互斥；根据实际分支、包管理器、防火墙和 CPU 架构匹配 |
| istore | 默认关闭；目前仅集成 25.12 APK x86_64/arm64 作者签名源，包含中文；不是安装 iStoreOS |
| extra_packages | 追加官方包名，以空格分隔；不接受命令或移除语法 |
| publish_release | 默认关闭；通过构建、检查、上传后才公开，不覆盖旧标签 |

选择 Docker、代理或 iStore 时补齐 LuCI HTTPS 和基础中文。Docker/Nikki 带专用中文包，OpenClash/iStore 检查包内简体中文资源。磁盘功能组合至少 512 MiB；容器数据应规划更充足的存储。固定闪存容量由设备构建规则限制，不能通过扩大分区绕过物理容量。

## 网络与登录

保留所选设备官方 DHCP、IPv6、网关及 DNS 默认配置，不提供主/旁路由自动配置。安装后由用户在 OpenWrt 中自行设置网络。管理 IPv4 选项只修改已有 LAN 的静态地址和 /24 掩码，不更改端口或桥接布局。

全新刷写用户名 **root**，初始密码**未设置**，首次登录自行设置。Release、运行摘要及 ACCESS.md 显示管理地址、官方网络默认行为和实际组件版本。保留旧配置升级时，以继承的地址、密码和服务设置为准。

## 最新组件与兼容性

- OpenClash 每次解析作者最新正式 Release，按实际 IPK/APK 选包。Mihomo 选择实际 CPU 的保守 ISA 变体，检查 ELF 类别、字节序和机器类型。未知架构、不唯一匹配或没有上游 SHA256 时失败，不回退旧版或 amd64。
- Nikki 从对应 OpenWrt 分支和 arch_packages 的作者签名源安装最新可用包，保留源与公钥。缺源、依赖不满足会失败；核心随该源配套，不混装其他项目的独立核心。
- iStore 验证固定公钥哈希，再由 APK 校验作者源签名，保留官方源。不执行网络安装器、不降低全局签名检查。尚未开放 opkg 路径，因为上游 is-opkg 会在其临时配置中剥除签名检查。iStore 自身后续安装器与应用由上游维护，应用列表不代表逐项兼容全部设备，见 [上游说明](https://github.com/istoreos/istore)。
- Docker 只从所选官方版本的软件源解析组件及内核依赖。构建成功不等于内存、容器驱动、数据盘与实际工作负载均已验收。

每次构建使用干净目录重新解析组件，记录确切 URL、版本与哈希。仅重试 Release 上传不会更新已构建的软件；需要最新组件时重新运行完整构建。

## 官方版本与设备目录

版本源为 [官方 .versions.json](https://downloads.openwrt.org/.versions.json)，保留最新两个实际存在的年号大版本，不假设年份连续。当前 25.12.0–25.12.6、24.10.0–24.10.8，共 16 项。

GitHub 原生输入不能实时联动官网。运行 Refresh version menu，下载 official-version-menu，将四个同路径文件提交到默认分支才更新菜单；同时刷新设备菜单和 configs/devices.json；此工作流只读仓库。也可执行 `python3 scripts/sync_versions.py` 和 `python3 scripts/sync_devices.py` 后提交。构建仍实时验证范围，过期选择被拒绝。

Discover 工作流读取与 Firmware Selector 相同的官方 .overview.json，再读取其中全部目标的 profiles.json，核对两份设备清单一致；任一请求失败就失败，不拿不完整结果冒充全集。各小版本支持设备可能不同，应按实际版本查询。构建前再次核对目标、Profile、架构和镜像类型。

## 校验、模拟器与产物

从所选目标 sha256sums 唯一解析官方 ImageBuilder，支持 tar.xz/tar.zst，经 HTTPS 下载并校验 SHA256。当前未独立验证官方清单 GPG/usign 签名；软件源签名检查保持开启。

x86 generic 检查 BIOS/EFI、ext4/squashfs 四种整盘镜像的 gzip、MBR/GPT、根分区大小与镜像长度。其他设备按官方 Profile 的预期文件和 ImageBuilder 生成的校验清单验证，不套用 x86 磁盘规则。ImageBuilder 不重新编译 initramfs 内核；此类源码构建产物不列为缺失，仍严格检查其 factory/sysupgrade 等拼装产物；只有 initramfs 的设备提前拒绝，需使用源码构建。容量由设备构建规则约束；不宣称已对所有硬件格式逐一逆向解析。

x86/64/generic 使用隔离 QEMU BIOS 启动；armsr/armv8/generic 使用 QEMU virt + ARM64 EFI。其他板级内核不能假装在通用虚拟板启动，仅记录镜像校验及可用的跨架构核心/CLI 检查，不算板级启动或 DHCP/流量测试。实际端口、无线、启动链、闪存与代理/容器流量需在隔离硬件环境验收。失败不发布固件，保存 build.log/smoke.log。

verify.yml 中 **192.168.77.1 是一次性隔离 CI 固件的合成管理地址**，不属于部署设备。QEMU 使用受限用户网络与快照，不连接生产网络。CI 覆盖两代 x86、ARM64 和固定闪存 MIPS 代表目标，不宣称官网全部设备均完成实机验收。

Artifacts 保留 14 天，CI 产物保留 7 天。内容包含镜像、manifest、build-info.json、device-profile.json、ACCESS.md、官方版本快照、校验清单、注入脚本和第三方来源/许可证。`sha256sum -c SHA256SUMS` 可复核下载内容。Release 先草稿，所有资产上传后才公开。

## 开发与来源

在项目根目录运行 `python3 -m unittest discover -s tests -v`。需要 Python 3.12+ 和 Linux x86-64 构建宿主。设备及功能匹配在 scripts/devices.py，设备目录导出在 scripts/discover_devices.py，其余入口见 scripts/ 和 .github/workflows/。证据与限制见 [VALIDATION.md](VALIDATION.md)。

第三方版权和许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 与 licenses/。自写脚本暂未指定许可证，来源引用不是完整对应源码归档。

可选 iStore 软件中心来自 [istoreos/istore](https://github.com/istoreos/istore)，版权归易有云团队及贡献者，采用 [MIT License](https://github.com/istoreos/istore/blob/main/LICENSE)。本项目集成的是 iStore 组件，并非 iStoreOS；商店应用及依赖各自的许可仍分别适用。选择 iStore 构建时，会随固件和附件保留上游完整版权与许可文本，实际版本及来源见 build-info.json 和 manifest。
