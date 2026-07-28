import subprocess,os,pty,errno,shlex,signal

def run_command(command:str,silent:bool=False,cwd:str|None=None,env:dict[str,str]|None=None)->str:
    command_list=shlex.split(command)
    if not command_list:
        raise ValueError(f"没有成功解析指令：{command}")
    if silent:
        result=subprocess.run(command_list,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace",
                              cwd=cwd,env=env)
        if result.returncode!=0:
            if result.stdout:
                print(result.stdout)
                if not result.stdout.endswith("\n"):
                    print()
            raise subprocess.CalledProcessError(result.returncode,command_list,output=result.stdout)
        return result.stdout
    else:
        # 构造master_fd和slave_fd，slave_fd收到的信息会自动发给master_fd
        master_fd,slave_fd=pty.openpty()
        try:
            # 创建子进程，全部输出到slave_fd
            proc=subprocess.Popen(command_list,stdout=slave_fd,stderr=slave_fd,cwd=cwd,env=env,start_new_session=True,close_fds=True)
        except:
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
            try:
                os.killpg(proc.pid,signal.SIGTERM)
            except ProcessLookupError:
                pass
            proc.wait()
            raise
        finally:
            os.close(master_fd)
        return_code=proc.wait()
        output="".join(chunks)
        if return_code!=0:
            raise subprocess.CalledProcessError(return_code,command_list,output=output)
        return output