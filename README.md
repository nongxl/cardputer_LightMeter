# Cardputer Photography Light Meter

[English](#english) | [中文](#中文)

---

<a name="english"></a>

## 📷 Cardputer Photography Light Meter (English)

A feature-rich photography light meter application for the M5Stack Cardputer, developed in MicroPython. It provides both Aperture Priority and Shutter Priority modes with a responsive and intuitive user interface.

![App Screenshot](20250722_163746.jpg) 
![App Screenshot](20250722_162342.webp) 
<!-- TODO: Replace this with your own app screenshot -->

### Hardware Requirements

*   M5Stack Cardputer
*   M5Stack DLight Unit (I2C Ambient Light Sensor)

### Features

-   **Dual-Mode Metering**: Supports Aperture Priority (`A`) and Shutter Priority (`S`) modes to suit different shooting scenarios.
-   **Real-Time Calculation**: After adjusting any exposure parameter (ISO, Aperture, Shutter), the third parameter is calculated and updated instantly without any confirmation needed.
-   **Intuitive UI**:
    *   The left side clearly displays the final exposure combination of ISO, Aperture (`APERT`), and Shutter Speed (`SPEED`).
    *   The right side features a vertical selection list for the currently adjustable parameter, providing clear context.
    *   The currently focused parameter and the selected value in the list are highlighted in **green** for clear operational focus.
-   **Smart Boundary Detection**:
    *   When an option in the selection list would cause the calculated result to exceed the preset range (e.g., a shutter speed faster than 1/4000s), that option is marked in **red**.
    *   The application **prevents** the user from selecting red-marked invalid options, ensuring operations stay within a valid exposure range.
-   **Non-Circular Selection**: The parameter list stops scrolling when it reaches the maximum or minimum value, which is more precise and aligns with professional habits.
-   **Hardware Info**: Displays the real-time LUX value from the DLight sensor and the device's battery level.

### How to Use

#### Key Controls

-   **`i` / `a` / `s` keys**: Switch operational focus and metering mode.
    -   **`a` key**: Sets to **Aperture Priority** mode and moves focus to Aperture (`APERT`).
    -   **`s` key**: Sets to **Shutter Priority** mode and moves focus to Shutter Speed (`SPEED`).
    -   **`i` key**: Moves focus to ISO. This action **does not** change the current metering mode (A/S).
-   **`.` key (Up Arrow)**: Scrolls up and selects a value for the focused parameter.
-   **`;` key (Down Arrow)**: Scrolls down and selects a value for the focused parameter.

### Installation

This project is developed with MicroPython. You can use tools like `mpremote` to deploy the code to your Cardputer.

1.  Connect your Cardputer to your computer via USB.
2.  Open your terminal and run the following command to copy the main program file to the device:
    mpremote connect autodetect fs cp main.py :
3. If your project includes library files, place them in a lib/ directory and upload them with the following command:
    mpremote connect autodetect fs cp -r lib/ :
4. Press the reset button on the side of the Cardputer, and the application will run automatically.
    
---

<a name="中文"></a>

## 📷 Cardputer 摄影测光表 (中文)

这是一款为 M5Stack Cardputer 打造的功能完善的摄影测光表应用，使用 MicroPython 开发。它提供了光圈优先和快门优先两种核心测光模式，并拥有一个响应迅速、交互直观的用户界面。

![应用截图](20250722_163746.jpg)
![应用截图](20250722_162342.webp)

### 硬件需求

*   M5Stack Cardputer
*   M5Stack DLight Unit (I2C 环境光传感器)

### 功能特性

-   **双模式测光**: 支持光圈优先 (`A`) 和快门优先 (`S`) 模式，满足不同拍摄场景的需求。
-   **实时计算**: 调整任何曝光参数（ISO、光圈、快门）后，程序会立即计算出第三个参数的值，无需等待或确认。
-   **直观的用户界面**:
    *   左侧清晰显示 ISO、光圈 (`APERT`) 和快门速度 (`SPEED`) 的最终曝光组合。
    *   右侧为当前可调参数的纵向选择列表，提供清晰的上下文。
    *   当前拥有输入焦点的参数和在列表中选中的值，均以**绿色**高亮显示，操作目标明确。
-   **智能边界检测**:
    *   当待选列表中的某个选项会导致计算结果超出预设范围时（例如，计算出的快门速度快于 1/4000s），该选项会在列表中被标为**红色**。
    *   程序会**阻止**用户选择被标为红色的无效选项，确保操作始终在有效曝光组合内。
-   **非循环选择**: 参数列表在选择到最大或最小值后会停止滚动，操作更精确、更符合专业习惯。
-   **硬件信息显示**: 实时显示 DLight 传感器读取的 LUX 值和设备电量。

### 如何使用

#### 按键控制

-   **`i` / `a` / `s` 键**: 切换操作焦点和测光模式。
    -   **`a` 键**: 设定为 **光圈优先** 模式，并将操作焦点切换到光圈 (`APERT`)。
    -   **`s` 键**: 设定为 **快门优先** 模式，并将操作焦点切换到快门速度 (`SPEED`)。
    -   **`i` 键**: 将操作焦点切换到 ISO。此操作**不会**改变当前的测光模式（光圈/快门优先）。
-   **`.` 键 (上箭头)**: 向上滚动并选择当前焦点参数的值。
-   **`;` 键 (下箭头)**: 向下滚动并选择当前焦点参数的值。

### 安装与部署

本项目基于 MicroPython 开发，您可以使用 `mpremote` 工具将代码部署到 Cardputer。

1.  将您的 Cardputer 通过 USB 连接到电脑。
2.  打开终端或命令行工具，执行以下命令将主程序文件复制到设备：
    mpremote connect autodetect fs cp main.py :
3.  如果您的项目包含库文件，请将它们放入 lib/ 目录，并使用以下命令上传：
    mpremote connect autodetect fs cp -r lib/ :
4. 按下 Cardputer 侧面的重启按钮，程序将自动运行。    
