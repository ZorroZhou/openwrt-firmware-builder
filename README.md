# OpenWrt Firmware Builder V1.0

在 GitHub Actions 中选择参数，用**官方 OpenWrt ImageBuilder**组装 x86-64 固件。保留官方内核、驱动和软件源；不从源码编译，不使用 ImmortalWrt，不访问现有 VM101。

## 开始使用

1. 新建 GitHub 仓库，把此目录内的全部文件放到仓库根目录，包括隐藏的 `.github/`。不要把外层 `openwrt-firmware-builder/` 一起作为子目录上传。
2. 将文件提交到默认分支，在仓库 **Actions** 中启用工作流。
3. 打开 **Build OpenWrt → Run workflow**，选择参数后运行。
4. 运行成功后，在该次运行页面底部 **Artifacts** 下载固件包。无需 PAT、SSH 密钥或仓库写权限，不创建 Release。

| 参数 | 取值与含义 |
| --- | --- |
| version | 下拉选择 `25.12.6` / `24.10.6`，默认 `25.12.6`；仅列出已核实存在的官方发布版本 |
| target | 仅 `x86-64`，内部目标 `x86/64`、设备 Profile `generic` |
| rootfs_mb | 256 / 512 / 1024 / 2048 / 4096 MiB；设置根分区，整盘镜像还包含引导分区和对齐空间 |
| preset | `minimal`：官方设备默认软件包；`standard`：默认软件包加 `luci-ssl curl ca-bundle` |

minimal 不主动裁剪官方默认包，不保证包含 LuCI。standard 提供 LuCI HTTPS 管理界面。预设不加入 Docker、OpenClash、Nikki、自定义 IP 或第三方源。系统初始设置遵循官方默认配置，首次使用应在隔离虚拟机中完成密码和网络设置。

## 版本、下载与包管理器

版本下拉列表是工作流中维护的固定列表，不会自动获取最新版本。增加选项前，先确认该版本官方 x86/64 ImageBuilder 存在且兼容，再更新 `.github/workflows/build.yml` 中的 `version.options`。构建脚本仍校验完整版本号及官方文件，不会因为版本列在菜单中就跳过下载检查。

截至 2026-10-28，已核对以下官方目录及 ImageBuilder 文件存在：

- [25.12.6 x86/64](https://downloads.openwrt.org/releases/25.12.6/targets/x86/64/)：`openwrt-imagebuilder-25.12.6-x86-64.Linux-x86_64.tar.zst`，apk。
- [24.10.6 x86/64](https://downloads.openwrt.org/releases/24.10.6/targets/x86/64/)：`openwrt-imagebuilder-24.10.6-x86-64.Linux-x86_64.tar.zst`，opkg。

工作流不会假设输入版本的目录一定存在，也不会自动退回其他版本。脚本先请求 `https://downloads.openwrt.org/releases/<version>/targets/x86/64/sha256sums`，从清单中严格匹配该版本、目标和 Linux x86_64 主机的唯一 ImageBuilder 文件（支持 `.tar.zst` / `.tar.xz`），然后下载并校验 SHA256。404、无匹配、重复匹配、损坏下载均终止。

SHA256 清单通过官方 HTTPS 获取，用于完整性校验；V1.0 没有独立验证清单的 GPG/usign 签名。它不等同于独立签名认证。

解压后读取 `.config` 中的 `CONFIG_USE_APK`：25.12 必须启用 apk，24.10 必须为 opkg，否则停止。包解析、下载和签名检查由该版本 ImageBuilder 自带工具处理，保留其官方源与密钥，不在宿主机安装 opkg/apk，也不转换软件包格式。接受某系列的补丁版本不代表每个补丁都已实测；不存在、下架或源不可用时均明确失败。新增版本系列应先核实工具与产物格式，再更新验证规则和测试。

## 构建和产物验证

运行环境是 GitHub 托管的 Ubuntu 24.04 x86-64。实际构建入口：

```text
make info
make image PROFILE=generic PACKAGES="<预设增量包>"
```

调用前仅替换解压目录 `.config` 中唯一的 `CONFIG_TARGET_ROOTFS_PARTSIZE` 为所选 MiB 数值。这样可穿过 ImageBuilder 清理 `MAKEFLAGS` 的递归调用，避免命令行配置丢失。内部的 `ROOTFS_PARTSIZE` 可能以字节计算，不能将 MiB 数值直接传给它；构建后还会检查镜像中的实际根分区大小。

`make` 返回非零立即失败，日志管道启用 GitHub Bash 默认的 `pipefail`。构建后要求 ext4、squashfs 各有 BIOS 和 EFI 四个非空 `combined*.img.gz`，校验 gzip CRC/完整性、BIOS MBR 或 EFI GPT、第二分区大小和解压后磁盘长度，要求非空软件包 manifest。允许 gzip 后附加 OpenWrt fwtool 元数据。全部通过才创建 `dist/` 并进入固件上传步骤。检查不能代替实际启动测试。

下载的 Artifact 内包含：

- 四个整盘固件：`generic-ext4-combined[‑efi].img.gz`、`generic-squashfs-combined[‑efi].img.gz`。
- ImageBuilder 输出的软件包 `.manifest`。
- `build-info.json`：输入参数、包管理器、官方工具 URL/哈希和构建提交。
- `imagebuilder-sha256sums.txt`：官方原始清单。
- `SHA256SUMS`：本次交付文件的哈希，不包含自身；下载解压后在 Linux 中运行 `sha256sum -c SHA256SUMS`。

固件 Artifact 保留 14 天；构建失败时尽力上传 `build.log`，保留 7 天。安装依赖等早期步骤失败时可能还没有日志文件，请查看 Actions 页面日志。上传失败会使任务失败，可从日志区分构建与上传问题。每次运行使用独立 Runner；本地执行时拒绝已有 `work/` 或 `dist/`，避免混入旧固件。

EFI 机器通常选 `combined-efi`，传统 BIOS 选 `combined`。ext4 和 squashfs 的存储/恢复行为不同，应先在新建的隔离 x86-64 虚拟机验证启动、网卡识别、LuCI 和根分区大小。此项目不提供刷盘、导入 Proxmox 或修改 VM101 的步骤。

## 开发验证与限制

在项目根目录运行已包含的测试入口：

```text
python3 -m unittest discover -s tests -v
```

构建脚本使用 Python 3.12+ 标准库。测试覆盖参数拒绝、版本清单匹配、哈希错误、404、网络重试耗尽、make 错误传播、旧产物拒绝及磁盘检查。工作流中先运行测试和输入验证，再安装构建依赖。静态检查不能证明包源当前可用或固件能启动；首次 GitHub Actions 完整运行和隔离虚拟机启动验收仍需执行。源码中没有任何远程主机或 VM101 凭据。

实现依据：[官方 ImageBuilder 文档](https://openwrt.org/docs/guide-user/additional-software/imagebuilder)、[官方 ImageBuilder 打包实现](https://github.com/openwrt/openwrt/blob/main/target/imagebuilder/Makefile)、[根文件系统大小计算](https://github.com/openwrt/openwrt/blob/main/include/image.mk)、[x86 镜像构建](https://github.com/openwrt/openwrt/blob/main/target/linux/x86/image/Makefile)。
