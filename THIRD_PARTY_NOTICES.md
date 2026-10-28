# 第三方来源、版权与许可证说明

本仓库由 ZorroZhou 维护，提供官方 OpenWrt 的自动化定制流程。OpenWrt、插件、内核及依赖库的版权属于各自作者；本项目不是这些上游项目的官方发行方，也不表示获得上游背书。

## 主要来源

| 项目/资料 | 作者或组织 | 用途/包含条件 | 许可证与来源 |
| --- | --- | --- | --- |
| OpenWrt / ImageBuilder | OpenWrt 项目及贡献者 | 官方系统、内核、包管理器、构建工具 | [源码](https://github.com/openwrt/openwrt)、[COPYING](https://github.com/openwrt/openwrt/blob/main/COPYING)：核心构建项目 GPL-2.0-only；各软件包另有各自条款 |
| Firmware Selector / 官方版本数据 | OpenWrt 项目及贡献者 | 版本与设备信息参考、发布清单 | [Firmware Selector](https://firmware-selector.openwrt.org/)、[源码](https://github.com/openwrt/firmware-selector-openwrt-org)、[版本数据](https://downloads.openwrt.org/.versions.json) |
| LuCI / 中文翻译 | LuCI 项目及翻译贡献者 | standard 或选择管理插件时包含 | [源码与许可证](https://github.com/openwrt/luci)；按实际模块的许可证与包元数据执行 |
| OpenClash | vernesong 及其贡献者 | 选择 OpenClash 时包含前端及相关文件 | [v0.48.002 源码](https://github.com/vernesong/OpenClash/tree/v0.48.002)、[MIT License](https://github.com/vernesong/OpenClash/blob/v0.48.002/LICENSE)；原版权声明见附带许可证 |
| Mihomo | MetaCubeX 及其贡献者 | OpenClash/Nikki 选择对应核心时包含 | [源码](https://github.com/MetaCubeX/mihomo)、[GPLv3 许可证](https://github.com/MetaCubeX/mihomo/blob/v1.19.33/LICENSE)；实际核心版本见 manifest/build-info |
| Nikki / LuCI 管理界面与翻译 | nikkinikki-org、Joseph Mory 及其贡献者 | 选择 Nikki 时从上游签名源安装 | [源码](https://github.com/nikkinikki-org/OpenWrt-nikki)、[LICENSE](https://github.com/nikkinikki-org/OpenWrt-nikki/blob/main/LICENSE)、[推荐软件源方式](https://github.com/nikkinikki-org/OpenWrt-nikki/blob/main/README.zh.md)；仓库提供 GPLv3 文本，包声明以对应源码/元数据为准 |
| Docker / Moby / containerd / runc / Dockerman | 各上游项目及贡献者 | 选择 Docker 时通过官方 OpenWrt 软件源安装 | [Moby](https://github.com/moby/moby)、[containerd](https://github.com/containerd/containerd)、[runc](https://github.com/opencontainers/runc)、[Dockerman](https://github.com/lisaac/luci-app-dockerman)；各组件许可证分别适用 |
| GitHub Actions | GitHub 及各 Action 作者 | 云端调度、下载与产物上传 | [actions/checkout](https://github.com/actions/checkout)、[upload-artifact](https://github.com/actions/upload-artifact)、[download-artifact](https://github.com/actions/download-artifact)；仅用于构建流程 |
| ImmortalWrt-ImageBuilder 交互设计参考 | wukongdaily 及其贡献者 | 本项目最初需求中的 Actions 参数交互参考 | [上游项目](https://github.com/wukongdaily/ImmortalWrt-ImageBuilder)；其代码及资源遵循原仓库条款 |

表格不是固件所有软件包的穷尽清单。实际包含哪些包及版本，以随附 `.manifest` 为准；OpenClash 的 MIT 许可不覆盖其调用的 GPL 核心、其他面板或第三方数据集。

表中固定标签和 `licenses/` 的文本保留初始参考来源。V2.3 起 OpenClash/Mihomo 每次构建解析最新正式标签，实际源码入口、许可证 URL 与哈希见 build-info.json；相应标签的原文同时保存在固件和附件的 `OpenClash-current-LICENSE.txt`、`mihomo-current-LICENSE.txt`（附件名前另加 `LICENSE-`）。当前上游条款与初始参考不一致时，以实际组件适用的上游条款为准，不能把旧快照当作新版本的授权。

## 保留许可与取得源码

V3.0 新增可选 iStore，来源为 [istoreos/istore](https://github.com/istoreos/istore)，作者 LinkEase 团队及贡献者，仓库采用 [MIT](https://github.com/istoreos/istore/blob/main/LICENSE)。它是软件中心组件，不是将系统替换为 iStoreOS。仅选择该功能时使用作者 APK 签名源；实际源码修订、源地址和许可证哈希记录在 build-info.json，相应修订许可证原文保存在固件与附件的 istore-current-LICENSE.txt。依赖与后续安装的应用继续适用各自许可证，不由 iStore 的 MIT 统一覆盖。

主要许可文本保存在 `licenses/`。固件中也保留于 `/usr/share/firmware-builder/`，构建 Artifact 会随附这些文本、此说明及 `SOURCE-REFERENCES.md`。不删除上游软件自身附带的版权和许可证声明。

本项目生成的是组合固件，不能把整个固件统一标成 MIT 或其他单一许可证。本仓库自写自动化脚本的许可证尚未单独指定；第三方组件继续适用其原许可证。

注明来源不替代许可证义务。再分发 GPL 等组件的二进制时，还须按具体许可提供对应源码及相关构建资料，并保证相应源码可取得。可结合：

- 本次 `SOURCE-REFERENCES.md`、`build-info.json`、`.manifest` 确认系统、插件与包版本。
- 对应 OpenWrt 发布目录中的 `config.buildinfo`、`feeds.buildinfo`，以及 [官方源码下载服务](https://sources.openwrt.org/) 查找源码和构建资料。
- 对应上游代码仓库、标签、依赖声明和构建配方取得插件及核心源码。
- [GNU 官方许可 FAQ](https://www.gnu.org/licenses/gpl-faq.en.html) 核对二进制与对应源码提供方式。

随附的来源引用不是所有包的完整对应源码归档，也不表示已对每个自选包的再分发条件做完审查。额外添加的软件、规则、Geo 数据、面板或订阅内容还可能有单独的授权条款，应保留并遵守。

## 安装与更新来源

- OpenWrt 基础包：当前版本的 OpenWrt 官方软件源，保留其签名检查。
- Nikki：插件作者提供的 `https://nikkinikki.pages.dev` 签名源，按 OpenWrt 分支与 `x86_64` 架构选择，并随固件保留上游源、公钥。它是 Nikki 上游源，不是 OpenWrt 官方软件源。公钥哈希和文档修订记录在 `configs/plugins.lock.json` / `build-info.json`。
- OpenClash：按作者的 Release 分发方式安装最新正式版本，并保留其内置更新机制；不添加未经作者确认的软件源。Mihomo 核心按实际选择记录来源和版本。

本项目只生成配置、拼装固件和提供检验流程，不接收或再分发用户的私人订阅与凭据。
