import codecs
import errno
import os
import pty
import shlex
import signal
import subprocess
import termios
from collections.abc import Sequence

def normalize_output(output:str)->str:
    # 和安静模式(text=True)保持一致：\r\n和单独的\r都换成\n
    return output.replace("\r\n","\n").replace("\r","\n")

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
        result=subprocess.run(command_list,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace",cwd=cwd)
        # text=True时Python已经把\r\n和\r都换成了\n，不需要再normalize_output
        output=result.stdout
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
            # 创建失败时没有子进程，slave_fd由下面的finally关闭，这里只需关闭master_fd
            os.close(master_fd)
            raise
        finally:
            # 无论子进程是否成功创建，父进程都不再需要slave_fd
            os.close(slave_fd)
        # 读取master_fd
        # 一个汉字占3个字节，可能被两次读取切开，增量解码器会把不完整的字节留到下一次再解码
        decoder=codecs.getincrementaldecoder("utf-8")(errors="replace")
        chunks=[]
        try:
            while True:
                try:
                    # 每次最多读取4096字节
                    data=os.read(master_fd,4096)
                except OSError as e:
                    # 子进程及其启动的进程都关闭输出后，Linux上os.read会报EIO，表示输出已经读完
                    if e.errno==errno.EIO:
                        break
                    raise
                if not data:
                    break
                text=decoder.decode(data)
                print(text,end="",flush=True)
                chunks.append(text)
            text=decoder.decode(b"",final=True)
            print(text,end="",flush=True)
            chunks.append(text)
            # 子进程可能先关掉输出再继续运行，等它退出的这段时间也要能被Ctrl+C中断
            return_code=proc.wait()
        except BaseException:
            # 不论是Ctrl+C还是其他错误，都先结束子进程及其启动的进程，再把错误抛出去
            terminate_process_group(proc)
            raise
        finally:
            os.close(master_fd)
        output=normalize_output("".join(chunks))
        if return_code!=0:
            raise subprocess.CalledProcessError(return_code,command_list,output=output)
        return output
