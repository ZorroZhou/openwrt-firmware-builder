# 验证范围与结果

## 自动化检查

- 49 项单元与失败路径测试通过，四个工作流通过 actionlint 语法检查。
- [V3.1 构建矩阵](https://github.com/ZorroZhou/openwrt-firmware-builder/actions/runs/40638371282)：8/8 成功，覆盖两代 OpenWrt、x86/ARM64 代理组件、Docker、iStore 和 MIPS 固定闪存代表目标。
- 设备菜单由两代最新小版本的官方目录合并，1969 个选项自动绑定目标和 Profile；构建前实时核对所选版本。测试覆盖未知选择拒绝、跨目标区分、去重及元数据不符。
- 输入测试覆盖 IPv4、软件包名、版本范围、架构及字节序；镜像测试覆盖缺失、路径越界、容量策略及校验失败。未匹配的第三方组件或源会明确失败。
- 网络注入只定制已有 LAN 的管理地址，不修改官方 DHCP、IPv6、上游网关或 DNS；有不覆盖这些服务的回归检查。

## 官方目录与来源

- 25.12.6：核对官方 .overview.json 与各目标 profiles.json，90 个 target/subtarget、1941 个 Profile。
- 24.10.8：同样核对，82 个 target/subtarget、1718 个 Profile。跨版本 Profile 不代表不同物理设备，不能直接相加。
- iStore 使用锁定公钥哈希的作者 APK 签名源；不执行在线安装器，不开放会降低临时签名检查的 opkg 集成路径。
- ImageBuilder 不重编译 initramfs 内核；仍检查可拼装的 factory/sysupgrade/磁盘镜像，只有 initramfs 的设备提前拒绝。

## 测试边界

192.168.77.1 仅为一次性隔离 CI 固件的合成管理地址。QEMU 使用受限网络与快照；不连接部署环境。

x86/64/generic 检查 QEMU BIOS 启动，armsr/armv8/generic 检查 virt + EFI 启动。其他板级设备仅进行镜像和可用的跨架构用户态检查，不表述为板级启动验收。

官方设备目录覆盖不等于全部 Profile 都有可用 ImageBuilder 或第三方包，也不等于逐台硬件刷写成功。无线、端口、交换机、存储、真实代理流量和容器负载仍需按实际设备测试。
