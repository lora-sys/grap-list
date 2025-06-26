好的，根据我们之前的讨论和最新的 HTML 信息，我为你重新整理了需求文档。这次更新更侧重于登录部分的细节和整体结构的明确性。

---

## 🧾 展会邮箱爬虫系统（高稳定性与额度优化版）- 需求文档 (V2.0)

---

## 一、项目背景与目标

`https://data.showsfinder.com` 网站汇集了海量的国际展会及其参展企业信息。部分企业在公司详情页会提供**邮箱地址**与**公司官网链接**，这些信息对商业拓展具有重要价值。然而，该网站存在以下挑战：

*   **登录访问要求：** 核心数据需要登录后才能访问。
*   **复杂的页面结构：** 页面元素定位和数据提取需要精确的策略。
*   **海量数据量：** 网站包含大量展会和企业信息，需要高效处理。
*   **用户额度限制：** 作为免费用户，每一次脚本运行的成功至关重要，必须最大化利用有限的额度。
*   **潜在的反爬机制：** 网站可能存在访问频率限制、IP 封锁等机制。

本项目旨在开发一个**高度稳定、容错性极强、能够有效利用有限额度进行数据抓取**的定制化爬虫系统。系统将围绕**分批处理、断点续爬、异常跳过、节奏控制与登录认证**等核心原则进行设计和实现。

## 二、功能需求

### 2.1. 核心爬取功能

1.  **展会列表抓取：**
    *   能够从 `config["base_url"]` 和 `config["exhibition_list_url"]` 访问展会列表页面。
    *   使用 `config["exhibition_item_selector"]`（XPath）精准定位到每一个展会的链接，并提取展会链接和名称（通过 `config["exhibition_name_selector"]`，XPath，在展会项内部）。

2.  **公司信息抓取：**
    *   逐一访问每个展会的详情页面。
    *   在展会详情页中，使用 `config["company_card_selector"]`（XPath）定位到所有参展公司的信息卡片。
    *   从每个公司卡片中提取公司名称（通过 `config["company_name_selector"]`，XPath，通常是属性值如 `@title`）。

3.  **联系方式提取：**
    *   对于每个公司，首先通过检查特定页面元素（如登录后才出现的元素，或者直接触发登录弹窗的元素）判断是否需要登录。
    *   **登录流程：**
        *   如果需要登录，通过模拟点击公司卡片（或其他触发登录行为的元素）来期望弹出登录框。
        *   使用 `config["login_modal_selector"]`（CSS Selector）定位到整个登录弹出框的元素（例如 `div#passport-login-pop-api`），以确认登录框的出现。
        *   在登录弹出框中，使用 `config["username_input_id"]` 和 `config["password_input_id"]` 定位用户名和密码输入框，并填充用户提供的凭证。
        *   使用 `config["login_button_selector"]`（CSS Selector）定位并点击登录按钮。
        *   等待登录成功（例如，登录框消失或出现用户已登录的标识元素）。
    *   **信息抓取（登录后）：**
        *   在确认已登录后（或者如果登录是即时生效的），定位并点击联系方式下拉触发器，该触发器通过 `config["contact_dropdown_trigger_selector"]`（CSS Selector，例如 placeholder 为'联系方式'的输入框）定位。
        *   在展开的下拉选项中，定位并点击“邮箱”选项，使用 `config["contact_type_option_selector"]`（XPath）。
        *   等待包含邮箱信息区域加载完成，该区域由 `config["email_container_selector"]`（XPath）定位。
        *   使用 `config["email_selector"]`（XPath）从每个邮箱项中提取实际的邮箱地址。
        *   使用 `config["website_from_contact_selector"]`（XPath，在邮箱项内部）或 `config["website_onclick_attribute_selector"]`（XPath，提取官网 `onclick` 属性）来提取公司官网链接，并进行必要的 JavaScript `onclick` 属性解析，以获取最终的 URL。

4.  **数据存储：**
    *   将抓取到的公司名称、邮箱、官网链接等信息，保存到结构化文件中（例如 CSV 或 JSON 格式）。
    *   文件命名应包含日期时间戳，便于管理和追溯。

### 2.2. 稳定性与额度优化功能

1.  **断点续爬：**
    *   系统支持断点续爬。启动时加载进度文件（例如 `progress.json`）。
    *   进度文件记录已成功处理的展会链接（或展会内的公司序号），以确保下一次运行时从中断处继续。
    *   在成功处理完一个展会的所有公司或完成关键步骤后，及时更新进度文件。

2.  **节奏控制：**
    *   在关键操作之间（如页面跳转、元素查找、点击后等待）添加可配置的延时 (`time.sleep()`)，模拟人类行为，降低被检测和封锁的风险，并更好地适配网站响应速度，优化额度使用。

3.  **异常处理与跳过：**
    *   **局部异常跳过：** 在处理单个公司信息时（例如，某个公司卡片无法解析，或联系方式提取失败），系统应捕获异常，记录错误日志，并跳过该项，继续处理下一个公司，确保整体任务不中断。
    *   **全局异常处理：** 捕获可能导致爬虫中断的严重异常（如网络连接丢失、浏览器意外关闭），并尝试保存当前进度后安全退出。
    *   **登录失败处理：** 如果在设定次数内多次登录失败（基于错误类型判断，如凭证错误），应暂停爬取或发出警报，避免因凭证错误或网站变化而消耗过多额度。

4.  **登录状态检测与重登录：**
    *   在开始处理新的展会或执行需要登录才能进行的操作前，主动检测当前登录状态。
    *   如果检测到已退出登录，则自动触发登录流程，以维持数据访问权限。

5.  **浏览器管理：**
    *   能够安全地初始化、操作和关闭浏览器实例。
    *   支持配置使用 Headless 模式运行浏览器，以提高运行效率。

6.  **配置化设计：**
    *   所有关键的 URL、选择器（XPath 和 CSS Selector）、用户凭证、延时参数、超时设置等均通过 `config` 字典和外部配置进行管理。
    *   用户凭证（用户名、密码）应从安全的环境变量或独立的配置文件加载，不应硬编码。

### 2.3. 可选增强功能（为未来迭代考虑）

1.  **IP 地址轮换：** 集成代理 IP 池，在检测到 IP 被限制时自动切换 IP。
2.  **用户代理 (User-Agent) 轮换：** 随机更换用户代理字符串，模拟不同浏览器和设备。
3.  **验证码处理：** 集成第三方验证码识别服务，处理登录或操作中的验证码。
4.  **分布式爬取：** 将展会任务分解，由多个爬虫实例并行处理。
5.  **数据去重：** 在保存数据前，根据关键字段（如公司名称、官网链接）进行去重处理。

## 三、技术选型

*   **编程语言：** Python
*   **浏览器自动化库：** Selenium 或 Playwright (推荐 Playwright，通常在处理现代 Web 应用时更稳定且高效)
*   **数据存储：** CSV 文件或 JSON 文件
*   **进度管理：** JSON 文件

## 四、配置项说明

以下为核心的 `config` 配置字典，所有选择器、URL 和关键参数均在此定义，便于管理和维护：

```python
config = {
    # --- 基础配置 ---
    "base_url": "https://data.showsfinder.com", # 网站根 URL

    # --- 登录相关配置 ---
    # 整个登录弹出框的 CSS Selector。根据 HTML 结构，ID "passport-login-pop-api" 是最合适的标识。
    "login_modal_selector": "#passport-login-pop-api",

    # 用户名输入框的 ID
    "username_input_id": "userName",

    # 密码输入框的 ID
    "password_input_id": "passwd",

    # 登录按钮的 CSS Selector。精准定位到 type="button", class="pass-button pass-button-submit", value="登录" 的 input 元素。
    "login_button_selector": "input.pass-button.pass-button-submit[value='登录']",

    # --- 展会列表页配置 ---
    "exhibition_list_url": "https://data.showsfinder.com", # 展会列表页 URL
    # 遍历展会链接的 XPath。定位到包含展会链接的 a 标签。
    "exhibition_item_selector": "//h4[contains(@class, 'default_pointer_cs')]/ancestor::a",
    # 在展会项内部提取展会名称的 XPath。
    "exhibition_name_selector": ".//h4",
   #进入每个展会先筛选国家为中国
   

    # --- 公司卡片配置 ---
    # 遍历公司卡片的 XPath。定位到每个公司信息的链接/卡片。
    "company_card_selector": "//a[contains(@class, 'show_floating_frame')]",
    # 在公司卡片内部提取公司名称的 XPath (通常是属性值)。
    "company_name_selector": "./@title",

    # --- 公司详情页内的操作选择器 ---
    # 点击下拉框触发器 (placeholder为'联系方式'的输入框) 的 CSS Selector。
    "contact_dropdown_trigger_selector": "input.layui-input.layui-unselect.default_pointer_cs[placeholder='联系方式']",
    # 在下拉列表内选择“邮箱”的 XPath。
    "contact_type_option_selector": "//dd[@lay-value='邮箱']",

    # --- 邮箱及官网信息提取选择器 (在正确选择“邮箱”后) ---
    # 每个邮箱项的 XPath。
    "email_container_selector": "//div[@data-v='邮箱']//ul[@class='concat_c default_cursor_cs']/li",
    # 在邮箱项内部提取邮箱文本的 XPath。
    "email_selector": ".//div[@class='divs']/p[@class='copy-value']",
    # 在邮箱项内部提取信息来源为官网链接的 XPath。
    "website_from_contact_selector": ".//p[starts-with(@class, 'text-ellipsis')]/a[@title='企业官网']",
    # 提取官网 onclick 属性的 XPath (如果官网链接是通过 onclick 属性动态生成的)。
    "website_onclick_attribute_selector": ".//div[@class='top_detail_other_rows']//a[contains(@class, 'c_mainblue')]/@onclick",
}
```

**外部配置（需单独管理）：**

*   `USER_NAME`: 用户名。
*   `PASS_WORD`: 密码。
*   `PROGRESS_FILE`: 进度文件的路径（例如 `"progress.json"`）。
*   `LOG_FILE`: 日志文件的路径（例如 `"crawler.log"`）。
*   `PAGE_LOAD_TIMEOUT`: 页面加载超时时间（秒），例如 `15`。
*   `ELEMENT_WAIT_TIMEOUT`: 元素等待超时时间（秒），例如 `10`。
*   `ACTION_DELAY`: 操作之间的基本延时（秒），例如 `1.5`。
*   `EXHIBITION_DELAY`: 展会之间的延时（秒），例如 `3`。
*   `LOGIN_RETRY_COUNT`: 登录失败时的最大重试次数。
*   `HEADLESS_MODE`: 是否启用 Headless 模式运行浏览器（Boolean, `True` 或 `False`）。

## 五、数据输出格式

抓取的数据将以 CSV 或 JSON 格式保存，每条记录应包含以下字段：

*   `company_name`: 公司名称 (String)
*   `email`: 公司邮箱地址 (String, 如果未找到则为空字符串 `""`)
*   `website`: 公司官网链接 (String, 如果未找到则为空字符串 `""`)
*   `source_exhibition`: 此信息所属的展会名称 (String, 可选，用于追溯来源)

**文件名格式示例：** `showsfinder_data_YYYYMMDD_HHMMSS.csv` 或 `showsfinder_data_YYYYMMDD_HHMMSS.json`

## 六、运行与维护

*   **启动方式：** 通过 Python 脚本直接执行。
*   **配置调整：** 所有可调参数均通过上述 `config` 字典和外部配置文件进行管理。
*   **日志记录：** 系统应生成详细的日志文件，记录每次运行的状态、遇到的警告和错误信息，用于监控和故障排查。
*   **维护：** 定期检查网站结构的变化，及时更新配置文件中的选择器。监控爬虫运行状态，处理可能出现的意外情况。

---

### 七 写一个与正常脚本类似的测试脚本

*   **测试目标：** 确保脚本能够在不干扰正常业务的情况下，正确地模拟用户登录、展会列表遍历、公司详情页操作等功能。
*   **测试策略：** 针对每个关键功能模块，编写独立的测试用例。测试用例应覆盖正常流程、异常情况（如未登录、元素未加载等）以及边界条件。
*   **测试环境：** 使用测试账号和模拟数据，独立于生产环境运行。