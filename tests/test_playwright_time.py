import re
from dotenv import load_dotenv
import os
from playwright.async_api import async_playwright
import sys
from pydantic import BaseModel, Field

# 修改路径指向src目录下的browser_use包
browser_use_path = os.path.join(os.path.dirname(__file__), '..', 'src')
if browser_use_path not in sys.path:
	sys.path.insert(0, browser_use_path)

load_dotenv()
import logging
logger = logging.getLogger(__name__)
# from browser_use.browser.context import BrowserContext
from browser_use.dom.views import DOMElementNode
from browser_use.browser.views import (
	BrowserError,
	BrowserState,
	TabInfo,
	URLNotAllowedError,
)

import asyncio

class ActionResult(BaseModel):
	"""Result of executing an action"""

	is_done: bool | None = False
	success: bool | None = None
	extracted_content: str | None = None
	error: str | None = None
	include_in_memory: bool = False  # whether to include in past messages as context or not

class InputTimeAction(BaseModel):
	index: int
	start_time_value: str = Field(..., description='时间值，格式可以是:"YYYY-MM-DD HH:MM", "YYYY-MM-DD HH:MM:SS" 等')
	end_time_value: str = Field(..., description='时间值，格式可以是:"YYYY-MM-DD HH:MM", "YYYY-MM-DD HH:MM:SS" 等')
	time_format: str | None = Field(None, description='可选的时间格式，如果不提供则自动检测')
	xpath: str | None = None



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
			logger.info("尝试使用CDP检测所有标签页...")
			cdp_session = await page.context.new_cdp_session(page)
			
			# 获取所有目标（包括所有标签页）
			targets = await cdp_session.send('Target.getTargets')
			logger.info(f"CDP检测到 {len(targets['targetInfos'])} 个目标")
			
			for target in targets['targetInfos']:
				if target['type'] == 'page':
					logger.info(f"CDP页面: ID={target['targetId']}, 标题={target['title']}, URL={target['url']}")
					
					# 尝试附加到新页面
					if '协同管理' in target.get('title', '') or 'meeting' in target.get('url', '').lower():
						logger.info(f"发现可能的会议页面: {target['title']}")
						try:
							new_page = await page.context.new_page()
							await new_page.goto(target['url'])
							logger.info(f"成功导航到新页面: {target['url']}")
							# 更新当前页面引用
							page = new_page
							break
						except Exception as e:
							logger.warning(f"无法导航到新页面: {str(e)}")
							
		except Exception as e:
			logger.warning(f"CDP检测失败: {str(e)}")
		
		# 尝试多种选择器来找到"新建会议"按钮
	   
		params = InputTimeAction(index=0, start_time_value="2023-04-10 11:01", end_time_value="2027-09-29 11:59", time_format=None)
		# 暂时注释掉这个调用，因为它需要browser对象有特定的方法
		await input_time(params, page)
		print("浏览器启动成功，测试导入完成！")
		await browser.close()




async def input_time(params: InputTimeAction, page):
			
		# 直接查找元素，不等待可见性
		meeting_div = await page.query_selector('//div[@title="新建会议"]')
		
		if not meeting_div:
			logger.warning("未找到'新建会议'元素，尝试其他选择器...")
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
						logger.info(f"使用选择器找到元素: {selector}")
						break
				except Exception as e:
					logger.debug(f"选择器 {selector} 失败: {str(e)}")
					continue
		
		if not meeting_div:
			raise Exception("无法找到'新建会议'元素")
		
		logger.info("成功找到'新建会议'元素")
		
		# 尝试多种点击方法，考虑到元素可能有特殊的交互要求
		
		try:
			# 方法3：JavaScript点击
			logger.debug("尝试JavaScript点击...")
			await page.evaluate("(element) => element.click()", meeting_div)
			logger.info("JavaScript点击成功")
		except Exception as e3:
			logger.debug(f"JavaScript点击失败: {str(e3)}")
			
		logger.info("等待页面响应...")
		await asyncio.sleep(2)

		# 跳转到新打开的页面（假设点击后会新开一个tab）
		pages = page.context.pages
		if len(pages) > 1:
			page = pages[-1]
			logger.info("已切换到新打开的页面 url："+page.url)
		else:
			logger.info("未检测到新页面，继续使用当前页面")
			

		# 等待页面响应
		
		# 尝试查找时间输入框   main hasIframe
		try:
			iframe = await page.query_selector("//div[@id='main']/iframe");
			page = await iframe.content_frame()
			logger.info("成功获取iframe内容")
		except Exception as e:
			logger.debug(f"无法获取iframe内容: {str(e)}")
			page = page
			if not page:
				raise Exception("无法获取iframe内容")
		
		# logger.info("查找时间输入框...")
		# time_input = await page.wait_for_selector('//input[@id="meetingTime"]', timeout=500)
		time_input = await page.wait_for_selector('//div[contains(@class, "CtpUiDateRange")]', timeout=500)
		await time_input.click()
		calStartYear = await page.wait_for_selector('//div[@id="doubleDate"]//span[@class="calendar_month_label_year"]', timeout=1000)
		calStartMonth = await page.wait_for_selector('//div[@id="doubleDate"]//span[@class="calendar_month_label_month"]', timeout=1000)
		print(await calStartYear.text_content())
		print(await calStartMonth.text_content())

		match_time = re.match(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})[ T](\d{1,2}):(\d{1,2})', params.start_time_value)
		
		start_year = int(match_time.group(1))
		start_month = int(match_time.group(2))
		start_day = int(match_time.group(3))
		start_hour = int(match_time.group(4))
		start_minute = int(match_time.group(5))
		print("start_time:"+str(start_year)+str(start_month)+str(start_day)+str(start_hour)+str(start_minute))
	
		match_time = re.match(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})[ T](\d{1,2}):(\d{1,2})', params.end_time_value)
	
		end_year = int(match_time.group(1))
		end_month = int(match_time.group(2))
		end_day = int(match_time.group(3))
		end_hour = int(match_time.group(4))
		end_minute = int(match_time.group(5))
		print("end_time:"+str(end_year)+str(end_month)+str(end_day)+str(end_hour)+str(end_minute))

		while True:
			leftYearAll = await page.query_selector_all('//div[@id="doubleDate"]//span[@class="calendar_year_arrow syIcon sy-double-arrow-left"]')
			rightYearAll = await page.query_selector_all('//div[@id="doubleDate"]//span[@class="calendar_year_arrow syIcon sy-double-arrow-right"]')

			leftMonthAll = await page.query_selector_all('//div[@id="doubleDate"]//span[@class="calendar_month_arrow syIcon sy-arrow-left"]')
			rightMonthAll = await page.query_selector_all('//div[@id="doubleDate"]//span[@class="calendar_month_arrow syIcon sy-arrow-right"]')

			calYearAll = await page.query_selector_all('//div[@id="doubleDate"]//span[@class="calendar_month_label_year"]')
			calMonthAll = await page.query_selector_all('//div[@id="doubleDate"]//span[@class="calendar_month_label_month"]')
			
			calHoursAll = await page.query_selector_all('//div[@id="doubleDate"]//span[@class="calendar_label_hours"]')
			calMinutesAll = await page.query_selector_all('//div[@id="doubleDate"]//span[@class="calendar_label_minutes"]')



	
			start_cal_year = int(await calYearAll[0].text_content())
		
			end_cal_year = int(await calYearAll[1].text_content())
	
			start_cal_month = int((await calMonthAll[0].text_content()).replace("月", ""))
		
			end_cal_month = int((await calMonthAll[1].text_content()).replace("月", ""))

			start_cal_hours = int(await calHoursAll[0].text_content())
			start_cal_minutes = int(await calMinutesAll[0].text_content())  

			end_cal_hours = int(await calHoursAll[1].text_content())
			end_cal_minutes = int(await calMinutesAll[1].text_content())	

			logger.info(f'解析到日历年月: {start_cal_year}年{start_cal_month}月')

			if int(start_cal_year) > start_year:
				start_year_left_button = leftYearAll[0]
				if start_year_left_button:
					await start_year_left_button.click()
					await asyncio.sleep(0.5)
					continue		
			elif start_cal_year < start_year:
				start_year_right_button = rightYearAll[0]
				if start_year_right_button:
					await start_year_right_button.click()
					await asyncio.sleep(0.5)
					continue

			if end_cal_year > end_year:
				end_year_left_button = leftYearAll[1]
				if end_year_left_button:
					await end_year_left_button.click()
					await asyncio.sleep(0.5)
					continue		
			elif end_cal_year < end_year:
				end_year_right_button = rightYearAll[1]
				if end_year_right_button:
					await end_year_right_button.click()
					await asyncio.sleep(0.5)
					continue
			
			if start_cal_month > start_month:
				start_month_left_button = leftMonthAll[0]
				if start_month_left_button:
						await start_month_left_button.click()
						await asyncio.sleep(0.5)
						continue
			elif start_cal_month < start_month:
				start_month_right_button = rightMonthAll[0]
				if start_month_right_button:
					await start_month_right_button.click()
					await asyncio.sleep(0.5)
					continue

			if end_cal_month > end_month:
				end_month_left_button = leftMonthAll[1]
				if end_month_left_button:
						await end_month_left_button.click()
						await asyncio.sleep(0.5)
						continue
			elif end_cal_month < end_month:
				end_month_right_button = rightMonthAll[1]
				if end_month_right_button:
					await end_month_right_button.click()
					await asyncio.sleep(0.5)
					continue
			
			
			chose_DayAll = await page.query_selector_all('//div[@id="doubleDate"]//li[contains(@class, "dhtmlxcalendar_cell_month")]/div[contains(@class,"dhtmlxcalendar_label") and text()="'+str(start_day)+'"]')
			if len(chose_DayAll) > 0:
				chose_Day = chose_DayAll[0]
				logger.debug(f"找到开始日期元素: {start_day}")
				# ElementHandle没有xpath属性，获取其他信息
				try:
					parent_path = await chose_Day.evaluate("""
						function(el) {
							let path = [];
							let current = el;
							while (current) {
								let id = current.id ? '@id="' + current.id + '"' : '';
								let className = current.className ? '@class="' + current.className + '"' : '';
								let extra = [id, className].filter(Boolean).join('-');
								if (extra) {
									path.unshift(current.tagName.toLowerCase() + '[' + extra + ']');
								} else {
									path.unshift(current.tagName.toLowerCase());
								}
								current = current.parentElement;
							}
							return path.join('/');
						}
					""")
					logger.debug(f"开始日期元素: 父级路径={parent_path}")
				except Exception as e:
					logger.debug(f"无法获取开始日期元素详细信息: {str(e)}")
				# 尝试多种点击方法
				try:
					# 方法1：直接点击
					await chose_Day.click(timeout=500)
					logger.debug("开始日期直接点击成功")
				except Exception as e:
					logger.debug(f"开始日期直接点击失败: {str(e)}")
				await asyncio.sleep(0.5)
				
			chose_DayAll = await page.query_selector_all('//div[@id="doubleDate"]//li[contains(@class, "dhtmlxcalendar_cell_month")]/div[contains(@class,"dhtmlxcalendar_label") and text()="'+str(end_day)+'"]')
			if len(chose_DayAll) > 0:
				chose_Day = chose_DayAll[0]
				if len(chose_DayAll) > 1:
					chose_Day = chose_DayAll[1]
				logger.debug(f"找到开始日期元素: {start_day}")
				# ElementHandle没有xpath属性，获取其他信息
				try:
					parent_path = await chose_Day.evaluate("""
						function(el) {
							let path = [];
							let current = el;
							while (current) {
								let id = current.id ? '@id="' + current.id + '"' : '';
								let className = current.className ? '@class="' + current.className + '"' : '';
								let extra = [id, className].filter(Boolean).join('-');
								if (extra) {
									path.unshift(current.tagName.toLowerCase() + '[' + extra + ']');
								} else {
									path.unshift(current.tagName.toLowerCase());
								}
								current = current.parentElement;
							}
							return path.join('/');
						}
					""")
					logger.debug(f"结束日期元素: 父级路径={parent_path}")
				except Exception as e:
					logger.debug(f"无法获取结束日期元素详细信息: {str(e)}")
				logger.debug(f"找到结束日期元素: {end_day}")
				# ElementHandle没有xpath属性，获取其他信息
				try:
					tag_name = await chose_Day.evaluate("el => el.tagName")
					class_name = await chose_Day.get_attribute("class")
					text_content = await chose_Day.text_content()
					logger.debug(f"开始日期元素: 标签={tag_name}, 类={class_name}, 文本={text_content}")
				except Exception as e:
					logger.debug(f"无法获取开始日期元素详细信息: {str(e)}")
				# 尝试多种点击方法
				try:
					# 方法1：直接点击
					await chose_Day.click(timeout=500)
					logger.debug("结束日期直接点击成功")
				except Exception as e:
					logger.debug(f"结束日期直接点击失败: {str(e)}")
				await asyncio.sleep(0.5)


			select_hour_all = await page.query_selector_all('//div[@id="doubleDate"]//ul[@class="calendar_line common_txtbox_wrap comp_select_ctl"]')
			if start_cal_hours == start_hour and start_cal_minutes == start_minute:
				print("开始时间选择完成")
			else:
				# page = await iframe.content_frame()
				if select_hour_all:
					await select_hour_all[0].click()
					await asyncio.sleep(0.5)
					hour_str = ""
					if start_hour < 10:
						hour_str = "0"+str(start_hour)
					else:
						hour_str = str(start_hour)
					hour_select = await page.query_selector_all('//div[@class="ivu-picker-panel-content"]//li[ contains(@class,"ivu-time-picker-cells-cell") and @type="hour" and text()="'+hour_str+'"]')
					await hour_select[0].click()
					await asyncio.sleep(0.5)
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
					minute_select = await page.query_selector_all('//div[@class="ivu-picker-panel-content"]//li[ contains(@class,"ivu-time-picker-cells-cell") and @type="min" and text()="'+minute_str+'"]')
					await minute_select[0].click()
					await asyncio.sleep(0.5)
					await select_hour_all[0].click()
					await asyncio.sleep(0.5)

			if end_cal_hours == end_hour and end_cal_minutes == end_minute:
				print("结束时间选择完成")
			else:
				if select_hour_all:
					await select_hour_all[1].click()
					await asyncio.sleep(0.5)
					hour_str = ""
					if end_hour < 10:
						hour_str = "0"+str(end_hour)
					else:
						hour_str = str(end_hour)
					hour_select = await page.query_selector_all('//div[@class="ivu-picker-panel-content"]//li[ contains(@class,"ivu-time-picker-cells-cell") and @type="hour" and text()="'+hour_str+'"]')
					await hour_select[1].click()
					await asyncio.sleep(0.5)
					minute_str = ""
					minute_value = 0
					while True:
						if minute_value < end_minute:
							minute_value += 5
						if minute_value > 55   :
							minute_value = 55
							break
						if minute_value > end_minute:
							break
						if minute_value == end_minute:
							break
					if minute_value == 0:
						minute_str = "00"
					elif minute_value == 5:
						minute_str = "05"
					else:
						minute_str = str(minute_value)

			   
					minute_select = await page.query_selector_all('//div[@class="ivu-picker-panel-content"]//li[ contains(@class,"ivu-time-picker-cells-cell") and @type="min" and text()="'+minute_str+'"]')
					await minute_select[1].click()
					await asyncio.sleep(0.5)
					await select_hour_all[1].click()
					await asyncio.sleep(0.5)
					
			
			break

		ok_button = await page.wait_for_selector('//div[@class="ivu-picker-confirm"]//a[text()="确定"]')
		if ok_button:
			await ok_button.click()
		await asyncio.sleep(0.5)

	
		


		msg = f'⏰  Input time value {params.start_time_value} and {params.end_time_value} into index {params.index}'
		logger.info(msg)
		return ActionResult(extracted_content=msg, include_in_memory=True)


if __name__ == '__main__':
	asyncio.run(test_connect_browser())
