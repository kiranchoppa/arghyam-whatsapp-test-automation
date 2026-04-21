"""WebDriver creation helpers."""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType


def create_driver(browser, edge_profile_dir, edge_profile_name, keep_browser_open=False):
    if browser == "edge":
        options = EdgeOptions()
        options.add_argument("--start-maximized")
        options.add_argument(f"--user-data-dir={edge_profile_dir}")
        options.add_argument(f"--profile-directory={edge_profile_name}")
        options.add_experimental_option("detach", keep_browser_open)
        return webdriver.Edge(options=options)

    options = ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--user-data-dir=.whatsapp_chrome_profile")
    options.add_experimental_option("detach", keep_browser_open)
    options.binary_location = "/snap/bin/chromium"
    service = ChromeService(
        ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
    )
    return webdriver.Chrome(service=service, options=options)

