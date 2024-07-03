#!/usr/bin/env python3
# _*_ coding:utf-8 _*_

import allure
import pytest

from os import remove
from os.path import exists
from os.path import splitext
from time import sleep
from funnylog import logger
from shutil import copyfile
from datetime import datetime
from pytest_record_video.cmdctl import CmdCtl
from pytest_record_video.recording_screen import recording_screen


def pytest_addoption(parser):
    parser.addoption(
        "--record_video", action="store", default=False,
        help="用例录屏，开启后每条用例都录制视频"
    )
    parser.addoption(
        "--record_failed_video", action="store", default=False,
        help="失败录屏，开启后只有失败用例保存视频"
    )
    parser.addoption(
        "--record_failed_num", action="store", default=False,
        help="失败录屏，从第几次失败开始录制视频，此参数需要结合 pytest-rerunfailures 插件使用"
    )


def pytest_runtest_setup(item):
    print()

    # 用例执行前，判断是否开启录屏
    if (item.config.option.record_video
            or item.config.option.record_failed_video
            or item.config.option.record_failed_num):
        item.record = {}
        _job_dir = item.session.fspath.strpath
        _record_name = f'{item.name}_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'

        try:
            if item.config.option.record_video or item.config.option.record_failed_video:
                # 用例录屏
                item.record["object"] = recording_screen(_record_name, _job_dir)
                item.record["image_path"] = next(item.record["object"])
                sleep(3)
            elif item.config.option.record_failed_num:
                # 失败录屏，从第几次失败开始录制视频，此参数需要结合 pytest-rerunfailures 插件使用
                execution_count = getattr(item, "execution_count", False)
                if (execution_count is not False
                        and execution_count > int(item.config.option.record_failed_num)):
                    item.record["object"] = recording_screen(_record_name, _job_dir)
                    item.record["image_path"] = next(item.record["object"])
                    sleep(3)

        except Exception as e:
            logger.info(f"录屏失败: {e}")


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    out = yield
    report = out.get_result()

    try:
        if (item.config.option.record_video
                or item.config.option.record_failed_video
                or item.config.option.record_failed_num):
            if report.when == "call":  # 存放录屏当次测试结果
                item.record["result"] = report.outcome
                try:
                    # 记录断言的模板图片
                    item.record["template"] = call.excinfo.value.args[0].args[1:]
                except (IndexError, KeyError, AttributeError):
                    # 记录ocr识别区域图片
                    try:
                        pic = call.excinfo.value.args[0][1]
                        if isinstance(pic, tuple):
                            item.record["ocr"] = call.excinfo.value.args[0][1]
                    except (IndexError, AttributeError, TypeError):
                        # 非ocr断言
                        pass
            elif report.when == "teardown":
                try:
                    sleep(3)
                    # 调用生成器保存视频
                    next(item.record["object"])
                except StopIteration:
                    _case_passed = "passed"
                    # 录屏时测试结果为passed，则删除视频
                    _is_remove_record = (item.record.get("result") == _case_passed
                                         and item.config.option.record_video is False)
                    if _is_remove_record:
                        try:
                            remove(item.record["image_path"])
                        except FileNotFoundError:
                            pass
                    else:
                        _screen_cache = "/tmp/screen.png"
                        if exists(_screen_cache):
                            screen_png = f"{splitext(item.record['image_path'])[0]}.png"
                            copyfile(_screen_cache, screen_png)
                            allure.attach.file(
                                screen_png,
                                name="屏幕截图",
                                attachment_type=allure.attachment_type.PNG,
                            )
                            try:
                                for index, tem in enumerate(item.record["template"]):
                                    template = f"{splitext(item.record['image_path'])[0]}_template_{index}.png"
                                    CmdCtl.run_cmd(f"cp {tem}.png {template}")
                                    allure.attach.file(
                                        template,
                                        name="模板图片",
                                        attachment_type=allure.attachment_type.PNG,
                                    )
                            except (FileNotFoundError, KeyError):
                                # 非图像识别错误
                                pass
                            try:
                                template = f"{splitext(item.record['image_path'])[0]}_ocr_.png"
                                CmdCtl.run_cmd(f"cp {item.record['ocr']} {template}")
                                allure.attach.file(
                                    template,
                                    name="OCR识别区域",
                                    attachment_type=allure.attachment_type.PNG,
                                )
                            except KeyError:
                                # ocr 识别区域
                                pass
                        allure.attach.file(
                            item.record["image_path"],
                            name="用例视频",
                            attachment_type=allure.attachment_type.MP4,
                        )
                    logger.info(
                        "结束录屏! "
                        f"{'用例测试通过，删除视频录像' if _is_remove_record else ''}"
                    )
    except (AttributeError, KeyError):
        pass
