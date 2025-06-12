# 英文文献翻译器 (带预览)

这是一个使用 PySide6 构建的桌面应用程序，用于翻译英文 PDF 文献为简体中文，并提供原文和译文的并排预览功能。

## 功能

*   选择本地 PDF 文件进行翻译。
*   支持多种在线翻译服务 (Google, Bing, DeepL 等)。
*   部分服务需要配置 API 密钥或环境变量。
*   提供翻译进度显示。
*   可选择翻译指定页码。
*   可配置翻译线程数。
*   提供原文和译文的并排预览窗口。
*   支持 Ctrl+滚轮 缩放预览（缩放比例实时显示），Shift+滚轮 横向滚动预览，缩放效果同步。
*   可选择显示/隐藏预览窗口。

## 安装与运行

建议在 Python 虚拟环境中安装和运行。

1.  **克隆或下载项目:**
    将项目文件（包括 `desktop_app.py`, `requirements.txt` 和这个 `README.md`）放到你的电脑上。

2.  **创建并激活 Conda 环境 (推荐):**
    *(需要先安装 Anaconda 或 Miniconda)*
    ```bash
    # 在项目根目录下打开终端 (如 Anaconda Prompt)
    conda create --name pdf_translator_env python=3.10  # 你可以指定希望的 Python 版本
    conda activate pdf_translator_env
    ```

3.  **安装依赖:**
    ```bash
    pip install -r requirements.txt
    ```
    *注意:* Conda 环境通常也使用 `pip` 来安装 `requirements.txt` 中的包。
    *注意:* `PySide6-Addons` 包含了 PDF 预览所需的模块。如果安装或运行时提示缺少 QtPdf 相关模块，请确保此库已成功安装。

4.  **运行程序:**
    ```bash
    python desktop_app.py
    ```

## 注意事项

*   **ONNX 模型:** 程序启动时会尝试加载用于文档布局分析的 ONNX 模型。`babeldoc` 库应该会自动处理下载（如果本地没有）。如果加载失败，程序仍可运行，但跳过图表/公式等高级功能可能受影响。
*   **翻译服务凭证:** 某些翻译服务（如 DeepL、Azure、Baidu、Tencent）需要在界面中输入相应的 API Key 或其他凭证才能使用。
*   **输出目录:** 翻译后的文件默认保存在程序运行目录下的 `pdf2zh_files` 文件夹中，你也可以在界面中更改输出目录。

## 后续开发

*   [ ] 解决预览窗口滚动不同步的问题。
*   [ ] (其他你计划的功能) 