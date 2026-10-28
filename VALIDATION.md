# 验证记录

## V2.3：每次构建解析最新代理组件

日期：2026-10-28。

- 38 项单元与失败路径测试通过；三个工作流的 actionlint 检查通过。
- OpenClash/Mihomo 通过各自 GitHub latest 正式发布 API 解析标签、对应格式/架构和资产 SHA256；资产仍使用确切标签地址下载，不使用浮动下载 URL。
- 新增缺少匹配资产、重复资产、错误来源、缺失 SHA256、草稿/预发布和未知仓库等失败路径测试；不静默回退旧版。核心另检查 x86-64 ELF 格式，运行兼容性继续由隔离启动测试检查。
- Nikki 保持每次从对应 OpenWrt 分支的作者签名源安装最新可用包，不混装 OpenClash 的独立核心。
- 实际安装组件版本记录在 manifest、build-info.json、ACCESS.md、运行摘要和 Release 正文；本地另确认版本显示内容。仅重试发布任务不会改变已经构建的产物。
- OpenClash/Mihomo 所选标签的许可证原文随固件和 Artifact 保留，记录来源 URL 与下载内容 SHA256。
- 手动 Build OpenWrt 选择代理时，也必须在固件上传/Release 发布前通过隔离启动检查；失败保留 build.log 和 smoke.log，不进入发布任务。此流程不替代真实代理流量测试。
- [代理动态版本首轮兼容检查](https://github.com/ZorroZhou/openwrt-firmware-builder/actions/runs/40623483455)：11 个组合全部通过，包含 23/24/25 的 OpenClash、支持分支的 Nikki 和三代 Docker。
- [真实手动构建与发布](https://github.com/ZorroZhou/openwrt-firmware-builder/actions/runs/40624437242)：build、release 均成功，固件上传前的隔离启动检查通过。使用 25.12.6、standard、512 MiB、OpenClash、不启用 Docker。
- [实际 Release](https://github.com/ZorroZhou/openwrt-firmware-builder/releases/tag/firmware-25.12.6-40624437242-1) 的 20 个附件全部上传成功；正文显示 OpenClash 0.48.002、Mihomo v1.19.33，以及 192.168.1.1、root、初始密码未设置。
- 另下载实际发布的 build-info.json 核对：builder_version=2.3.0，动态版本策略、解析后的固定标签 URL、上游资产 SHA256、对应标签源码/许可证 URL 与内容哈希均保留。
- 未访问或修改 VM101。
- [加入手动发布启动检查后的重复复核](https://github.com/ZorroZhou/openwrt-firmware-builder/actions/runs/40624286914)：截至本次记录，10/11 项通过，23.05.6 + Docker（不带代理）仍在镜像打包阶段，尚未记为通过。该组合在上面的首轮矩阵已通过；新增手动代理发布检查也已通过真实运行验收。此处保留未完成状态，不将其描述为本轮全部成功。

## V2.2：完整小版本菜单、作者签名源和第三方来源

日期：2026-10-28。

- 35 项单元与失败路径测试通过，三个工作流通过 actionlint 语法检查。
- 从官方 `.versions.json` 生成 23 个正式版本选项：25.12.0–25.12.6、24.10.0–24.10.8、23.05.0–23.05.6；Chrome 中确认下拉菜单包含全部选项。
- [菜单刷新实际运行](https://github.com/ZorroZhou/openwrt-firmware-builder/actions/runs/40621033678) 成功，只有 contents:read 权限；成功上传包含三个更新文件的 Artifact，其中包含隐藏的 `.github/` 路径。菜单更新仍须提交这些文件，不是打开页面时实时获取。
- Nikki 依据作者 `feed.sh` 的签名源配置方法安装，保留运行系统的源与公钥。公钥下载哈希固定；上游软件源滚动更新，包版本由 manifest 记录。23.05/Nikki 提前拒绝。
- 首次云端尝试发现作者站点拒绝 Python 默认下载标识；使用项目真实名称作为下载标识后重新验证，未关闭 TLS 或软件源签名检查。
- 新增第三方来源、许可原文、源码引用和升级说明；构建时放入固件与 Artifact，Release 正文增加来源入口。自写脚本未指定许可证。这些文件不是所有软件包的完整对应源码归档。
- [签名源与完整小版本菜单兼容验收](https://github.com/ZorroZhou/openwrt-firmware-builder/actions/runs/40620956576)：11 个组合全部成功。原有八个组合覆盖三代最新稳定版本、支持的代理组合与三代 Docker；新增 23.05.0、24.10.0、25.12.0 基础构建与启动抽测。
- Nikki 在 24.10/opkg 和 25.12/apk 上均完成作者源安装、四种镜像结构检查和隔离启动；启动后检查源配置保留、核心可执行、代理默认关闭。没有执行真实路由器上的在线升级或代理流量测试。
- 所有测试未访问或修改 VM101。菜单包含 23 个版本，不代表全部小版本与功能组合均已逐项构建。
- [最终提交复核](https://github.com/ZorroZhou/openwrt-firmware-builder/actions/runs/40621675806)：统一生成文件换行后，11 个组合再次全部成功。GitHub 显示的 Action Node.js 运行时弃用提示没有导致任务失败；当前 Runner 已使用 Node.js 24 兼容执行。

## V2.1：官网三代版本、中文与登录说明

日期：2026-10-28。

- 31 项单元与失败路径测试通过；actionlint 检查通过。
- 核对 Firmware Selector 线上 `config.js`：发布数据源指向 `https://downloads.openwrt.org`。每次构建读取其 `.versions.json`，当前解析为 25.12.6、24.10.8、23.05.6，RC/SNAPSHOT 被排除。
- 实际下载官方 23.05.6 ImageBuilder，哈希为 `1086f40e313369bd04146408e287bb5edb0a02555f3f6030b67c07f33baa8ba9`，与官方清单一致；`.config` 确认为 opkg + firewall4。
- 新增 LuCI 基础中文、Dockerman 中文、Nikki 中文；OpenClash 检查非空简体中文资源。已根据实际构建根目录修正检查路径，并加入回归测试。
- IPv4 校验覆盖格式、私网范围、/24 主机地址、Docker 默认网段冲突；GitHub 表单不能实时自定义校验，校验在工作流下载前执行。不能据此判断真实 LAN 是否已有同址设备。
- [真实发布验收](https://github.com/ZorroZhou/openwrt-firmware-builder/actions/runs/40617675561)：构建和 release 两个任务均成功。
- [已发布的 25.12.6 standard / 1024 MiB 固件](https://github.com/ZorroZhou/openwrt-firmware-builder/releases/tag/firmware-25.12.6-40617675561-1)：正文和附件 `ACCESS.md` 已实测显示 192.168.1.1、root、初始密码未设置及保留旧配置的说明；11 个项目产物均上传成功（GitHub 另提供两个源码下载链接）。
- Chrome 扩展已用于触发上述手动工作流，并在已登录页面核对 Release 正文。
- [三代兼容矩阵](https://github.com/ZorroZhou/openwrt-firmware-builder/actions/runs/40617947610)：8 个组合全部通过构建、四种镜像结构检查和 ext4 BIOS 隔离启动验收；Docker 组合均验证 daemon 能响应，中文包由安装清单检查，OpenClash 还检查其实际中文资源文件。

| 官方解析版本 | 代理 | Docker | 结果 |
| --- | --- | --- | --- |
| 25.12.6 | none | 开启 | 通过 |
| 25.12.6 | OpenClash | 关闭 | 通过 |
| 25.12.6 | Nikki | 关闭 | 通过 |
| 24.10.8 | none | 关闭 | 通过 |
| 24.10.8 | OpenClash | 关闭 | 通过 |
| 24.10.8 | Nikki | 开启 | 通过 |
| 23.05.6 | none | 开启 | 通过 |
| 23.05.6 | OpenClash | 关闭 | 通过 |

23.05/Nikki 因缺少匹配的锁定上游包而提前拒绝，并有对应失败路径测试，不混用 24/25 软件包。三代检测结果均为 fw4/nftables；23/24 为 opkg，25 为 apk。

版本入口覆盖三代，不等于三代都仍受安全维护；23.05 已 EOL。软件源签名、下载哈希和禁用代理默认启动不能保证第三方软件没有漏洞。真实网卡、容器流量、代理订阅与转发仍需隔离实机/虚拟机测试；VM101 未被访问。

## V2.0 历史验证

检查日期：2026-10-28。范围为 x86-64；未访问 VM101。

## 已完成的基础验证

- actionlint 1.7.12 验证手动与 CI 工作流语法通过。
- 23 项 Python 测试通过：输入与注入拒绝、锁文件、版本清单、哈希、404/网络失败、make 失败、根分区设置、BIOS/GPT、缺失镜像/manifest、请求包安装检查、解压越界拒绝、首次启动设置、带 fwtool 元数据的启动镜像解压、发布上传失败不公开草稿等。
- 实际下载官方 24.10.6 / 25.12.6 工具，核对 SHA256 与 `.config`：分别使用 opkg 和 apk。
- 初次真实构建发现官方归档含指向构建服务器的绝对工具链接。已限制在已知宿主工具目录内重建这些链接，保留其他归档路径检查。
- [基础构建运行](https://github.com/ZorroZhou/openwrt-firmware-builder/actions/runs/40611707003)：两条版本线均成功生成四种 256 MiB 固件并通过结构检查。
- 官方 24.10.6 ext4 BIOS 与 25.12.6 squashfs EFI 参考镜像通过分区解析器检查。

## V2.0 功能矩阵

配置为 standard / 512 MiB / 管理 IP 192.168.77.1 / 额外 htop。覆盖两版本与 none、OpenClash、Nikki；25.12 none 和 24.10 Nikki 同时开启 Docker。

[功能构建运行](https://github.com/ZorroZhou/openwrt-firmware-builder/actions/runs/40612055156)：六种组合均成功，包含两种包管理器的第三方包安装及 Docker 构建。

[最终构建与启动验收](https://github.com/ZorroZhou/openwrt-firmware-builder/actions/runs/40614536075)：六项任务全部成功，每项生成四种镜像并检查结构，再以 ext4 BIOS 镜像启动隔离 QEMU。

| 版本 | 代理 | Docker | 构建与启动 |
| --- | --- | --- | --- |
| 24.10.6 | none | 关闭 | 通过 |
| 24.10.6 | OpenClash | 关闭 | 通过 |
| 24.10.6 | Nikki | 开启 | 通过，Docker daemon 正常响应 |
| 25.12.6 | none | 开启 | 通过，Docker daemon 正常响应 |
| 25.12.6 | OpenClash | 关闭 | 通过 |
| 25.12.6 | Nikki | 关闭 | 通过 |

六项均确认管理 IP 为 192.168.77.1；代理组合确认核心可执行且未启用代理服务。Docker 组合执行 `docker info` 检查服务响应。启动测试兼容 fwtool 尾部元数据，等待首次配置完成，并用短行脚本避免 BusyBox 控制台截断命令。

## 检查边界

- 镜像结构检查覆盖 ext4/squashfs 与 BIOS/EFI 四种组合。
- 隔离 QEMU 启动检查使用 ext4 BIOS 镜像，检查 LAN IP、网卡、Docker CLI 和 daemon、代理核心执行和代理保持关闭；不修改原始产物。
- 尚未验证 J4125 真实硬件、物理网卡、容器网络与存储负载、代理订阅和真实流量。需要在独立测试虚拟机中完成这些验收。
- V2.0 当时仅完成 Release 失败路径测试；真实试发布已在上面的 V2.1 验收中补齐。
- 锁文件验证的是上游下载文件的固定哈希。官方清单没有独立 GPG/usign 验签；不承诺官方滚动软件源能长期逐字节复现。

## 主要失败路径

| 失败条件 | 行为 |
| --- | --- |
| 非法参数/IP/包名、功能与分区大小不匹配 | 下载前失败 |
| 版本或归档不存在、404、清单不匹配 | 不回退版本，直接失败 |
| 网络错误/5xx | 最多三次请求，仍失败则退出 |
| 工具或插件哈希错误 | 解压/安装前退出 |
| 归档路径越界、结构异常、包格式缺失 | 不进行构建 |
| 包管理器、Profile、软件包依赖不兼容 | 非零退出，不发布产物 |
| 镜像/manifest/请求包/分区检查失败 | 不上传固件、不发布 Release |
| QEMU 启动或功能检查失败 | CI 失败，保留日志 |
| 发布前清单或文件哈希不符 | 不创建 Release |
| 资产上传失败 | 保留草稿，不公开部分 Release |

所有测试和构建在本地工作区或 GitHub Runner 中执行，没有修改现有路由系统。
