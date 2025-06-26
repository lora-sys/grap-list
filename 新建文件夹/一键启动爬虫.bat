@echo off
chcp 65001 > nul

echo ============================================
echo            邮箱爬虫程序启动器
echo ============================================
echo.

REM 检查是否在正确的目录
if not exist "advanced_crawler.py" (
    echo [错误] 程序文件丢失
    echo 请确保您是在解压后的文件夹中运行此程序
    echo 建议：将程序解压到桌面后再运行
    pause
    exit /b 1
)

REM 检查Chrome浏览器驱动
if not exist "chromedriver.exe" (
    echo [错误] 未找到Chrome浏览器驱动文件
    echo 请确保chromedriver.exe在当前文件夹中
    pause
    exit /b 1
)

REM 检查虚拟环境
if not exist "venv311\Scripts\activate.bat" (
    echo [错误] 程序运行环境丢失
    echo 请确保完整解压了所有文件
    echo 建议：重新解压程序后再试
    pause
    exit /b 1
)

echo [准备] 正在启动程序...
echo.

REM 激活虚拟环境
call "venv311\Scripts\activate.bat"

REM 检查并安装依赖
echo [检查] 正在检查程序所需组件...
pip install selenium==4.21.0 undetected-chromedriver==3.5.5 beautifulsoup4==4.13.4 lxml==5.4.0 pandas==2.3.0 openpyxl==3.1.3 coloredlogs==15.0.1 tqdm==4.67.1 --quiet

echo [提示] 如果首次运行较慢属于正常现象
echo [提示] 请耐心等待浏览器自动打开
echo.

REM 运行Python脚本
python "advanced_crawler.py"

REM 检查运行结果
if %errorlevel% neq 0 (
    echo.
    echo [错误] 程序运行遇到问题
    echo 请将上方的错误信息截图，发给技术支持
    echo.
    echo [English] Error occurred during program execution
    echo Please take a screenshot of the error message above and send it to technical support
    echo.
    echo 按任意键退出...
    pause > nul
    exit /b 1
)

echo.
echo [成功] 程序已完成运行！
echo.
echo 按任意键退出...

REM 退出虚拟环境
call "venv311\Scripts\deactivate.bat"

pause > nul 