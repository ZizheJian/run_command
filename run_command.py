import errno
import os
import pty
import shlex
import signal
import subprocess
import termios
from collections.abc import Sequence

def normalize_output(output:str)->str:
    return output.replace("\r\n","\n")

def terminate_process_group(proc:subprocess.Popen):
    try:
        os.killpg(proc.pid,signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid,signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()

def run_command(command:str|Sequence[object],silent:bool=False,cwd:str|None=None)->str:
    command_list=shlex.split(command) if isinstance(command,str) else [str(value) for value in command]
    if not command_list:
        raise ValueError(f"没有成功解析指令：{command}")
    if silent:
        result=subprocess.run(command_list,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace",
                              cwd=cwd)
        output=normalize_output(result.stdout)
        if result.returncode!=0:
            if output:
                print(output,end="" if output.endswith("\n") else "\n")
            raise subprocess.CalledProcessError(result.returncode,command_list,output=output)
        return output
    else:
        # 构造master_fd和slave_fd，slave_fd收到的信息会自动发给master_fd
        master_fd,slave_fd=pty.openpty()
        terminal_attributes=termios.tcgetattr(slave_fd)
        terminal_attributes[1]&=~termios.ONLCR
        termios.tcsetattr(slave_fd,termios.TCSANOW,terminal_attributes)
        try:
            # 创建子进程，全部输出到slave_fd
            proc=subprocess.Popen(command_list,stdout=slave_fd,stderr=slave_fd,cwd=cwd,start_new_session=True,close_fds=True)
        except BaseException:
            # 如果创建子进程失败，子进程会自动关闭slave_fd，父进程需要关闭master_fd
            os.close(master_fd)
            raise
        finally:
            # 无论子进程是否成功创建，父进程都不再需要slave_fd
            os.close(slave_fd)
        # 读取master_fd
        chunks=[]
        try:
            while True:
                try:
                    # 每次最多读取4096字节
                    data=os.read(master_fd,4096)
                except OSError as e:
                    # 子进程退出时，os.read可能会误报EIO错误
                    if e.errno==errno.EIO:
                        break
                    raise e
                if not data:
                    break
                text=data.decode("utf-8",errors="replace")
                print(text,end="",flush=True)
                chunks.append(text)
        except KeyboardInterrupt:
            terminate_process_group(proc)
            raise
        finally:
            os.close(master_fd)
        return_code=proc.wait()
        output=normalize_output("".join(chunks))
        if return_code!=0:
            raise subprocess.CalledProcessError(return_code,command_list,output=output)
        return output
