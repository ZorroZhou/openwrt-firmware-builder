# 验证记录

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
