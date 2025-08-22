#!/usr/bin/env python3
"""
测试申请会议室action的脚本
"""

import sys
import os

# 添加browser-use项目路径到Python路径
browser_use_path = os.path.join(os.path.dirname(__file__), '..', 'browser-use')
if browser_use_path not in sys.path:
    sys.path.insert(0, browser_use_path)
    print(f"Added {browser_use_path} to Python path")

import asyncio
from browser_use.controller.views import ApplyMeetingRoomAction
from browser_use.controller.service import Controller
from browser_use.browser.context import BrowserContext

async def test_apply_meeting_room():
    """测试申请会议室action"""
    
    # 创建控制器实例
    controller = Controller()
    
    # 创建测试参数
    test_params = ApplyMeetingRoomAction(
        room_name="2楼多媒体会议室",
        start_time="14:00",
        end_time="16:00"
    )
    
    print("✅ 申请会议室action已成功创建")
    print(f"参数模型: {test_params}")
    print(f"会议室名称: {test_params.room_name}")
    print(f"开始时间: {test_params.start_time}")
    print(f"结束时间: {test_params.end_time}")
    
    # 检查action是否已注册
    if hasattr(controller, 'apply_meeting_room'):
        print("✅ apply_meeting_room action已成功注册到控制器")
    else:
        print("❌ apply_meeting_room action未找到")
    
    # 检查registry中是否有这个action
    action_names = [action.name for action in controller.registry.registry.actions.values()]
    if 'apply_meeting_room' in action_names:
        print("✅ apply_meeting_room action已成功注册到registry")
    else:
        print("❌ apply_meeting_room action未在registry中找到")
        print(f"可用的actions: {action_names}")

if __name__ == "__main__":
    asyncio.run(test_apply_meeting_room())
