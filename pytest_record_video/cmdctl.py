#!/usr/bin/env python3
# _*_ coding:utf-8 _*_

# SPDX-FileCopyrightText: 2023 UnionTech Software Technology Co., Ltd.

import sys
import subprocess

from funnylog import logger


class CmdCtl:
    """命令行工具"""

    @staticmethod
    def _run(command, _input=None, timeout=None, check=False, **kwargs):
        """run"""
        with subprocess.Popen(command, **kwargs) as process:
            try:
                stdout, stderr = process.communicate(_input, timeout=timeout)
            except:  # Including KeyboardInterrupt, communicate handled that.
                process.kill()
                raise
            ret_code = process.poll()
            if check and ret_code:
                raise subprocess.CalledProcessError(
                    ret_code, process.args, output=stdout, stderr=stderr
                )
        return subprocess.CompletedProcess(process.args, ret_code, stdout, stderr)

    @classmethod
    def _getstatusoutput(cls, command, timeout):
        """getstatusoutput"""
        kwargs = {
            "shell": True,
            "stderr": subprocess.STDOUT,
            "stdout": subprocess.PIPE,
            "timeout": timeout,
        }
        try:
            if sys.version_info >= (3, 7):
                kwargs["text"] = True
            result = cls._run(command, **kwargs
                              )
            data = result.stdout
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            exitcode = result.returncode
        except subprocess.CalledProcessError as ex:
            data = ex.output
            exitcode = ex.returncode
        except subprocess.TimeoutExpired as ex:
            data = ex.__str__()
            exitcode = -1
        if data[-1:] == "\n":
            data = data[:-1]
        return exitcode, data

    @classmethod
    def run_cmd(cls, command, interrupt=False, timeout=25, out_debug_flag=True, command_log=True):
        """
         执行shell命令
        :param command: shell 命令
        :param interrupt: 命令异常时是否中断
        :param timeout: 命令执行超时
        :param out_debug_flag: 命令返回信息输出日志
        :param command_log: 执行的命令字符串日志
        :return: 返回终端输出
        """
        status, out = cls._getstatusoutput(command, timeout=timeout)
        if command_log:
            logger.debug(command)
        if status and interrupt:
            raise f"shell执行失败！| {out}"
        if out_debug_flag and out:
            logger.debug(out)
        return out
