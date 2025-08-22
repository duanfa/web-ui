import pdb
from dotenv import load_dotenv
import os
from playwright.sync_api import sync_playwright
import sys
browser_use_path = os.path.join(os.path.dirname(__file__), '..', 'browser-use')
if browser_use_path not in sys.path:
    sys.path.insert(0, browser_use_path)

load_dotenv()
import logging
logger = logging.getLogger(__name__)
# from browser_use.browser.context import BrowserContext

import asyncio


def test_connect_browser():

    # chrome_exe = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    # chrome_use_data = "/Users/duanfa/chromeData/Google/Chrome-browseruse"

    chrome_exe = os.getenv("BROWSER_PATH", "")
    chrome_use_data = os.getenv("BROWSER_USER_DATA", "/Users/duanfa/chromeData/Google/Chrome-browseruse-test")
    # chrome_use_data = "/Users/duanfa/chromeData/Google/Chrome-browseruse"

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=chrome_use_data,
            executable_path=chrome_exe,
            headless=False  # Keep browser window visible
        )

        page = browser.new_page()
        page.goto("https://a8demo.seeyoncloud.com/seeyon/meeting.do?method=editor&showTab=true&columnsName=%E6%96%B0%E5%BB%BA%E4%BC%9A%E8%AE%AE")
        page.wait_for_load_state()

        # input("Press the Enter key to close the browser...")
        asyncio.run(apply_meeting_room(browser))
        browser.close()


async def apply_meeting_room(browser):
    page = await browser.get_current_page()
    params = {}
    params.start_time = "2024-06-25 14:30"
    params.end_time = "2025-08-21 15:30"
    params.room_name = "会议室1"
    
    try:
        # 步骤1: 查找并点击"申请会议室"按钮
        apply_button = None
       
        # 点击申请会议室按钮
        element_handle = page.query_selector('//div[@id="roomAppBtn"]');
        if not element_handle:
            raise Exception('Could not locate apply meeting room button element')
        
        iframeSelector = '//div[@id="meetingRoomDialog_main"]/iframe'
        iframe = await page.query_selector(iframeSelector);
        if not iframe:
            await element_handle.click()
            logger.info('Clicked apply meeting room button')
            await asyncio.sleep(2)  # 等待弹窗出现
        
        # 步骤2: 在弹出的会议室选择窗口中选择会议室
        # 查找会议室选择弹窗
    
        # iframeSelector = '//div[@id="meetingRoomDialog_main"]/iframe'
        iframe = await page.query_selector(iframeSelector);
        iframeContent = await iframe.content_frame()
        if not iframeContent:
            raise Exception('Could not find room selection dialog')
        
        dateBlock = await iframeContent.query_selector('//div[@class="dhx_cal_dateContainer"]/div[@class="dhx_cal_date"]')
        if dateBlock:
            date_text = await dateBlock.inner_html()
            # 解析 date_text，格式为：2025年 8月 21日
            match = re.match(r'(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日', date_text)
            if match:
                DefaultYear = int(match.group(1))
                DefaultMonth = int(match.group(2))
                DefaultDay = int(match.group(3))
                logger.info(f'解析到日期: {DefaultYear}年{DefaultMonth}月{DefaultDay}日')
            # 解析 params.start_time 的 年月日，时分
            # 假设 params.start_time 是字符串格式，如 "2025-08-21 14:30"
            start_time = params.start_time
            start_year, start_month, start_day, start_hour, start_minute = None, None, None, None, None
            import re
            match_time = re.match(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})[ T](\d{1,2}):(\d{1,2})', start_time)
            if match_time:
                start_year = int(match_time.group(1))
                start_month = int(match_time.group(2))
                start_day = int(match_time.group(3))
                start_hour = int(match_time.group(4))
                start_minute = int(match_time.group(5))
                logger.info(f'解析到 params.start_time: {start_year}年{start_month}月{start_day}日 {start_hour}:{start_minute}')

                if start_year == DefaultYear and start_month == DefaultMonth and start_day == DefaultDay:
                    # 如果开始时间与默认日期相同，则使用默认日期
                    logger.info(f'使用默认日期: {start_year}年{start_month}月{start_day}日')
                else:
                    # 如果开始时间与默认日期不同，则使用开始时间
                    # start_year = start_year
                    # start_month = start_month
                    # start_day = start_day
                    # logger.info(f'使用开始时间: {start_year}年{start_month}月{start_day}日')
                # else:
                    # /html/body/div[6]/table/thead/tr[1]/td[2]
                    #9月, 2025
                    calendar_span = await iframeContent.query_selector('//span[@class="calendar_icon"]')
                    if calendar_span:
                        await calendar_span.click()
                        await asyncio.sleep(0.5)
                        while True:
                            cal_day_div = await iframeContent.query_selector('//div[contains(@class, "calendar")  and contains(@class, "miniCalendar")]/table/thead/tr/td[@class="title"]')
                            if cal_day_div:
                                cal_day_text = await cal_day_div.get_inner_text()
                                # cal_day_text 的格式：9月, 2025，解析为 cal_month, cal_year
                                # 例如 cal_day_text = "9月, 2025"
                                cal_month, cal_year = None, None
                                if cal_day_text:
                                    match_cal = re.match(r'(\d{1,2})月,\s*(\d{4})', cal_day_text)
                                    if match_cal:
                                        cal_month = int(match_cal.group(1))
                                        cal_year = int(match_cal.group(2))
                                        logger.info(f'解析到日历年月: {cal_year}年{cal_month}月')

                                        if cal_year > start_year:
                                            cal_year_left_button = await iframeContent.query_selector('//div[contains(@class, "calendar")  and contains(@class, "miniCalendar")]/table/thead/tr[@class="headrow"]/td/div[text()="«"]')  
                                            if cal_year_left_button:
                                                await cal_year_left_button.click()
                                                await asyncio.sleep(0.5)
                                                continue		
                                        elif cal_year < start_year:
                                            cal_year_right_button = await iframeContent.query_selector('//div[contains(@class, "calendar")  and contains(@class, "miniCalendar")]/table/thead/tr[@class="headrow"]/td/div[text()="»"]')
                                            if cal_year_right_button:
                                                await cal_year_right_button.click()
                                                await asyncio.sleep(0.5)
                                                continue
                                        
                                        if cal_month > start_month:
                                            cal_month_left_button = await iframeContent.query_selector('//div[contains(@class, "calendar")  and contains(@class, "miniCalendar")]/table/thead/tr[@class="headrow"]/td/div[text()="‹"]')
                                            if cal_month_left_button:
                                                    await cal_month_left_button.click()
                                                    await asyncio.sleep(0.5)
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
                                            await asyncio.sleep(0.5)

                                        break

            else:
                logger.warning(f'无法解析 params.start_time: {start_time}')
            

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
                    logger.info(f'Found search input with selector: {selector}')
                    break
            except:
                continue
        
        if search_input:
            # 清空并输入会议室名称
            await search_input.fill('')
            await search_input.type(params.room_name, delay=100)
            logger.info(f'Input room name: {params.room_name}')
            
            # 按回车键搜索
            search_button = await iframeContent.query_selector('//a[contains(@class, "search_buttonHand") and contains(@class, "search_button")]')
            if search_button:
                await search_button.click()
            await asyncio.sleep(2)  # 等待搜索结果
        
        # 选择第一个搜索结果（会议室）
        room_result_selector = '//div[@class="dhx_matrix_line" and @data-section-index="1"]/div[contains(@class, "dhx_timeline_data_row")]/div'
        timeBlockList = await iframeContent.query_selector_all(room_result_selector)

        room_result = None
        for timeBlock in timeBlockList:
            try:
                print(await timeBlock.get_attribute('data-col-date'))
            except:
                continue
        
        if room_result:
            await room_result.click()
            logger.info(f'Selected meeting room: {params.room_name}')
            await asyncio.sleep(1)
        else:
            logger.warning(f'No room result found for: {params.room_name}')
        
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
                    logger.info(f'Found start time input with selector: {selector}')
                    break
            except:
                continue
        
        if start_time_input:
            await start_time_input.fill('')
            await start_time_input.type(params.start_time, delay=100)
            logger.info(f'Set start time: {params.start_time}')
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
                    logger.info(f'Found end time input with selector: {selector}')
                    break
            except:
                continue
        
        if end_time_input:
            await end_time_input.fill('')
            await end_time_input.type(params.end_time, delay=100)
            logger.info(f'Set end time: {params.end_time}')
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
                    logger.info(f'Found confirm button with selector: {selector}')
                    break
            except:
                continue
        
        if confirm_button:
            await confirm_button.click()
            logger.info('Clicked confirm button')
            await asyncio.sleep(2)  # 等待操作完成
        else:
            logger.warning('Could not find confirm button')
        
        msg = f'✅ 成功申请会议室: {params.room_name}，时间: {params.start_time} - {params.end_time}'
        logger.info(msg)
        return 
    
    except Exception as e:
        error_msg = f'申请会议室失败: {str(e)}'
        logger.error(error_msg)
        return 

# Register ---------------------------------------------------------------



if __name__ == '__main__':
    test_connect_browser()
