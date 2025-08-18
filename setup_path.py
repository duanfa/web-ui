import sys
import os

# 添加browser-use项目路径到Python路径
browser_use_path = os.path.join(os.path.dirname(__file__), '..', 'browser-use')
if browser_use_path not in sys.path:
    sys.path.insert(0, browser_use_path)
    print(f"Added {browser_use_path} to Python path")

# 验证导入
try:
    from browser_use.browser.browser import Browser
    print("Successfully imported Browser from local browser-use project")
except ImportError as e:
    print(f"Failed to import Browser: {e}")
