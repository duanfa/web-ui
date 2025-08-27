import pdb
from dotenv import load_dotenv
import os
from playwright.async_api import async_playwright
import sys
browser_use_path = os.path.join(os.path.dirname(__file__), '..', 'browser-use')
if browser_use_path not in sys.path:
    sys.path.insert(0, browser_use_path)

import traceback
load_dotenv()
import logging
logger = logging.getLogger(__name__)
# from browser_use.browser.context import BrowserContext

import asyncio
from pydantic import BaseModel, Field
import re

class ActionResult(BaseModel):
	"""Result of executing an action"""

	is_done: bool | None = False
	success: bool | None = None
	extracted_content: str | None = None
	error: str | None = None
	include_in_memory: bool = False  # whether to include in past messages as context or not


class ApplyMeetingRoomAction(BaseModel):
    room_name: str = Field(..., description='会议室名称')
    start_time: str = Field(..., description='会议开始时间，格式：YYYY-MM-DD HH:MM')
    end_time: str = Field(..., description='会议结束时间，格式：YYYY-MM-DD HH:MM')
    apply_button_index: int | None = Field(None, description='申请会议室按钮的索引，如果不提供则自动查找')


async def test_connect_browser():

    # chrome_exe = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    chrome_use_data = "/Users/duanfa/chromeData/Google/Chrome-browseruse-test"

    chrome_exe = os.getenv("BROWSER_PATH", "")
    # chrome_use_data = os.getenv("BROWSER_USER_DATA", "/Users/duanfa/chromeData/Google/Chrome-browseruse-test")
    # chrome_use_data = "/Users/duanfa/chromeData/Google/Chrome-browseruse"

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=chrome_use_data,
            executable_path=chrome_exe,
            headless=False  # Keep browser window visible
        )

        page = await browser.new_page()
        await page.goto("https://cloud.seeyon.com/c/expintroduce?id=162634020513720000&module=166530360015950003&entranceName=PC%E7%AB%AF-%E4%BD%93%E9%AA%8C%E4%B8%AD%E5%BF%83-%E5%B9%B3%E5%8F%B0")
        await page.wait_for_load_state()

        
        # 方法2：尝试使用 CDP (Chrome DevTools Protocol) 来检测所有标签页
        try:
            print("尝试使用CDP检测所有标签页...")
            cdp_session = await page.context.new_cdp_session(page)
            
            # 获取所有目标（包括所有标签页）
            targets = await cdp_session.send('Target.getTargets')
            print(f"CDP检测到 {len(targets['targetInfos'])} 个目标")
            
            for target in targets['targetInfos']:
                if target['type'] == 'page':
                    print(f"CDP页面: ID={target['targetId']}, 标题={target['title']}, URL={target['url']}")
                    
                    # 尝试附加到新页面
                    if '协同管理' in target.get('title', '') or 'meeting' in target.get('url', '').lower():
                        print(f"发现可能的会议页面: {target['title']}")
                        try:
                            new_page = await page.context.new_page()
                            await new_page.goto(target['url'])
                            print(f"成功导航到新页面: {target['url']}")
                            # 更新当前页面引用
                            page = new_page
                            break
                        except Exception as e:
                            print(f"无法导航到新页面: {str(e)}")
                            
        except Exception as e:
            print(f"CDP检测失败: {str(e)}")
        
        # 尝试多种选择器来找到"新建会议"按钮

         # 直接查找元素，不等待可见性
        meeting_div = await page.query_selector('//div[@title="新建会议"]')
        
        if not meeting_div:
            print("未找到'新建会议'元素，尝试其他选择器...")
            # 尝试其他选择器
            alternative_selectors = [
                '//div[contains(@class, "lev2Title") and contains(@title, "新建会议")]',
                '//div[contains(@class, "navTitleName") and contains(@title, "新建会议")]',
                '//div[contains(@onclick, "meetingNavigation")]'
            ]
            
            for selector in alternative_selectors:
                try:
                    meeting_div = await page.query_selector(selector)
                    if meeting_div:
                        print(f"使用选择器找到元素: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"选择器 {selector} 失败: {str(e)}")
                    continue
        
        if not meeting_div:
            raise Exception("无法找到'新建会议'元素")
        
        print("成功找到'新建会议'元素")
        
        # 尝试多种点击方法，考虑到元素可能有特殊的交互要求
        
        try:
            # 方法3：JavaScript点击
            logger.debug("尝试JavaScript点击...")
            await page.evaluate("(element) => element.click()", meeting_div)
            print("JavaScript点击成功")
        except Exception as e3:
            logger.debug(f"JavaScript点击失败: {str(e3)}")
            
        print("等待页面响应...")
        await asyncio.sleep(2)

        # 跳转到新打开的页面（假设点击后会新开一个tab）
        pages = page.context.pages
        if len(pages) > 1:
            page = pages[-1]
            print("已切换到新打开的页面")
        else:
            print("未检测到新页面，继续使用当前页面")
            
       
        params = ApplyMeetingRoomAction(room_name="2楼标准会议室", start_time="2025-10-21 14:30", end_time="2025-10-21 15:30")
       
        # input("Press the Enter key to close the browser...")
        await apply_meeting_room(params, page)
        browser.close()


async def apply_meeting_room(params:ApplyMeetingRoomAction,page):

    
    try:
        # 步骤1: 查找并点击"申请会议室"按钮
        apply_button = None
       
        # 点击申请会议室按钮
        element_handle = await page.query_selector('//div[@id="roomAppBtn"]');
        if not element_handle:
            raise Exception('Could not locate apply meeting room button element')
        
        iframeSelector = '//div[@id="meetingRoomDialog_main"]/iframe'
        iframe = await page.query_selector(iframeSelector);
        if not iframe:
            await element_handle.click()
            print('Clicked apply meeting room button')
            await asyncio.sleep(0.2)  # 等待弹窗出现
        
        # 步骤2: 在弹出的会议室选择窗口中选择会议室
        # 查找会议室选择弹窗
    
        # iframeSelector = '//div[@id="meetingRoomDialog_main"]/iframe'
        iframe = await page.query_selector(iframeSelector);
        iframeContent = await iframe.content_frame()
        if not iframeContent:
            raise Exception('Could not find room selection dialog')
        
        start_year, start_month, start_day, start_hour, start_minute = None, None, None, None, None
        start_time = params.start_time
        match_time = re.match(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})[ T](\d{1,2}):(\d{1,2})', start_time)
        if match_time:
            start_year = int(match_time.group(1))
            start_month = int(match_time.group(2))
            start_day = int(match_time.group(3))
            start_hour = int(match_time.group(4))
            start_minute = int(match_time.group(5))

        end_year, end_month, end_day, end_hour, end_minute = None, None, None, None, None
        end_time = params.end_time
        match_time = re.match(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})[ T](\d{1,2}):(\d{1,2})', end_time)
        if match_time:
            end_year = int(match_time.group(1))
            end_month = int(match_time.group(2))
            end_day = int(match_time.group(3))
            end_hour = int(match_time.group(4))
            end_minute = int(match_time.group(5))   

        print(f'解析到 params.start_time: {start_year}年{start_month}月{start_day}日 {start_hour}:{start_minute}')
        print(f'解析到 params.end_time: {end_year}年{end_month}月{end_day}日 {end_hour}:{end_minute}')
        dateBlock = await iframeContent.query_selector('//div[@class="dhx_cal_dateContainer"]/div[@class="dhx_cal_date"]')
        if dateBlock:
            date_text = await dateBlock.inner_html()
            # 解析 date_text，格式为：2025年 8月 21日
            match = re.match(r'(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日', date_text)
            if match:
                DefaultYear = int(match.group(1))
                DefaultMonth = int(match.group(2))
                DefaultDay = int(match.group(3))
                print(f'解析到日期: {DefaultYear}年{DefaultMonth}月{DefaultDay}日')
            # 解析 params.start_time 的 年月日，时分
            # 假设 params.start_time 是字符串格式，如 "2025-08-21 14:30"
           

                if start_year == DefaultYear and start_month == DefaultMonth and start_day == DefaultDay:
                    # 如果开始时间与默认日期相同，则使用默认日期
                    print(f'使用默认日期: {start_year}年{start_month}月{start_day}日')
                else:
                    # 如果开始时间与默认日期不同，则使用开始时间
                    # start_year = start_year
                    # start_month = start_month
                    # start_day = start_day
                    # print(f'使用开始时间: {start_year}年{start_month}月{start_day}日')
                # else:
                    # /html/body/div[6]/table/thead/tr[1]/td[2]
                    #9月, 2025
                    calendar_span = await iframeContent.query_selector('//span[@class="calendar_icon"]')
                    if calendar_span:
                        await calendar_span.click()
                        await asyncio.sleep(0.2)
                        while True:
                            cal_day_div = await iframeContent.query_selector('//div[contains(@class, "calendar")  and contains(@class, "miniCalendar")]/table/thead/tr/td[@class="title"]')
                            if cal_day_div:
                                # cal_day_text = await cal_day_div.get_inner_text()
                                cal_day_text = await cal_day_div.text_content()
                                # cal_day_text 的格式：9月, 2025，解析为 cal_month, cal_year
                                # 例如 cal_day_text = "9月, 2025"
                                cal_month, cal_year = None, None
                                if cal_day_text:
                                    match_cal = re.match(r'(\d{1,2})月,\s*(\d{4})', cal_day_text)
                                    if match_cal:
                                        cal_month = int(match_cal.group(1))
                                        cal_year = int(match_cal.group(2))
                                        print(f'解析到日历年月: {cal_year}年{cal_month}月')

                                        if cal_year > start_year:
                                            cal_year_left_button = await iframeContent.query_selector('//div[contains(@class, "calendar")  and contains(@class, "miniCalendar")]/table/thead/tr[@class="headrow"]/td/div[text()="«"]')  
                                            if cal_year_left_button:
                                                await cal_year_left_button.click()
                                                await asyncio.sleep(0.2)
                                                continue		
                                        elif cal_year < start_year:
                                            cal_year_right_button = await iframeContent.query_selector('//div[contains(@class, "calendar")  and contains(@class, "miniCalendar")]/table/thead/tr[@class="headrow"]/td/div[text()="»"]')
                                            if cal_year_right_button:
                                                await cal_year_right_button.click()
                                                await asyncio.sleep(0.2)
                                                continue
                                        
                                        if cal_month > start_month:
                                            cal_month_left_button = await iframeContent.query_selector('//div[contains(@class, "calendar")  and contains(@class, "miniCalendar")]/table/thead/tr[@class="headrow"]/td/div[text()="‹"]')
                                            if cal_month_left_button:
                                                    await cal_month_left_button.click()
                                                    await asyncio.sleep(0.2)
                                                    continue
                                        elif cal_month < start_month:
                                            cal_month_right_button = await iframeContent.query_selector('//div[contains(@class, "calendar")  and contains(@class, "miniCalendar")]/table/thead/tr[@class="headrow"]/td/div[text()="›"]')
                                            if cal_month_right_button:
                                                await cal_month_right_button.click()
                                                await asyncio.sleep(0.5)
                                                continue
                                        
                                        chose_Day = await iframeContent.query_selector('//div[contains(@class, "calendar")  and contains(@class, "miniCalendar")]/table/tbody/tr/td[@class="day" and text()="'+str(start_day)+'"]')
                                        if chose_Day:
                                            await chose_Day.click()
                                            await asyncio.sleep(0.2)

                                        break

            else:
                print(f'无法解析 params.start_time: {start_time}')

        miniCalendarOkBtn = await iframeContent.query_selector('//div[contains(@class, "miniCalendar")]//span[contains(@class, "common_button_emphasize") and text()="确定"]')
        if miniCalendarOkBtn:
            await miniCalendarOkBtn.click()
            await asyncio.sleep(0.1)

        # 在弹窗中搜索并选择指定的会议室
        search_input_selectors = [
            'input[placeholder*="请输入会议室名称"]',
            'input[placeholder*="搜索"]',
            'input[type="text"]'
        ]
        
        search_input = None
        for selector in search_input_selectors:
            try:
                search_input = await iframeContent.query_selector(selector)
                if search_input:
                    print(f'Found search input with selector: {selector}')
                    break
            except:
                continue
        
        if search_input:
            # 清空并输入会议室名称
            await search_input.fill('')
            await search_input.type(params.room_name, delay=100)
            print(f'Input room name: {params.room_name}')
            
            # 按回车键搜索
            search_button = await iframeContent.query_selector('//a[contains(@class, "search_buttonHand") and contains(@class, "search_button")]')
            if search_button:
                await search_button.click()
            await asyncio.sleep(0.5)  # 等待搜索结果


        minute_value = 0
        minute_str = ""
        while True:
            if minute_value < start_minute:
                if minute_value + 5 > start_minute:
                    break
                minute_value += 5
            if minute_value == start_minute:
                break
            if minute_value > 55   :
                minute_value = 55
                break
        if minute_value == 0:
            minute_str = "00"
        elif minute_value == 5:
            minute_str = "05"
        else:
            minute_str = str(minute_value)

        
        
        # 选择第一个搜索结果（会议室）
        room_result_selector = '//div[@class="dhx_matrix_line" and @data-section-index="1"]/div[contains(@class, "dhx_timeline_data_row")]/div'
        timeBlockList = await iframeContent.query_selector_all(room_result_selector)

        room_result = None
        for timeBlock in timeBlockList:
            try:
                print(await timeBlock.get_attribute('data-col-date'))
            except:
                continue

        start_cell = iframeContent.locator('//div[@class="dhx_timeline_data_col"]/div[2]/div/div[contains(@class, "dhx_timeline_data_cell") and @data-col-date="2025-10-21 10:00"]')
        end_cell = iframeContent.locator('//div[@class="dhx_timeline_data_col"]/div[2]/div/div[contains(@class, "dhx_timeline_data_cell") and @data-col-date="2025-10-21 14:00"]')
        
        # 执行拖拽操作  
        await start_cell.drag_to(end_cell)
        await asyncio.sleep(0.2)

        # 等待元素可见
        await start_cell.wait_for(state="visible")
        await end_cell.wait_for(state="visible")

        # 检查元素是否可交互
        start_visible = await start_cell.is_visible()
        end_visible = await end_cell.is_visible()
        print(f"Start cell visible: {start_visible}, End cell visible: {end_visible}")

        if start_visible and end_visible:
            # 执行拖拽操作
            await start_cell.drag_to(end_cell)
            print("Drag operation completed")
        else:
            print("Cells are not visible for drag operation")
        
        if room_result:
            await room_result.click()
            print(f'Selected meeting room: {params.room_name}')
            await asyncio.sleep(1)
        else:
            print(f'No room result found for: {params.room_name}')



         # 3333333333333
        start_box = await start_cell.bounding_box()
        end_box = await end_cell.bounding_box()
        
        if start_box and end_box:
            # 计算中心点
            start_x = start_box['x'] + start_box['width'] / 2
            start_y = start_box['y'] + start_box['height'] / 2
            end_x = end_box['x'] + end_box['width'] / 2
            end_y = end_box['y'] + end_box['height'] / 2
            
            # 获取 iframe 的位置信息，用于坐标转换
            iframe_box = await iframe.bounding_box()
            if iframe_box:
                # 将 iframe 内的坐标转换为页面坐标
                page_start_x = iframe_box['x'] + start_x
                page_start_y = iframe_box['y'] + start_y
                page_end_x = iframe_box['x'] + end_x
                page_end_y = iframe_box['y'] + end_y
                
                # 使用 page.mouse 进行拖拽操作
                await page.mouse.move(page_start_x, page_start_y)
                await page.mouse.down()
                await page.mouse.move(page_end_x, page_end_y)
                await page.mouse.up()
                
                logger.info(f"Manual drag from {start_time} to {end_time}")
            else:
                logger.error("Could not get iframe position")
                # return False
        else:
            logger.error("Could not get element positions")
            # return False
        

        # 44444444
        start_count = await start_cell.count()
        end_count = await end_cell.count()
        logger.info(f"Found {start_count} start cells, {end_count} end cells")

        # 检查元素属性
        if start_count > 0:
            start_attrs = await start_cell.first.get_attribute('class')
            logger.info(f"Start cell classes: {start_attrs}")

        if end_count > 0:
            end_attrs = await end_cell.first.get_attribute('class')
            logger.info(f"End cell classes: {end_attrs}")

        # 尝试拖拽
        if start_count > 0 and end_count > 0:
            try:
                await start_cell.first.drag_to(end_cell.first)
                logger.info("Drag operation successful")
            except Exception as e:
                logger.error(f"Drag operation failed: {e}")
        
        # 步骤3: 设置会议时间
        # 查找开始时间输入框
        start_time_selectors = [
            'input[placeholder*="开始时间"]',
            'input[placeholder*="开始"]',
            'input[name*="start"]',
            'input[id*="start"]'
        ]
        
        start_time_input = None
        for selector in start_time_selectors:
            try:
                start_time_input = await iframeContent.query_selector(selector)
                if start_time_input:
                    print(f'Found start time input with selector: {selector}')
                    break
            except:
                continue
        
        if start_time_input:
            await start_time_input.fill('')
            await start_time_input.type(params.start_time, delay=100)
            print(f'Set start time: {params.start_time}')
            await asyncio.sleep(0.5)
        
        # 查找结束时间输入框
        end_time_selectors = [
            'input[placeholder*="结束时间"]',
            'input[placeholder*="结束"]',
            'input[name*="end"]',
            'input[id*="end"]'
        ]
        
        end_time_input = None
        for selector in end_time_selectors:
            try:
                end_time_input = await iframeContent.query_selector(selector)
                if end_time_input:
                    print(f'Found end time input with selector: {selector}')
                    break
            except:
                continue
        
        if end_time_input:
            await end_time_input.fill('')
            await end_time_input.type(params.end_time, delay=100)
            print(f'Set end time: {params.end_time}')
            await asyncio.sleep(0.5)
        
        # 步骤4: 点击确定按钮
        confirm_button_selectors = [
            '//button[contains(text(), "确定")]',
            '//button[contains(text(), "确认")]',
            '//a[contains(@class, "ok")]',
            '//button[contains(@class, "confirm")]'
        ]
        
        confirm_button = None
        for selector in confirm_button_selectors:
            try:
                confirm_button = await page.query_selector(selector)
                if confirm_button:
                    print(f'Found confirm button with selector: {selector}')
                    break
            except:
                continue
        
        if confirm_button:
            await confirm_button.click()
            print('Clicked confirm button')
            await asyncio.sleep(2)  # 等待操作完成
        else:
            print('Could not find confirm button')
        
        msg = f'✅ 成功申请会议室: {params.room_name}，时间: {params.start_time} - {params.end_time}'
        print(msg)
        return 
    
    except Exception as e:
        error_msg = f'申请会议室失败: {str(e)}'
        traceback.print_exc()
        print(error_msg)
        return 

# Register ---------------------------------------------------------------



if __name__ == '__main__':
    asyncio.run(test_connect_browser())
