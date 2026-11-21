# RDK X5 v0.3.2 → v0.3.3 原地更新

支持本项目真板验证的 v0.3.2 镜像（fnOS ARM 1.2.0701、Linux 6.18.0）。更新只替换 `/usr/lib/fnos-x5/quark_log_compat.py` 和 `/etc/fnos-x5/release`。系统分区中的 `/var/lib/fnos-x5/update-v0.3.3/` 保存回滚副本。同一更新包可重复执行。升级或回滚过程中中断后，使用同一个包重试 `apply` 或执行 `rollback`。

在源码根目录用 Python 3 构建更新包。

```sh
python3 -m fnos.integration.in_place_update.build rdk-x5-fnos-v0.3.2-to-v0.3.3.pyz
sha256sum rdk-x5-fnos-v0.3.2-to-v0.3.3.pyz
```

将包传到 X5，和 [release.json](../../../release.json) 中的 `in_place_update.sha256` 核对。把包放在系统分区，方便应用更新后再次使用。

```sh
sudo install -o root -g root -m 0600 rdk-x5-fnos-v0.3.2-to-v0.3.3.pyz /var/lib/fnos-x5/
sudo python3 /var/lib/fnos-x5/rdk-x5-fnos-v0.3.2-to-v0.3.3.pyz status
sudo python3 /var/lib/fnos-x5/rdk-x5-fnos-v0.3.2-to-v0.3.3.pyz apply
```

成功后命令输出 `v0.3.3`。下次应用中心触发兼容服务时会使用更新后的脚本。需要回滚时执行以下命令，成功后输出 `v0.3.2`。

```sh
sudo python3 /var/lib/fnos-x5/rdk-x5-fnos-v0.3.2-to-v0.3.3.pyz rollback
```
