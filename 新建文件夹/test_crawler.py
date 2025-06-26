import time
import csv
import os
import getpass
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.chrome.service import Service

# ====== 配置区 ======
config = {
    "base_url": "https://data.showsfinder.com",
    "login_modal_selector": "#passport-login-pop-api",
    "username_input_id": "userName",
    "password_input_id": "passwd",
    "login_button_selector": "input.pass-button.pass-button-submit[value='登录']",
    "exhibition_list_url": "https://data.showsfinder.com",
    "exhibition_item_selector": "//h4[contains(@class, 'default_pointer_cs')]/ancestor::a",
    "exhibition_name_selector": ".//h4",
    "company_card_selector": "//a[contains(@class, 'show_floating_frame')]",
    "company_name_selector": "./@title",
    "contact_dropdown_trigger_selector": "input.layui-input.layui-unselect.default_pointer_cs[placeholder='联系方式']",
    "contact_type_option_selector": "//dd[@lay-value='邮箱']",
    "email_container_selector": "//div[@data-v='邮箱']//ul[@class='concat_c default_cursor_cs']/li",
    "email_selector": ".//div[@class='divs']/p[@class='copy-value']",
    "website_from_contact_selector": ".//p[starts-with(@class, 'text-ellipsis')]/a[@title='企业官网']",
    "website_onclick_attribute_selector": ".//div[@class='top_detail_other_rows']//a[contains(@class, 'c_mainblue')]/@onclick",
}

# ====== 主流程 ======
def login(driver, wait, USER_NAME, PASS_WORD):
    driver.get(config["base_url"])
    time.sleep(1)
    # 触发登录弹窗
    try:
        driver.find_element(By.CSS_SELECTOR, "a.login").click()
    except Exception:
        pass  # 有时已弹出
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, config["login_modal_selector"])))
    driver.find_element(By.ID, config["username_input_id"]).send_keys(USER_NAME)
    driver.find_element(By.ID, config["password_input_id"]).send_keys(PASS_WORD)
    driver.find_element(By.CSS_SELECTOR, config["login_button_selector"]).click()
    # 等待登录成功
    wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, config["login_modal_selector"])))
    time.sleep(1)

def get_exhibition_links(driver, wait, max_count=3):
    links = []
    page = 1
    while len(links) < max_count:
        wait.until(EC.presence_of_all_elements_located((By.XPATH, "//ul[@id='list']/li")))
        items = driver.find_elements(By.XPATH, "//ul[@id='list']/li")
        for item in items:
            a = item.find_element(By.XPATH, ".//div[contains(@class, 'media-heading')]/a")
            link = a.get_attribute("href")
            if link.startswith("/"):
                link = config["base_url"] + link
            name = a.find_element(By.XPATH, "./h4").text.strip()
            links.append((link, name))
            if len(links) >= max_count:
                break
        # 分页
        if len(links) < max_count:
            try:
                next_btn = driver.find_element(By.XPATH, "//a[contains(@class, 'pg-next')]")
                if not next_btn.is_displayed() or "disabled" in next_btn.get_attribute("class"):
                    break
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(2)
            except Exception:
                break
    return links

def select_country_china(driver, wait):
    # 展会详情页加载后，点击"国家"下的"中国"
    try:
        country_menu = wait.until(EC.presence_of_element_located((By.ID, "country_menu")))
        china_li = country_menu.find_element(By.XPATH, ".//li[@data-value='中国']/a")
        driver.execute_script("arguments[0].click();", china_li)
        time.sleep(1.5)
    except Exception as e:
        print("筛选中国失败，跳过本展会", e)

def get_company_elements(driver, wait):
    wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[@id='list']//li[contains(@class, 'promptaisho')]")))
    return driver.find_elements(By.XPATH, "//div[@id='list']//li[contains(@class, 'promptaisho')]")

def close_company_card(driver, wait):
    closed = False
    try:
        mask = driver.find_element(By.XPATH, "//div[contains(@class, 'layui-layer-shade')]")
        driver.execute_script("arguments[0].click();", mask)
        closed = True
    except Exception:
        pass
    if not closed:
        try:
            close_btn = driver.find_element(By.XPATH, "//span[contains(@class, 'layui-layer-setwin')]//a")
            close_btn.click()
            closed = True
        except Exception:
            pass
    if not closed:
        driver.refresh()
        time.sleep(1.5)
    wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[@id='list']//li[contains(@class, 'promptaisho')]")))

def open_company_card_and_collect_basic(driver, wait, company_li):
    card_link = company_li.find_element(By.XPATH, ".//a[contains(@class, 'show_floating_frame')]")
    company_name_main = company_li.find_element(By.XPATH, ".//div[contains(@class, 'divboxs')]/a").get_attribute("title")
    print(f"点击公司卡片: {company_name_main}")
    for attempt in range(3):
        try:
            print(f"  [尝试{attempt+1}] 等待iframe弹窗...")
            driver.execute_script("arguments[0].click();", card_link)
            wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, "//iframe[contains(@name, 'layui-layer-iframe')]")))
            print("  已进入iframe，采集基础字段...")
            # 采集iframe内公司名
            try:
                company_name = driver.find_element(By.XPATH, "//div[contains(@class, 'company-top-name')] | //div[contains(@class, 'divboxs')]/a").get_attribute("title")
            except Exception:
                company_name = ""
            # 采集iframe内成立日期
            try:
                establish_date = driver.find_element(By.XPATH, "//div[contains(@class, 'top_detail_other_rows')][p[contains(text(), '成立日期')]]/span").text.strip()
            except Exception:
                try:
                    establish_date = driver.find_element(By.XPATH, "//div[contains(@class, 'top_detail_other_rows')]/p[contains(text(), '成立日期')]/following-sibling::span[1]").text.strip()
                except Exception:
                    establish_date = ""
            driver.switch_to.default_content()
            print("  关闭弹窗...")
            close_company_card(driver, wait)
            return company_name, establish_date
        except Exception as e:
            print(f"  [异常] {e}")
            driver.switch_to.default_content()
            time.sleep(0.5)
    print("  采集失败，关闭弹窗...")
    close_company_card(driver, wait)
    return "", ""

def goto_exhibition_list(driver, wait):
    # 登录后直接跳转展会列表页，最稳妥
    driver.get("https://data.showsfinder.com/exhibition")
    wait.until(EC.presence_of_all_elements_located((By.XPATH, "//ul[@id='list']/li")))

def collect_company_basic_info(left_li, right_li):
    # 公司名
    try:
        company_name = left_li.find_element(By.XPATH, ".//div[contains(@class, 'divboxs')]/a").get_attribute("title")
    except Exception:
        company_name = ""
    # 成立日期
    establish_date = ""
    # 输出整个li源码，人工查找成立日期div
    print(f"调试 right_li HTML: {right_li.get_attribute('outerHTML')}")
    divs = right_li.find_elements(By.XPATH, ".//div[contains(@class, 'col-md-1')]")
    for div in divs:
        text = div.text.strip()
        print(f"调试 div内容: {text}")
        if re.match(r"\d{4}-\d{2}-\d{2}", text):
            establish_date = text
            break
    return {
        "公司名": company_name,
        "成立日期": establish_date
    }

def main():
    print("请输入您的账号：")
    USER_NAME = input("用户名: ").strip()
    PASS_WORD = getpass.getpass("密码: ").strip()
    if not USER_NAME or not PASS_WORD:
        print("用户名和密码不能为空！")
        exit(1)
    script_dir = os.path.abspath(os.path.dirname(__file__))
    chromedriver_path = os.path.join(script_dir, 'chromedriver.exe')
    if not os.path.isfile(chromedriver_path):
        print(f"未找到chromedriver.exe，请将其放在：{chromedriver_path}")
        exit(1)
    options = webdriver.ChromeOptions()
    service = Service(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 15)
    login(driver, wait, USER_NAME, PASS_WORD)
    goto_exhibition_list(driver, wait)
    exhibitions = get_exhibition_links(driver, wait, max_count=3)
    for ex_link, ex_name in exhibitions:
        driver.get(ex_link)
        # select_country_china(driver, wait)
        # 获取左侧公司卡片li和右侧info区li
        left_lis = driver.find_elements(By.XPATH, "//div[@class='company-list-left']//ul/li[position()>1]")
        right_lis = driver.find_elements(By.XPATH, "//div[@class='company-list-info']//ul/li[position()>1]")
        min_len = min(len(left_lis), len(right_lis))
        for idx in range(min_len):
            left_li = left_lis[idx]
            right_li = right_lis[idx]
            try:
                company_name = left_li.find_element(By.XPATH, ".//div[contains(@class, 'divboxs')]/a").get_attribute("title")
            except Exception:
                company_name = ""
            establish_date = ""
            divs = right_li.find_elements(By.XPATH, ".//div[contains(@class, 'col-md-1')]")
            for div in divs:
                text = div.text.strip()
                print(f"调试[{idx}] div内容: {text}")
                if re.match(r"\d{4}-\d{2}-\d{2}", text):
                    establish_date = text
                    break
            print(f"[{idx}] 公司名: {company_name}, 成立日期: {establish_date}")
        # 返回展会列表页
    # 下一页

if __name__ == "__main__":
    main() 