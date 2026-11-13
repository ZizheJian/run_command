# run_command

**English** | [中文](README_CN.md)

`run_command` runs an external command from Python. By default, it shows the output on screen while the command runs and returns the full output as a string. It raises an error when the command fails. Linux only.

## Usage

When the repository is a submodule at `third_party/run_command`:

```python
from third_party.run_command.run_command import run_command

output=run_command("cmake --build build --parallel 8")
output=run_command(["cmake","--build","build","--parallel",8],cwd="/path/to/project")
run_command("cmake --install build",silent=True)
```

- The command can be a string, which is split into arguments the way a shell would, or a list of arguments. Numbers and paths in the list are converted to strings.
- The command runs directly instead of through a shell, so pipes (`|`), redirection (`>`), variables (`$HOME`) and wildcards (`*`) do not work.
- `cwd` sets the directory in which the command runs.
- Normal output and error output are merged in their original order. In the returned string, `\r\n` and `\r` become `\n`.

## Two modes

- Default: the output appears on screen line by line while the command runs, the same as running it directly in a terminal, including colors and progress bars.
- `silent=True`: nothing is shown while the command runs. If the command fails, its output is printed before the error is raised.

## Errors

- A non-zero exit code raises `subprocess.CalledProcessError`. Its `returncode` and `output` hold the exit code and the full output.
- A command that cannot be found raises `FileNotFoundError`.
- Pressing Ctrl+C stops the command together with all the processes it started.
