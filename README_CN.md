# run_command

[English](README.md) | **中文**

`run_command`从Python里运行一条外部命令。默认在命令运行时把输出实时显示在屏幕上，并把全部输出作为字符串返回。命令失败时报错。只支持Linux。

## 用法

仓库以子模块形式放在`third_party/run_command`时：

```python
from third_party.run_command.run_command import run_command

output=run_command("cmake --build build --parallel 8")
output=run_command(["cmake","--build","build","--parallel",8],cwd="/path/to/project")
run_command("cmake --install build",silent=True)
```

- 命令可以是字符串，会像shell一样拆成参数，也可以是参数列表，列表里的数字和路径会自动转成字符串。
- 命令直接运行，不经过shell，所以管道（`|`）、重定向（`>`）、变量（`$HOME`）和通配符（`*`）都不能用。
- `cwd`指定命令在哪个目录下运行。
- 正常输出和错误输出按原来的先后顺序合并。返回的字符串里，`\r\n`和`\r`都换成了`\n`。

## 两种模式

- 默认模式：命令运行时，输出一行一行地显示在屏幕上，和直接在终端里运行一样，颜色和进度条都能正常显示。
- `silent=True`：运行时什么都不显示。命令失败时，先打印它的输出，再报错。

## 报错

- 退出码不是0时抛出`subprocess.CalledProcessError`，它的`returncode`和`output`分别是退出码和全部输出。
- 找不到命令时抛出`FileNotFoundError`。
- 按Ctrl+C时，命令和它启动的所有进程都会被结束。
