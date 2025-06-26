import time
import csv
import json
import os
import getpass
import pickle
import re
import pandas as pd
# ===== 新增导入 =====
try:
    import undetected_chromedriver as uc
except ImportError:
    uc = None
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
# from selenium.webdriver.chrome.service import Service  # 不再需要

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

USER_NAME = "你的用户名"
PASS_WORD = "你的密码"
PROGRESS_FILE = "progress.json"
LOG_FILE = "crawler.log"
PAGE_LOAD_TIMEOUT = 20
ELEMENT_WAIT_TIMEOUT = 10
ACTION_DELAY = 1.5
EXHIBITION_DELAY = 3
LOGIN_RETRY_COUNT = 3
HEADLESS_MODE = False
COOKIE_FILE = "cookies.pkl"

# ====== 日志工具 ======
def log(msg):
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")

# ====== 断点续爬 ======
def save_progress(progress):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cookies(driver, path):
    with open(path, 'wb') as filehandler:
        pickle.dump(driver.get_cookies(), filehandler)

def load_cookies(driver, path):
    with open(path, 'rb') as cookiesfile:
        cookies = pickle.load(cookiesfile)
        for cookie in cookies:
            driver.add_cookie(cookie)

# ====== 登录流程 ======
def login(driver, wait):
    driver.get(config["base_url"])
    time.sleep(1)
    for _ in range(LOGIN_RETRY_COUNT):
        try:
            try:
                driver.find_element(By.CSS_SELECTOR, "a.login").click()
            except Exception:
                pass
            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, config["login_modal_selector"])))
            driver.find_element(By.ID, config["username_input_id"]).send_keys(USER_NAME)
            driver.find_element(By.ID, config["password_input_id"]).send_keys(PASS_WORD)
            driver.find_element(By.CSS_SELECTOR, config["login_button_selector"]).click()
            wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, config["login_modal_selector"])))
            time.sleep(1)
            log("登录成功")
            save_cookies(driver, COOKIE_FILE)
            return
        except Exception as e:
            log(f"登录失败重试: {e}")
            time.sleep(3)
    raise Exception("登录失败，已达最大重试次数")

# ====== 展会列表分页遍历 ======
def get_exhibition_links(driver, wait):
    links = []
    page = 1
    while True:
        wait.until(EC.presence_of_all_elements_located((By.XPATH, "//ul[@id='list']/li")))
        items = driver.find_elements(By.XPATH, "//ul[@id='list']/li")
        for item in items:
            a = item.find_element(By.XPATH, ".//div[contains(@class, 'media-heading')]/a")
            link = a.get_attribute("href")
            if link.startswith("/"):
                link = config["base_url"] + link
            name = a.find_element(By.XPATH, "./h4").text.strip()
            links.append((link, name))
        # 分页
        try:
            next_btn = driver.find_element(By.XPATH, "//a[contains(@class, 'pg-next')]")
            if not next_btn.is_displayed() or "disabled" in next_btn.get_attribute("class"):
                break
            driver.execute_script("arguments[0].click();", next_btn)
            time.sleep(2)
            page += 1
        except Exception:
            break
    return links

# ====== 进入展会后筛选国家为中国 ======
def select_country_china(driver, wait):
    try:
        country_menu = wait.until(EC.presence_of_element_located((By.ID, "country_menu")))
        china_li = country_menu.find_element(By.XPATH, ".//li[@data-value='中国']/a")
        driver.execute_script("arguments[0].click();", china_li)
        time.sleep(1.5)
    except Exception as e:
        print("筛选中国失败，跳过本展会", e)

# ====== 进入展会后筛选行业为汽摩配件 ======
def select_industry_qmpj(driver, wait):
    try:
        # 等待行业栏加载
        industry_menu = wait.until(EC.presence_of_element_located((By.ID, "industry")))
        qmpj_li = industry_menu.find_element(By.XPATH, ".//li[@data-value='汽摩配件']")
        driver.execute_script("arguments[0].click();", qmpj_li)
        time.sleep(1.5)
        log("已选择行业：汽摩配件")
    except Exception as e:
        log(f"选择行业汽摩配件失败: {e}")

# ====== 公司列表分页遍历 ======
def get_company_elements(driver, wait):
    wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[@id='list']//li[contains(@class, 'promptaisho')]")))
    return driver.find_elements(By.XPATH, "//div[@id='list']//li[contains(@class, 'promptaisho')]")

def get_company_name(company_elem):
    try:
        return company_elem.find_element(By.XPATH, ".//div[contains(@class, 'divboxs')]/a").get_attribute("title")
    except Exception:
        return ""

# ====== 处理公司卡片（iframe弹窗） ======
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

def process_company_card(driver, wait, company_elem):
    # 只点击公司名区域的show_floating_frame
    try:
        a = company_elem.find_element(By.XPATH, ".//a[contains(@class, 'show_floating_frame') and @title]")
    except Exception:
        # 兜底：点击第一个show_floating_frame
        a = company_elem.find_element(By.XPATH, ".//a[contains(@class, 'show_floating_frame')]")
    driver.execute_script("arguments[0].click();", a)
    # 1. 等待iframe弹出，并调试输出所有iframe属性
    # ====== 调试：切换iframe前先回到主页面 ======
    driver.switch_to.default_content()
    iframe = None
    for _ in range(10):
        iframes = driver.find_elements(By.XPATH, "//iframe[starts-with(@id, 'layui-layer-iframe') or starts-with(@name, 'layui-layer-iframe')]")
        log(f"调试: 当前页面iframe数量: {len(iframes)}")
        for idx, f in enumerate(iframes):
            try:
                name = f.get_attribute('name')
                src = f.get_attribute('src')
                id_ = f.get_attribute('id')
                display = f.value_of_css_property('display')
                zidx = f.value_of_css_property('z-index')
                log(f"调试: iframe[{idx}] id={id_}, name={name}, src={src}, display={display}, z-index={zidx}")
            except Exception as e:
                log(f"调试: 获取iframe属性异常: {e}")
        if iframes:
            iframe = iframes[-1]  # 取最后一个
            try:
                driver.switch_to.frame(iframe)
                log(f"调试: 已切换到iframe: src={iframe.get_attribute('src')}, id={iframe.get_attribute('id')}, name={iframe.get_attribute('name')}")
                # 打印iframe源码前1000字符
                log(f"调试: iframe源码前1000字符: {driver.page_source[:1000]}")
                break
            except Exception as e:
                log(f"调试: 切换iframe异常: {e}")
        time.sleep(0.5)
    # 2. 等待body和邮箱tab内容出现
    for _ in range(10):
        try:
            if driver.find_elements(By.TAG_NAME, "body"):
                # 再等邮箱tab
                if driver.find_elements(By.XPATH, "//dd[@lay-value='邮箱']"):
                    break
        except Exception:
            pass
        time.sleep(0.5)
    try:
        # 1. 等待联系方式输入框出现
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='联系方式']")))
        driver.find_element(By.CSS_SELECTOR, "input[placeholder='联系方式']").click()
        time.sleep(0.5)
        # 2. 选择邮箱tab
        wait.until(EC.element_to_be_clickable((By.XPATH, "//dd[@lay-value='邮箱']"))).click()
        time.sleep(1.2)
        # ====== 调试：打印ul.concat_c下li元素 ======
        email_lis = driver.find_elements(By.XPATH, "//ul[contains(@class, 'concat_c')]/li")
        log(f"调试: ul.concat_c下li元素数量: {len(email_lis)}")
        for idx, li in enumerate(email_lis):
            try:
                log(f"调试: li[{idx}] outerHTML: {li.get_attribute('outerHTML')}")
            except Exception as e:
                log(f"调试: 获取li[{idx}] outerHTML异常: {e}")
        # ====== 原有邮箱采集逻辑 ======
        emails = []
        for item in email_lis:
            try:
                email = item.find_element(By.XPATH, ".//p[contains(@class, 'copy-value')]").text.strip()
                if email:
                    emails.append(email)
            except Exception as e:
                log(f"采集单个邮箱异常: {e}")
                continue
        # ===== 新增：正则补充采集 =====
        if not emails:
            page_source = driver.page_source
            regex_email = r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}'
            emails = list(set(re.findall(regex_email, page_source)))
            log(f"正则补充采集到邮箱数量: {len(emails)}，内容: {emails}")
        # ===== 新增：可见文本正则采集 =====
        if not emails:
            try:
                visible_text = driver.find_element(By.TAG_NAME, "body").text
                emails = list(set(re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}', visible_text)))
                log(f"卡片可见文本正则采集到邮箱数量: {len(emails)}，内容: {emails}")
            except Exception as e:
                log(f"卡片可见文本采集邮箱异常: {e}")
                emails = []
        log(f"调试: 采集到邮箱数量: {len(emails)}，内容: {emails}")
        if not emails:
            log("邮箱tab无数据，当前iframe HTML片段：" + driver.page_source[:1000])
        # 4. 官网
        website = ""
        try:
            # 先用原有方式
            website_btn = driver.find_element(By.XPATH, ".//div[@class='top_detail_other_rows']//a[contains(@class, 'c_mainblue')]")
            onclick = website_btn.get_attribute("onclick")
            if onclick and "windowopen('" in onclick:
                website = onclick.split("windowopen('")[1].split("'")[0]
        except Exception as e:
            website = ""
        # ===== 新增：正则补充采集官网 =====
        if not website:
            page_source = driver.page_source
            regex_url = r'https?://[A-Za-z0-9\\-\\.]+\\.[A-Za-z]{2,}(/[\\w\\-\\./?%&=]*)?'
            urls = re.findall(regex_url, page_source)
            onclick_urls = re.findall(r"windowopen\\('([^']+)'\\)", page_source)
            all_urls = set(urls) | set(onclick_urls)
            if all_urls:
                website = list(all_urls)[0]
            log(f"正则补充采集到官网: {website}")
        # ===== 新增：可见文本正则采集官网 =====
        if not website:
            try:
                visible_text = driver.find_element(By.TAG_NAME, "body").text
                url_matches = re.findall(r'https?://[A-Za-z0-9\\-\\.]+\\.[A-Za-z]{2,}(/[\\w\\-\\./?%&=]*)?', visible_text)
                if url_matches:
                    website = url_matches[0] if isinstance(url_matches[0], str) else url_matches[0][0]
                log(f"卡片可见文本正则采集到官网: {website}")
            except Exception as e:
                log(f"卡片可见文本采集官网异常: {e}")
        driver.switch_to.default_content()
        close_company_card(driver, wait)
        return emails, website
    except Exception as e:
        log(f"采集公司卡片异常: {e}")
        driver.switch_to.default_content()
        time.sleep(0.5)
        close_company_card(driver, wait)
        return [], ""

# ====== 主流程 ======
def main():
    global USER_NAME, PASS_WORD
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
    # ====== 使用undetected-chromedriver启动浏览器 ======
    if uc is None:
        print("未安装undetected-chromedriver，请先安装：pip install undetected-chromedriver")
        exit(1)
    options = uc.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    if HEADLESS_MODE:
        options.add_argument('--headless')
    driver = uc.Chrome(options=options, driver_executable_path=chromedriver_path)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    wait = WebDriverWait(driver, ELEMENT_WAIT_TIMEOUT)
    progress = load_progress()
    all_data = []
    try:
        # ====== 优先加载cookie自动登录 ======
        if os.path.exists(COOKIE_FILE):
            driver.get(config["base_url"])
            time.sleep(2)
            load_cookies(driver, COOKIE_FILE)
            driver.refresh()
            time.sleep(2)
            log("已加载cookie，尝试自动登录")
        else:
            login(driver, wait)
        # 检查是否已登录，否则重新登录
        try:
            driver.find_element(By.CSS_SELECTOR, "a.login")
            log("cookie登录未生效，重新手动登录")
            login(driver, wait)
        except NoSuchElementException:
            log("cookie登录成功")
        exhibition_page = progress.get("exhibition_page", 1)
        while True:  # 展会列表页循环
            # 跳转到正确的展会列表页
            if exhibition_page > 1:
                driver.get(f"https://data.showsfinder.com/exhibition?page={exhibition_page}")
            else:
                driver.get("https://data.showsfinder.com/exhibition")
            time.sleep(2)
            select_industry_qmpj(driver, wait)
            wait.until(EC.presence_of_all_elements_located((By.XPATH, "//ul[@id='list']/li")))
            exhibition_items = driver.find_elements(By.XPATH, "//ul[@id='list']/li")
            start_ex_idx = progress.get("exhibition_idx", 0)
            for ex_idx, item in enumerate(exhibition_items[start_ex_idx:], start=start_ex_idx):
                try:
                    a = item.find_element(By.XPATH, ".//div[contains(@class, 'media-heading')]/a")
                    ex_link = a.get_attribute("href")
                    if ex_link.startswith("/"):
                        ex_link = config["base_url"] + ex_link
                    ex_name = a.find_element(By.XPATH, "./h4").text.strip()
                    log(f"开始展会: {ex_name}")
                    driver.get(ex_link)
                    time.sleep(2)
                    select_country_china(driver, wait)
                    # 公司分页采集
                    company_page = progress.get("company_page", 1) if ex_idx == start_ex_idx else 1
                    current_company_page = company_page
                    while True:
                        companies = get_company_elements(driver, wait)
                        start_co_idx = progress.get("company_idx", 0) if ex_idx == start_ex_idx and current_company_page == company_page else 0
                        co_idx = start_co_idx
                        while co_idx < len(companies):
                            try:
                                company_elem = companies[co_idx]
                                emails, website = process_company_card(driver, wait, company_elem)
                                for email in emails:
                                    all_data.append({
                                        "company_name": get_company_name(company_elem),
                                        "email": email,
                                        "website": website,
                                        "source_exhibition": ex_name
                                    })
                                log(f"展会[{ex_name}] 公司[{get_company_name(company_elem)}] 邮箱数: {len(emails)}")
                                progress["exhibition_page"] = exhibition_page
                                progress["exhibition_idx"] = ex_idx
                                progress["company_page"] = current_company_page
                                progress["company_idx"] = co_idx + 1
                                save_progress(progress)
                                time.sleep(ACTION_DELAY)
                            except Exception as e:
                                log(f"公司处理异常，跳过: {e}")
                            finally:
                                # 关键：每次都重新获取公司元素，防止stale element
                                companies = get_company_elements(driver, wait)
                                co_idx += 1
                        # 公司翻页
                        try:
                            next_btn = driver.find_element(By.XPATH, "//a[contains(@class, 'pg-next')]")
                            if not next_btn.is_displayed() or "disabled" in next_btn.get_attribute("class"):
                                break
                            driver.execute_script("arguments[0].click();", next_btn)
                            time.sleep(2)
                            current_company_page += 1
                            progress["company_idx"] = 0
                            progress["company_page"] = current_company_page
                            save_progress(progress)
                        except Exception:
                            break
                    # 展会采集完，返回展会列表页
                    progress["company_idx"] = 0
                    progress["company_page"] = 1
                    save_progress(progress)
                    driver.back()
                    time.sleep(1)
                except Exception as e:
                    log(f"展会处理异常，跳过: {e}")
                    continue
                progress["exhibition_idx"] = ex_idx + 1
                save_progress(progress)
                time.sleep(EXHIBITION_DELAY)
            # 展会列表翻页
            try:
                next_btn = driver.find_element(By.XPATH, "//a[contains(@class, 'pg-next')]")
                if not next_btn.is_displayed() or "disabled" in next_btn.get_attribute("class"):
                    break
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(2)
                exhibition_page += 1
                progress["exhibition_page"] = exhibition_page
                progress["exhibition_idx"] = 0
                save_progress(progress)
            except Exception:
                break
    finally:
        # ===== 新增：公司聚合，邮箱/网址合并，保存为Excel =====
        company_dict = {}
        for row in all_data:
            key = (row["company_name"], row["source_exhibition"])
            if key not in company_dict:
                company_dict[key] = {
                    "公司名称": row["company_name"],
                    "邮箱": set(),
                    "企业网址": set(),
                    "展会名称": row["source_exhibition"]
                }
            if isinstance(row["email"], list):
                company_dict[key]["邮箱"].update(row["email"])
            elif row["email"]:
                company_dict[key]["邮箱"].add(row["email"])
            if isinstance(row["website"], list):
                company_dict[key]["企业网址"].update(row["website"])
            elif row["website"]:
                company_dict[key]["企业网址"].add(row["website"])
        df = pd.DataFrame([
            {
                "公司名称": v["公司名称"],
                "邮箱": ";".join(sorted(v["邮箱"])),
                "企业网址": ";".join(sorted(v["企业网址"])),
                "展会名称": v["展会名称"]
            }
            for v in company_dict.values()
        ])
        filename = f"showsfinder_data_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(filename, index=False)
        log(f"数据已保存到 {filename}")
        driver.quit()

if __name__ == "__main__":
    main() 