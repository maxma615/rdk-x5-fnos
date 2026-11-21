# RDK X5 v0.3.2 → v0.3.3 原地更新

支持本项目真板验证的 v0.3.2 镜像（fnOS ARM 1.2.0701、Linux 6.18.0）。更新包包含 AIC8800 Wi-Fi 模块、应用兼容脚本和版本标记。系统分区中的 `/var/lib/fnos-x5/update-v0.3.3/` 保存原模块和脚本，用于回滚。同一更新包可重复执行。升级或回滚过程中中断后，使用同一个包重试 `apply` 或执行 `rollback`。

按[内核说明](../../../KERNEL.md#v033-aic8800-sdio-wi-fi-修复)构建匹配的 AIC8800 模块，然后在源码根目录用 Python 3 构建更新包。

```sh
python3 -m fnos.integration.in_place_update.build rdk-x5-fnos-v0.3.2-to-v0.3.3-wifi.pyz --wifi-module aic8800_fdrv.ko
sha256sum rdk-x5-fnos-v0.3.2-to-v0.3.3-wifi.pyz
```

将包传到 X5，和 [release.json](../../../release.json) 中的 `in_place_update.sha256` 核对。把包放在系统分区，方便应用更新后再次使用。

```sh
sudo install -o root -g root -m 0600 rdk-x5-fnos-v0.3.2-to-v0.3.3-wifi.pyz /var/lib/fnos-x5/
sudo python3 /var/lib/fnos-x5/rdk-x5-fnos-v0.3.2-to-v0.3.3-wifi.pyz status
sudo python3 /var/lib/fnos-x5/rdk-x5-fnos-v0.3.2-to-v0.3.3-wifi.pyz apply
sudo reboot
```

成功后命令输出 `v0.3.3`，重启加载新模块。可以从 `/sys/module/aic8800_fdrv/srcversion` 读取已加载版本并与 `release.json` 核对。回滚后命令输出 `v0.3.2`，重启加载原模块。原模块可能复现已知的 Wi-Fi 启动异常。

```sh
sudo python3 /var/lib/fnos-x5/rdk-x5-fnos-v0.3.2-to-v0.3.3-wifi.pyz rollback
sudo reboot
```
