# 验证记录

## V3.0 开发验收范围

日期：2026-10-28。当前公开描述使用通用测试环境，不包含个人设备或部署信息。

- 47 项单元与失败路径测试通过；四个工作流通过 actionlint。
- 最新两代菜单从官网生成，共 16 项（25.12.0–25.12.6、24.10.0–24.10.8）；旧第三代及第三代别名有拒绝测试。
- 多平台测试覆盖目标/Profile/版本对应关系、架构及字节序匹配、未知核心架构拒绝、固定闪存禁止套用磁盘分区、Docker/iStore 不兼容组合拒绝。
- 网络策略测试覆盖上游网关、DNS、自身地址冲突、缺字段与注入输入；旁路由关闭 LAN IPv4 DHCP、RA/DHCPv6/NDP，同时不停止 dnsmasq，不猜测端口名称。
- 镜像测试覆盖按官方设备元数据选择文件、缺失和校验失败；x86 保留已有磁盘结构与分区检查。
- 实际从 25.12.6 的官方 .overview.json 和全部 profiles.json 导出 90 个 target/subtarget、1941 个设备 Profile，与总览逐目标核对。目录里的 malta/be 没有对应已发布 Profile，已改用 Firmware Selector 的权威总览，而非把目录存在等同于支持设备。
- 首轮实构发现官方 Profile 含有源码构建的 initramfs 内核，ImageBuilder 不重新生成此类内核。已按工具实际能力区分，新增失败路径测试；没有跳过其余 factory/sysupgrade/磁盘镜像检查。
- iStore 审查了作者 README、网络安装器与包内 is-opkg：APK 源提供公钥，已锁定公钥哈希。opkg 包装器会剥除临时配置的签名检查，因此目前拒绝该集成路径；没有执行在线安装器或关闭全局源签名检查。
- 24.10.8 的完整官方目录也已导出并逐目标核对：82 个 target/subtarget、1718 个 Profile。跨版本 Profile 数不能当作不同硬件数量相加。
- [V3.0 矩阵](https://github.com/ZorroZhou/openwrt-firmware-builder/actions/runs/40634880054) 当前 7/8 成功；24.10 x86 Nikki + Docker 尚在构建，未计为通过。已通过的组合包括 x86/ARM64 OpenClash、ARM64 Nikki、ARM64 Docker、x86/ARM64 iStore 旁路由及 MIPS 固定闪存镜像。
- [ARM64 组合验收](https://github.com/ZorroZhou/openwrt-firmware-builder/actions/runs/40635187062) build 成功：25.12.6、armsr/armv8 generic、standard、512 MiB、iStore + OpenClash、旁路由。通过 EFI 隔离启动与模式检查，产物保存在该运行的 Artifacts；此次未公开发布 Release。实际包版本记录在 build-info.json、ACCESS.md 和 manifest 中。
- 当前工作流中的 192.168.77.1 以及组合测试使用的上游 192.168.77.254 均为受限 QEMU 网络的一次性测试配置，不是任何现有设备地址，也不表示上游连通性已验证。已通过的 x86 generic 验证 BIOS 启动，ARM64 generic 验证 virt + EFI；其他板级设备只能按日志记录镜像与跨架构用户态检查，不能宣称已启动硬件。
- 非 x86 Release 文本使用本地模拟 API 检查：目标/Profile 正确，固定闪存显示“官方设备布局”，不出现 None MiB；没有为此测试向外部发布内容。

## 已确认的历史发布基础

- [V2.3 最终矩阵](https://github.com/ZorroZhou/openwrt-firmware-builder/actions/runs/40624286914) 已于 2026-10-28 完成，11/11 成功；此前慢任务已核对为成功。
- [V2.3 手动构建与发布](https://github.com/ZorroZhou/openwrt-firmware-builder/actions/runs/40624437242) 的 build/release 均成功，所选代理在上传前通过隔离启动检查。
- 此前的矩阵不代表 V3.0 新设备、iStore 或模式切换已实机验收。

## 检查边界

所有设备入口来自官方目录，不代表所有 Profile 都已有可用 ImageBuilder 或第三方预编译包；缺少对应资源时明确失败。没有逐台硬件刷写、验证无线/交换机/存储，或测试真实代理订阅与容器负载。

旁路由模式不修改其他设备配置，不自动接管全网。Git 历史和既有标签未被重写；当前文件清理不能删除旧提交或第三方缓存中的历史内容。
