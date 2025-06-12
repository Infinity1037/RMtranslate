#!/usr/bin/env python
import sys
import os
import subprocess
import platform # 用于检测操作系统以打开文件
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QComboBox, QLineEdit, QTextEdit,
    QProgressBar, QCheckBox, QSpinBox, QGroupBox, QStatusBar,
    QSplitter, QMessageBox # 导入QMessageBox用于显示对话框
)
from PySide6.QtCore import Qt, QThread, Signal, QUrl, QTimer # 导入QUrl和QTimer用于打开文件和定时任务
from PySide6.QtGui import QDesktopServices # 导入QDesktopServices用于打开外部文件
import asyncio # 导入asyncio用于任务取消事件
from asyncio import CancelledError # 导入CancelledError用于处理任务取消异常

# ----------------------------------------------------
# 从pdf2zh和babeldoc库导入所需功能
# ----------------------------------------------------
from pdf2zh.high_level import translate
from pdf2zh.config import ConfigManager
from pdf2zh.translators import (
    BaseTranslator,
    GoogleTranslator,
    BingTranslator,
    DeepLTranslator,
    DeepLXTranslator,
    AzureTranslator,
    TencentTranslator,
    BaiduTranslator,
    ArgosTranslator,
)
# 导入ONNX模型类，用于文档布局分析
from babeldoc.docvision.doclayout import OnnxModel

# 导入UI组件和翻译工作线程模块
from desktop_app_widgets import ZoomablePdfView, QPdfDocument, PDF_MODULE_AVAILABLE
from translation_worker import TranslationWorker
from desktop_app_ui import Ui_MainWindow # 导入新的UI类

# --- 应用程序新的整洁样式表 ---
APP_STYLESHEET = """
QWidget {
    /* font-family: "SF Pro Text", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; */ /* Common font stack */
    font-size: 10pt;
    background-color: #f7f7f7; /* Slightly adjusted light gray background */
    color: #333333; 
}

QMainWindow {
    background-color: #f7f7f7;
}

QLabel {
    background-color: transparent;
    padding: 2px;
}

QPushButton {
    background-color: #007aff; 
    color: white;
    border: 1px solid #007aff;
    padding: 7px 14px; /* Slightly increased padding for better touch */
    border-radius: 6px; 
    min-height: 22px; /* Slightly increased min-height */
}

QPushButton:hover {
    background-color: #005ecb; 
    border-color: #005ecb;
}

QPushButton:disabled {
    background-color: #e0e0e0; 
    color: #a0a0a0;
    border-color: #d0d0d0;
}

QPushButton:pressed {
    background-color: #004aaa; 
    border-color: #004aaa;
}

/* Styling for buttons with icons, if needed for distinction later */
/* QPushButton#iconButton { ... } */

QLineEdit, QComboBox, QSpinBox {
    padding: 7px; /* Increased padding */
    border: 1px solid #cccccc; /* Slightly darker border for better definition */
    border-radius: 6px; 
    background-color: white;
    min-height: 22px; /* Consistent min-height */
}

QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {
    background-color: #f0f0f0; /* Slightly lighter gray for disabled inputs */
    color: #aaaaaa; 
    border-color: #d0d0d0;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #007aff; 
    /* box-shadow: 0 0 0 2px rgba(0, 122, 255, 0.2); */ /* Simulated glow - might need QGraphicsEffect */
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px; /* Slightly wider */
    border-left-width: 1px;
    border-left-color: #cccccc;
    border-left-style: solid;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    background-color: #f0f0f0; 
}

QComboBox::down-arrow {
    image: url(:/qt-project.org/styles/commonstyle/images/down_arrow.png); /* Try to use a standard Qt resource */
    width: 12px; /* Adjust size as needed */
    height: 12px;
}
QComboBox::down-arrow:on {
    top: 1px;
}
/* Enhancing ComboBox items */
QComboBox QAbstractItemView { /* Target the popup list */
    border: 1px solid #cccccc;
    background-color: white;
    selection-background-color: #007aff;
    selection-color: white;
    padding: 2px;
}
QComboBox QAbstractItemView::item {
    padding: 4px 6px;
    min-height: 20px;
}


QGroupBox {
    border: 1px solid #d9d9d9; /* Slightly more visible border */
    border-radius: 8px;
    margin-top: 15px; /* Increased margin for title */
    padding: 20px 12px 12px 12px; 
    background-color: #ffffff; 
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 3px 10px; /* Slightly more padding */
    left: 10px; 
    background-color: #efefef; /* Light distinct background for title */
    border: 1px solid #d9d9d9; /* Border around title */
    border-bottom: 1px solid #efefef; /* Blend bottom border with background */
    border-radius: 5px;
    color: #333333; /* Darker title color for better contrast */
    font-weight: bold;
    font-size: 9.5pt; 
}

QProgressBar {
    border: 1px solid #cccccc;
    border-radius: 6px; 
    text-align: center;
    background-color: #e8e8e8; 
    height: 12px; /* Slightly taller */
    color: #444444; 
    font-weight: bold;
}

QProgressBar::chunk {
    background-color: #007aff; 
    border-radius: 5px; 
    margin: 1px; /* Add a tiny margin to chunk for visual separation */
}

QSplitter::handle {
    background-color: #e0e0e0; 
}

QSplitter::handle:horizontal {
    width: 6px; 
    margin: 0 2px; 
    border-left: 1px solid #c8c8c8; 
    border-right: 1px solid #c8c8c8;
    background-color: #e8e8e8;
}
QSplitter::handle:horizontal:hover {
    background-color: #d0d0d0;
}

QSplitter::handle:vertical {
    height: 6px; 
    margin: 2px 0; 
    border-top: 1px solid #c8c8c8;
    border-bottom: 1px solid #c8c8c8;
    background-color: #e8e8e8;
}
QSplitter::handle:vertical:hover {
    background-color: #d0d0d0;
}

QStatusBar {
    font-size: 9pt;
    color: #555555; /* Slightly darker status bar text */
}

QLineEdit[missing="true"] {
    border: 1px solid #ff3333; /* Brighter red for error */
    background-color: #fff0f0; /* Light red background for error */
}

QCheckBox {
    spacing: 6px; 
    padding: 3px 0; 
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #bbbbbb;
    border-radius: 4px;
    background-color: #ffffff;
}
QCheckBox::indicator:hover {
    border: 1px solid #007aff;
}
QCheckBox::indicator:checked {
    background-color: #007aff;
    border: 1px solid #007aff;
    image: url(:/qt-project.org/styles/commonstyle/images/checkbox_checked.png); /* Standard checkmark */
}
QCheckBox::indicator:checked:hover {
    background-color: #005ecb;
    border: 1px solid #005ecb;
}
QCheckBox:disabled {
    color: #a0a0a0;
}
QCheckBox::indicator:disabled {
    background-color: #e0e0e0;
    border: 1px solid #d0d0d0;
}


"""

# --- 直接定义语言映射表 --- 

# lang_map = { ... }

# --- 定义桌面应用程序的翻译服务映射表 ---
service_map: dict[str, type[BaseTranslator]] = {
    "Google": GoogleTranslator,
    "Bing": BingTranslator,
    "Baidu": BaiduTranslator,
    "DeepL": DeepLTranslator,
    "DeepLX": DeepLXTranslator,
    "Azure": AzureTranslator,
    "Tencent": TencentTranslator,
    "Argos Translate": ArgosTranslator,
}

# --- 加载ONNX布局分析模型 --- 
try:
    print("正在加载布局分析模型...")
    LAYOUT_MODEL = OnnxModel.load_available()
    print("布局分析模型加载成功。")
except Exception as e:
    print(f"加载布局分析模型出错: {e}")
    print("布局分析（图形/表格/公式跳过）功能可能无法正常工作。")
    LAYOUT_MODEL = None # 如果加载失败，则在没有模型的情况下继续

# 尝试导入必要的PDF模块
try:
    from PySide6.QtPdfWidgets import QPdfView
    from PySide6.QtPdf import QPdfDocument
    PDF_MODULE_AVAILABLE = True

    # --- Custom Zoomable PDF View --- 
    class ZoomablePdfView(QPdfView):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setZoomMode(QPdfView.ZoomMode.FitInView)
            self.setPageMode(QPdfView.PageMode.MultiPage)
            self.setFocusPolicy(Qt.ClickFocus) 

        def wheelEvent(self, event): # 可以添加QWheelEvent类型提示（如需要）
            modifiers = QApplication.keyboardModifiers()
            
            # 情况1：按住Shift键（用于水平滚动）
            if (modifiers & Qt.ShiftModifier) and not (modifiers & Qt.ControlModifier):
                h_scrollbar = self.horizontalScrollBar()
                if h_scrollbar and h_scrollbar.isVisible() and h_scrollbar.maximum() > h_scrollbar.minimum():
                    delta = event.angleDelta().y()
                    current_value = h_scrollbar.value()
                    step = delta // 2 
                    new_value = current_value - step
                    new_value = max(h_scrollbar.minimum(), min(new_value, h_scrollbar.maximum()))
                    
                    h_scrollbar.setValue(new_value)
                    event.accept()
                    return  # 自定义水平滚动已处理，所以返回
                # 如果按下了Shift但没有活动/有效的水平滚动条，这里不做任何操作
                # 事件将在最后传递给super().wheelEvent()
            
            # 情况2：按住Ctrl键（用于缩放）
            elif (modifiers & Qt.ControlModifier) and not (modifiers & Qt.ShiftModifier):
                delta = event.angleDelta().y()
                current_zoom_factor = self.zoomFactor()
                new_zoom_factor = current_zoom_factor 
                
                if delta > 0:  
                    new_zoom_factor = current_zoom_factor * 1.15
                elif delta < 0:
                    new_zoom_factor = current_zoom_factor / 1.15
                
                # 检查缩放因子是否实际改变且在范围内
                if abs(new_zoom_factor - current_zoom_factor) > 1e-9 and 0.1 < new_zoom_factor < 50.0: 
                    if self.zoomMode() != QPdfView.ZoomMode.Custom:
                        self.setZoomMode(QPdfView.ZoomMode.Custom)
                    self.setZoomFactor(new_zoom_factor)
                    # self.update()  # 如果缩放后出现视觉故障，可能需要调用self.update()
                    event.accept()
                    return  # 自定义缩放已处理，所以返回
                # 如果按下了Ctrl但缩放未应用（例如，已达到限制），这里不做任何操作
                # 事件将在最后传递给super().wheelEvent()

            # 默认情况：如果以上自定义处理程序都未返回，则传递给基类
            # 这包括：没有相关修饰键，或者有修饰键但条件不满足自定义操作
            super().wheelEvent(event)

except ImportError:
    print("Warning: PySide6.QtPdfWidgets or PySide6.QtPdf not found.")
    print("PDF preview functionality will be disabled.")
    print("Try installing with: pip install PySide6-Addons")
    # 如果导入失败，使用QLabel作为占位符
    # 将ZoomablePdfView定义为QLabel，这样其余代码不会中断
    class ZoomablePdfView(QLabel):
         def __init__(self, parent=None):
             super().__init__("PDF 预览不可用 (缺少 QtPdfWidgets 或 QtPdf)", parent)
             self.setAlignment(Qt.AlignCenter)
         # 添加MainWindow期望的虚拟方法
         def setDocument(self, doc): pass
         def setZoomMode(self, mode): pass
         def setPageMode(self, mode): pass
         def zoomFactor(self): return 1.0
         def setZoomFactor(self, factor): pass
         def pageNavigator(self): return None # 对于滚动同步检查很重要

    QPdfView = ZoomablePdfView # 让QPdfView指向我们的占位符
    QPdfDocument = None
    PDF_MODULE_AVAILABLE = False

class TranslationWorker(QThread):
    """ 用于运行翻译任务的工作线程 """
    progress = Signal(int, str)  # 进度百分比和描述信息
    finished = Signal(bool, str)  # 成功状态(布尔值)和仅单语言输出路径
    error = Signal(str)  # 错误信息

    def __init__(self, params):
        super().__init__()
        self.params = params
        self.cancellation_event = asyncio.Event()  # 创建取消事件
        self.params['cancellation_event'] = self.cancellation_event  # 将取消事件添加到参数中

    def run(self):
        output_mono_path = None
        output_dual_path = None
        try:
            print("开始翻译，参数：", self.params)
            
            # 调用translate函数，返回元组列表
            results_list = translate(**self.params)

            # 由于我们只传递一个文件，列表应该只有一个元素：
            # 即元组 (output_mono_path, output_dual_path)
            if results_list and len(results_list) == 1:
                output_mono_path, output_dual_path = results_list[0] # 解包元组
                # 仅发送单语言路径
                self.finished.emit(True, output_mono_path)
                 # --- 可选：删除双语文件 --- 
                if output_dual_path and os.path.exists(output_dual_path):
                    try:
                        os.remove(output_dual_path)
                        print(f"已删除未使用的双语文件: {output_dual_path}")
                    except OSError as e:
                         print(f"删除双语文件 {output_dual_path} 时出错: {e}")
                # --- 结束可选删除部分 --- 
            else:
                # 处理意外的返回格式（例如，空列表或多个结果）
                print(f"错误：从translate函数获得意外的返回值：{results_list}")
                self.error.emit("翻译函数返回格式错误")
                self.finished.emit(False, "") # 错误时不返回路径

        except CancelledError:
             print("翻译在工作线程中被取消。")
             self.error.emit("任务已取消")
             self.finished.emit(False, "") # 取消时不返回路径
        except Exception as e:
            print(f"工作线程中的错误: {e}")
            self.error.emit(str(e))
            self.finished.emit(False, "") # 错误时不返回路径

    def stop(self):
        print("尝试通过设置取消事件来停止工作线程...")
        if self.cancellation_event:
             self.cancellation_event.set()  # 设置取消事件以停止任务

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # --- 首先初始化非UI属性 ---
        self.selected_file_path = None
        self.worker = None
        self.output_mono_path = None
        self.output_dir = os.path.join(os.getcwd(), "pdf2zh_files") # 更改默认输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        self.pdf_doc_orig = None
        self.pdf_doc_trans = None
        self.is_syncing_zoom = False
        self.zoom_sync_connected = False
        self.zoom_level = 1.0
        
        # 凭证部件字典需要在setupUi访问之前存在
        self.credentials_widgets = {}
        
        # --- 使用 Ui_MainWindow 类设置UI ---
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # --- 连接预览控制信号 ---
        self.sync_scroll = self.findChild(QCheckBox, "syncScroll")
        self.sync_zoom = self.findChild(QCheckBox, "syncZoom")
        self.zoom_in = self.findChild(QPushButton, "zoomIn")
        self.zoom_out = self.findChild(QPushButton, "zoomOut")
        # self.zoom_level_label = self.findChild(QLabel, "zoomLevel") # 已被QLineEdit替代
# 我们将直接使用Ui_MainWindow类中的self.ui.zoom_level_input

        if self.sync_scroll:
            self.sync_scroll.stateChanged.connect(self.toggle_sync_scroll)
        if self.sync_zoom:
            self.sync_zoom.stateChanged.connect(self.toggle_sync_zoom)
        if self.zoom_in:
            self.zoom_in.clicked.connect(self.zoom_in_preview)
        if self.zoom_out:
            self.zoom_out.clicked.connect(self.zoom_out_preview)

        # 连接新的QLineEdit用于手动输入缩放值
        if hasattr(self.ui, 'zoom_level_input') and self.ui.zoom_level_input:
            self.ui.zoom_level_input.returnPressed.connect(self.apply_manual_zoom)

        # --- 后UI设置 --- 
        # 向下拉框添加服务项（需要service_map）
        for service_name in service_map.keys():
            self.ui.service_combo.addItem(service_name)

        # 连接信号到槽（方法）
        self.ui.select_file_button.clicked.connect(self.select_file)
        self.ui.change_dir_button.clicked.connect(self.select_output_dir)
        self.ui.service_combo.currentTextChanged.connect(self.update_credential_fields)
        self.ui.start_button.clicked.connect(self.start_translation)
        self.ui.cancel_button.clicked.connect(self.cancel_translation)
        self.ui.open_mono_button.clicked.connect(self.open_mono_file)
        self.ui.open_folder_button.clicked.connect(self.open_output_folder)
        self.ui.options_group.toggled.connect(self.toggle_options_enabled)

        # 设置初始UI状态
        self.ui.status_bar.showMessage("准备就绪 (英 -> 简中)")
        self.update_credential_fields(self.ui.service_combo.currentText())
        self.toggle_options_enabled(self.ui.options_group.isChecked())

        # 设置初始分割器大小
        # self.main_splitter.setSizes([self.width() // 3, 2 * self.width() // 3]) # 已移除，main_splitter不再存在
        # 设置PDF预览分割器的初始大小（相等大小）
        # 计算右侧面板的可用宽度（近似值）
        right_panel_width = self.width() - 350 - 20 # 窗口宽度 - 控制面板宽度 - 边距/间距估计
        if right_panel_width < 200: right_panel_width = 200 # 最小宽度
        self.ui.pdf_splitter.setSizes([right_panel_width // 2, right_panel_width // 2])

        # 存储原始和翻译后的PDF路径
        self.original_pdf_path = None
        self.translated_pdf_path = None
        self.monolingual_output_path = None # 用于.txt或.docx输出
        self.bilingual_output_path = None # 用于_bilingual.pdf输出

        # 连接同步复选框（假设它们存在于Ui_MainWindow中）
        if hasattr(self.ui, 'sync_scroll') and hasattr(self.ui, 'sync_zoom'):
            self.ui.sync_scroll.stateChanged.connect(self.toggle_sync_scroll)
            self.ui.sync_zoom.stateChanged.connect(self.toggle_sync_zoom)
            self.toggle_sync_scroll(self.ui.sync_scroll.isChecked())
            self.toggle_sync_zoom(self.ui.sync_zoom.isChecked())
            
        # 连接预览可见性QGroupBox的toggled信号
        if hasattr(self.ui, 'preview_visibility_group') and self.ui.preview_visibility_group.isCheckable():
            self.ui.preview_visibility_group.toggled.connect(self.toggle_preview_visibility)
            # 根据组框的选中状态设置初始状态
            self.toggle_preview_visibility(self.ui.preview_visibility_group.isChecked())

        # 基于默认选择的服务初始化凭证字段
        self.update_credential_fields(self.ui.service_combo.currentText())

        # asyncio事件循环设置，用于取消任务
        self.async_event = None # 将在工作线程的事件循环中设置为asyncio.Event()
        self.current_worker = None # 用于翻译工作线程
        
        # 用于视图的PDF文档
        self.original_doc = None
        self.translated_doc = None
        
        # 设置初始缩放级别显示
        if hasattr(self.ui, 'zoom_level_input') and self.ui.zoom_level_input: # 检查新的QLineEdit是否存在
             self.ui.zoom_level_input.setText(f"{int(self.ui.pdf_view_orig.zoomFactor() * 100)}%")
        
        # 连接原始PDF视图的zoomFactorChanged信号以更新缩放显示
        if hasattr(self.ui, 'pdf_view_orig') and self.ui.pdf_view_orig and PDF_MODULE_AVAILABLE:
            self.ui.pdf_view_orig.zoomFactorChanged.connect(self._update_zoom_display)

        # 初始状态栏消息
        self.ui.status_bar.showMessage("准备就绪", 5000)

    def _update_zoom_display(self, zoom_factor):
        """仅更新缩放级别输入框的显示"""
        if hasattr(self.ui, 'zoom_level_input') and self.ui.zoom_level_input:
            zoom_percentage = int(zoom_factor * 100)
            # 检查输入框当前文本是否与新值相同，避免不必要的setText和潜在的信号循环 (如果输入框有自己的textChanged信号处理)
            if self.ui.zoom_level_input.text() != f"{zoom_percentage}%":
                self.ui.zoom_level_input.setText(f"{zoom_percentage}%")

    def select_file(self):
        """ 打开文件对话框选择PDF文件 """
        self.disconnect_view_sync() # 在加载新的原始文件前断开视图同步
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 PDF 文件",
            "",
            "PDF Files (*.pdf)"
        )
        if file_path:
            # 规范化路径
            self.selected_file_path = os.path.normpath(file_path)
            display_path = os.path.join(os.path.basename(os.path.dirname(self.selected_file_path)), os.path.basename(self.selected_file_path))
            if len(display_path) > 40:
                 display_path = "..." + display_path[-37:]
            self.ui.file_label.setText(display_path)
            self.ui.status_bar.showMessage(f"已选择文件: {self.selected_file_path}")
            self.ui.result_buttons_widget.setVisible(False)
            self.load_pdf(self.ui.pdf_view_orig, self.selected_file_path, is_original=True)
            self.clear_pdf(self.ui.pdf_view_trans, is_original=False) # 清除翻译视图
        else:
            self.selected_file_path = None
            self.ui.file_label.setText("未选择文件")
            self.ui.status_bar.showMessage("未选择文件")
            self.ui.result_buttons_widget.setVisible(False)
            self.clear_pdf(self.ui.pdf_view_orig, is_original=True)
            self.clear_pdf(self.ui.pdf_view_trans, is_original=False)

    def select_output_dir(self):
        """ 打开目录对话框选择输出文件夹 """
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            self.output_dir # 从当前输出目录开始浏览
        )
        if dir_path:
            self.output_dir = dir_path
            # 更新标签，处理可能过长的路径以便显示
            display_dir = dir_path
            if len(display_dir) > 40:
                 display_dir = "..." + display_dir[-37:]
            self.ui.output_dir_label.setText(f"输出: {display_dir}")
            self.ui.status_bar.showMessage(f"输出目录已更改为: {dir_path}")
        else:
            # 用户取消，保持现有目录
            self.ui.status_bar.showMessage("输出目录未更改")

    def update_credential_fields(self, service_name):
        """ 根据所选服务动态更新凭证输入字段。 """
        # --- 更有力地清除布局内容 --- 
        # 从credentials_layout中移除所有小部件和布局
        while (item := self.ui.credentials_layout.takeAt(0)) is not None:
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # 递归清除嵌套布局（重要）
                while (sub_item := item.layout().takeAt(0)) is not None:
                     if sub_item.widget():
                         sub_item.widget().deleteLater()
                item.layout().deleteLater() # 删除布局本身
        self.credentials_widgets.clear()
        # --- 结束清除 --- 
        
        if not service_name or service_name not in service_map:
             self.ui.credentials_group.setVisible(False)
             return
             
        translator_class = service_map[service_name]
        required_envs = translator_class.envs
        
        if not required_envs:
            self.ui.credentials_group.setVisible(False)
            return
            
        self.ui.credentials_group.setVisible(True)
        # --- 重新添加小部件 --- 
        for key, default_value in required_envs.items():
            hbox = QHBoxLayout()
            label = QLabel(f"{key}:")
            input_field = QLineEdit()
            if "KEY" in key.upper() or "SECRET" in key.upper():
                 input_field.setEchoMode(QLineEdit.Password)
            saved_value = ConfigManager.get_env_by_translatername(translator_class, key)
            input_field.setText(saved_value or "")
            hbox.addWidget(label)
            hbox.addWidget(input_field)
            self.ui.credentials_layout.addLayout(hbox)
            self.credentials_widgets[key] = input_field

    def start_translation(self):
        """ 收集输入并启动翻译工作线程 """
        if not self.selected_file_path:
            # 文件缺失时使用 QMessageBox
            QMessageBox.warning(self, "缺少文件", "请先选择一个 PDF 文件再开始翻译。")
            self.ui.status_bar.showMessage("错误：未选择文件") # 保留状态栏消息
            return
        if LAYOUT_MODEL is None:
            print("Warning: Layout model not loaded. Figure/table skipping may not work.")
            # 可选择向用户显示非阻塞警告
            # QMessageBox.information(self, "提示", "布局分析模型未加载，图表/公式跳过功能可能无法正常工作。")

        self.disconnect_view_sync() 
        self.clear_pdf(self.ui.pdf_view_trans, is_original=False)
        self.output_mono_path = None

        service_name = self.ui.service_combo.currentText()
        if service_name not in service_map:
             QMessageBox.critical(self, "服务错误", f"选择的服务 '{service_name}' 无效或未正确配置。")
             self.ui.status_bar.showMessage(f"错误: 未知的服务 '{service_name}'")
             return
        translator_class = service_map[service_name]

        # --- 收集并验证凭证 ---
        envs = {}
        credentials_missing = False
        missing_keys = []
        config_changed = False 
        if self.ui.credentials_group.isVisible():
            for key, widget in self.credentials_widgets.items():
                value = widget.text().strip()
                saved_value = ConfigManager.get_env_by_translatername(translator_class, key)
                
                # 首先重置 missing 属性
                widget.setProperty("missing", False)
                self.style().unpolish(widget); self.style().polish(widget)

                if not value:
                    credentials_missing = True
                    widget.setProperty("missing", True)
                    missing_keys.append(key)
                    self.style().unpolish(widget); self.style().polish(widget)
                else:
                    envs[key] = value
                    if value != saved_value:
                         ConfigManager.set_env_by_translatername(translator_class, key, value)
                         config_changed = True 

        if credentials_missing:
             missing_keys_str = "\n • " + "\n • ".join(missing_keys)
             QMessageBox.warning(self, "凭证缺失", f"请为 {service_name} 服务填写以下必需信息：{missing_keys_str}")
             self.ui.status_bar.showMessage(f"错误: {service_name} 服务缺少凭证。") 
             return
            
        # --- 收集参数 ---
        params = {}
        params['files'] = [self.selected_file_path]
        params['service'] = service_name 
        params['lang_in'] = 'en' 
        params['lang_out'] = 'zh' 

        # 解析页面
        page_str = self.ui.page_input.text().strip()
        selected_page = None
        if self.ui.options_group.isChecked() and page_str:
            try:
                selected_page = []
                for p in page_str.replace(" ", "").split(","):
                    if "-" in p:
                        parts = p.split("-")
                        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
                             raise ValueError(f"无效范围: '{p}'")
                        start, end = int(parts[0]), int(parts[1])
                        if start <= 0 or end <= 0 or start > end:
                            raise ValueError(f"无效范围: '{p}' (页码必须 > 0 且 start <= end)")
                        selected_page.extend(range(start - 1, end))
                    elif p.isdigit():
                        page_num = int(p)
                        if page_num <= 0:
                            raise ValueError(f"无效页码: '{p}' (必须 > 0)")
                        selected_page.append(page_num - 1)
                    else:
                         raise ValueError(f"无效输入: '{p}'")
                selected_page = sorted(list(set(selected_page)))
            except Exception as e:
                QMessageBox.warning(self, "格式错误", f"无效的页面范围格式：\n{e}\n\n请输入类似 '1-3,5,7' 的格式，页码需大于0。")
                self.ui.status_bar.showMessage(f"错误: 无效的页面范围格式 - {e}")
                return
        params['pages'] = selected_page

        # 收集简化选项
        params['thread'] = self.ui.thread_spinbox.value() if self.ui.options_group.isChecked() else 4
        
        # 将已移除的选项硬编码为默认值或基于逻辑设置
        params['skip_subset_fonts'] = False 
        params['ignore_cache'] = False 
        params['vfont'] = '' 

        params['envs'] = envs
        params['callback'] = self.qt_progress_callback
        params['model'] = LAYOUT_MODEL 
        params['output'] = self.output_dir 
        
        # 为此运行创建取消事件
        cancellation_event = asyncio.Event()
        params['cancellation_event'] = cancellation_event

        # --- 设置工作线程 ---
        if self.worker and self.worker.isRunning():
            print("Warning: Previous worker still running? Stopping it first.")
            self.worker.stop() 
            
        self.worker = TranslationWorker(params)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.translation_finished)
        self.worker.error.connect(self.translation_error)

        # --- 更新UI ---
        self.ui.start_button.setEnabled(False)
        self.ui.cancel_button.setEnabled(True)
        self.ui.progress_bar.setValue(0)
        self.ui.progress_bar.setVisible(True)
        self.ui.result_buttons_widget.setVisible(False)
        self.ui.status_bar.showMessage("正在开始翻译...")

        self.worker.start()

    def cancel_translation(self):
        """ 通知工作线程停止 """
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.ui.status_bar.showMessage("正在取消...")
        else:
             self.reset_ui_state()

    def update_progress(self, value, description):
        """ 更新进度条和状态消息 """
        self.ui.progress_bar.setValue(value)
        self.ui.status_bar.showMessage(description)

    def translation_finished(self, success, mono_path):
        """ 翻译线程完成（成功与否）时调用 """
        if success:
            self.output_mono_path = os.path.normpath(mono_path)
            display_mono = self.output_mono_path
            if len(display_mono) > 60: display_mono = "..." + display_mono[-57:]
            self.ui.status_bar.showMessage(f"翻译完成！输出: {display_mono}")
            self.ui.result_buttons_widget.setVisible(True)
            self.load_pdf(self.ui.pdf_view_trans, self.output_mono_path, is_original=False)
            if PDF_MODULE_AVAILABLE and self.pdf_doc_orig and self.pdf_doc_trans and self.pdf_doc_orig.pageCount() > 0 and self.pdf_doc_trans.pageCount() > 0:
               print("Attempting to connect view sync (ZOOM ONLY)...") 
               self.connect_view_sync()
            else:
               print("Skipping view sync connection (docs not ready or PDF module unavailable).")
        if self.worker: 
            self.reset_ui_state()
            
    def translation_error(self, error_message):
        """ 翻译线程中发生错误时调用 """
        error_title = "翻译出错"
        detailed_error = f"翻译过程中遇到问题：\n\n{error_message}\n\n请检查您的网络连接、API凭证或PDF文件后重试。"
        QMessageBox.critical(self, error_title, detailed_error)
        self.ui.status_bar.showMessage(f"{error_title}: {error_message}") 
        self.ui.result_buttons_widget.setVisible(False)
        self.reset_ui_state()

    def reset_ui_state(self):
         """ 将按钮和进度条重置为空闲状态 """
         self.ui.start_button.setEnabled(True)
         self.ui.cancel_button.setEnabled(False)
         self.ui.progress_bar.setVisible(False)
         self.worker = None

    def qt_progress_callback(self, t_obj):
        """ 为Qt信号适配类似tqdm的回调对象。 """
        # 发射前检查工作线程是否存在
        if self.worker and hasattr(t_obj, 'total') and t_obj.total > 0:
             percentage = int((t_obj.n / t_obj.total) * 100)
             desc = getattr(t_obj, 'desc', 'Translating...')
             if not desc: desc = 'Translating...'
             # 仅当工作线程正在运行时才发射信号（可能已被取消）
             if self.worker.isRunning():
                  self.worker.progress.emit(percentage, desc)
                  
    # --- 打开结果的方法 ---
    def open_mono_file(self):
        if self.output_mono_path and os.path.exists(self.output_mono_path):
            self.open_path(self.output_mono_path)
        else:
             self.ui.status_bar.showMessage("错误：找不到翻译文件路径。")
             
    def open_output_folder(self):
        if self.output_dir and os.path.exists(self.output_dir):
             self.open_path(self.output_dir)
        elif self.output_mono_path: # Fallback to file's dir if output_dir is weird
             folder = os.path.dirname(self.output_mono_path)
             if os.path.exists(folder):
                  self.open_path(folder)
             else:
                  self.ui.status_bar.showMessage("错误：找不到输出文件夹路径。")
        else:
             self.ui.status_bar.showMessage("错误：找不到输出文件夹路径。")
             
    def open_path(self, path):
        """ 使用默认系统应用程序打开文件或目录。 """
        try:
            norm_path = os.path.normpath(path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(norm_path))
            self.ui.status_bar.showMessage(f"正在尝试打开: {os.path.basename(norm_path)}")
        except Exception as e:
            self.ui.status_bar.showMessage(f"错误：无法打开路径 {norm_path}: {e}")
            print(f"Error opening path {norm_path}: {e}") # 记录详细错误

    def load_pdf(self, pdf_view, file_path, is_original=True):
        """ 将PDF加载到指定的QPdfView中。 """
        print(f"Attempting to load PDF into {'original' if is_original else 'translated'} view: {file_path}")
        if not PDF_MODULE_AVAILABLE:
            print(" PDF module not available.")
            return
            
        if not file_path or not os.path.exists(file_path):
            print(f" File path invalid or file does not exist: {file_path}")
            # 通过self引用访问视图（在setupUi期间设置）
            if isinstance(self.pdf_view_orig if is_original else self.pdf_view_trans, QLabel):
                 (self.pdf_view_orig if is_original else self.pdf_view_trans).setText(f"无法加载: {'文件不存在' if file_path else '无文件'}")
            # 清除以前的文档（如果有）
            (self.pdf_view_orig if is_original else self.pdf_view_trans).setDocument(None)
            if is_original: self.pdf_doc_orig = None
            else: self.pdf_doc_trans = None
            return

        # 使用从widgets模块导入的QPdfDocument
        new_doc = QPdfDocument(self) 
        
        # 关闭先前的文档
        doc_to_close = self.pdf_doc_orig if is_original else self.pdf_doc_trans
        if doc_to_close:
             print(f" Closing previous {'original' if is_original else 'translated'} document.")
             doc_to_close.close()

        # 分配新文档
        if is_original:
             self.pdf_doc_orig = new_doc
        else:
             self.pdf_doc_trans = new_doc
             
        try:
            norm_path = os.path.normpath(file_path)
            print(f" Loading normalized path: {norm_path}")
            status = new_doc.load(norm_path) 
            print(f" QPdfDocument.load status enum member: {status}")

            # 检查加载状态（使用QPdfDocument中的Error枚举）
            if status != QPdfDocument.Error.None_:
                 print(f" Error loading PDF '{norm_path}': Status Enum {status}")
                 self.ui.status_bar.showMessage(f"错误: 无法加载PDF '{os.path.basename(norm_path)}'")
                 if isinstance(pdf_view, QLabel): pdf_view.setText(f"无法加载: {os.path.basename(norm_path)}")
                 new_doc.close() 
                 if is_original: self.pdf_doc_orig = None
                 else: self.pdf_doc_trans = None
                 pdf_view.setDocument(None)
                 return
            
            print(f" Load status OK. Trying to set document...")
            pdf_view.setDocument(new_doc) # Set the new document on the view
            print(f" Set document successful.")

            page_count = new_doc.pageCount()
            print(f" Document page count: {page_count}")
            if page_count == 0:
                print(" Warning: Loaded PDF has 0 pages.")
                self.ui.status_bar.showMessage(f"警告: PDF '{os.path.basename(norm_path)}' 加载成功但页数为0")

        except Exception as e:
            import traceback
            print(f"!!! Exception during PDF processing for '{file_path}' !!!")
            print(f" Exception Type: {type(e)}"); print(f" Exception Args: {e.args}"); print(f" Exception Message: {e}")
            traceback.print_exc()
            self.ui.status_bar.showMessage(f"错误: 处理PDF时异常 '{os.path.basename(file_path)}'")
            if isinstance(pdf_view, QLabel): pdf_view.setText(f"处理异常: {os.path.basename(file_path)}")
            # 确保在异常时关闭new_doc
            new_doc.close()
            if is_original: self.pdf_doc_orig = None
            else: self.pdf_doc_trans = None
            if pdf_view and hasattr(pdf_view, 'setDocument'): pdf_view.setDocument(None)

    def clear_pdf(self, pdf_view, is_original=True):
         if not PDF_MODULE_AVAILABLE:
             if isinstance(pdf_view, QLabel): pdf_view.setText("")
             return
         pdf_view.setDocument(None) # Clear the view
         doc_to_close = self.pdf_doc_orig if is_original else self.pdf_doc_trans
         if doc_to_close:
              doc_to_close.close()
              if is_original:
                  self.pdf_doc_orig = None
              else:
                  self.pdf_doc_trans = None

    # --- PDF视图同步方法 (仅缩放) ---
    def connect_view_sync(self):
        if not PDF_MODULE_AVAILABLE: return
        # 先尝试断开连接，确保在尝试连接之前标志为False
        self.disconnect_view_sync()
        
        print("Connecting view sync (Zoom Only)...")
        try:
            # 连接信号以实现缩放同步
            self.ui.pdf_view_orig.zoomFactorChanged.connect(self.sync_orig_to_trans_zoom)
            self.ui.pdf_view_trans.zoomFactorChanged.connect(self.sync_trans_to_orig_zoom)
            self.zoom_sync_connected = True
            print("Connected zoom synchronization.")
        except AttributeError as e:
            print(f"Could not connect zoom sync (AttributeError): {e}")
            self.zoom_sync_connected = False
        except Exception as e:
            print(f"Error connecting zoom sync: {e}")
            self.zoom_sync_connected = False

    def disconnect_view_sync(self):
        """断开所有视图同步信号"""
        if not PDF_MODULE_AVAILABLE: return
        
        if not self.zoom_sync_connected: # 仅当我们认为它们已连接时才尝试断开连接
            # print("Zoom sync was not marked as connected, skipping disconnect attempt.")
            return

        # print("Attempting to disconnect view sync (zoom only)...")
        try:
            if hasattr(self.ui, 'pdf_view_orig') and self.ui.pdf_view_orig:
                try:
                    self.ui.pdf_view_orig.zoomFactorChanged.disconnect(self.sync_orig_to_trans_zoom)
                except RuntimeError: # 特定槽未连接
                    # print("Debug: sync_orig_to_trans_zoom was not connected to pdf_view_orig or already disconnected.")
                    pass 
            if hasattr(self.ui, 'pdf_view_trans') and self.ui.pdf_view_trans:
                try:
                    self.ui.pdf_view_trans.zoomFactorChanged.disconnect(self.sync_trans_to_orig_zoom)
                except RuntimeError: # 特定槽未连接
                    # print("Debug: sync_trans_to_orig_zoom was not connected to pdf_view_trans or already disconnected.")
                    pass
        except AttributeError as e:
            # 这可能会捕获pdf_view_orig/trans本身是否为None或没有zoomFactorChanged的情况
            print(f"AttributeError during view sync disconnection: {e}")
        except Exception as e:
            # 捕获断开连接逻辑期间的任何其他意外错误
            print(f"Unexpected error disconnecting view sync: {e}")
        finally:
            self.zoom_sync_connected = False # 尝试断开连接后始终设置为false
            # print("Set zoom_sync_connected to False.")

    def sync_orig_to_trans_zoom(self, zoom_factor):
        """将缩放从原始视图同步到翻译视图"""
        if self.ui.sync_zoom.isChecked() and hasattr(self.ui, 'pdf_view_trans'):
            self.ui.pdf_view_trans.syncZoom(zoom_factor)
            # 更新缩放级别显示
            if hasattr(self.ui, 'zoom_level_input') and self.ui.zoom_level_input:
                zoom_percentage = int(zoom_factor * 100)
                self.ui.zoom_level_input.setText(f"{zoom_percentage}%")

    def sync_trans_to_orig_zoom(self, zoom_factor):
        """将缩放从翻译视图同步到原始视图"""
        if self.ui.sync_zoom.isChecked() and hasattr(self.ui, 'pdf_view_orig'):
            self.ui.pdf_view_orig.syncZoom(zoom_factor)
            # 更新缩放级别显示
            if hasattr(self.ui, 'zoom_level_input') and self.ui.zoom_level_input:
                zoom_percentage = int(zoom_factor * 100)
                self.ui.zoom_level_input.setText(f"{zoom_percentage}%")

    def toggle_sync_zoom(self, state):
        """切换缩放同步"""
        if state == Qt.Checked:
            self.connect_view_sync()
        else:
            self.disconnect_view_sync()

    def toggle_sync_scroll(self, state):
        """切换同步滚动功能"""
        if hasattr(self, 'pdf_doc_orig') and self.pdf_doc_orig:
            if state == Qt.Checked:
                # 启用同步滚动
                self.ui.pdf_view_orig.verticalScrollBar().valueChanged.connect(self._sync_scroll_orig_to_trans)
                self.ui.pdf_view_trans.verticalScrollBar().valueChanged.connect(self._sync_scroll_trans_to_orig)
            else:
                # 禁用同步滚动
                try:
                    self.ui.pdf_view_orig.verticalScrollBar().valueChanged.disconnect(self._sync_scroll_orig_to_trans)
                    self.ui.pdf_view_trans.verticalScrollBar().valueChanged.disconnect(self._sync_scroll_trans_to_orig)
                except:
                    pass

    def _sync_scroll_orig_to_trans(self, value):
        """从原文同步滚动到译文"""
        if self.sync_scroll and self.sync_scroll.isChecked():
            self.ui.pdf_view_trans.verticalScrollBar().setValue(value)

    def _sync_scroll_trans_to_orig(self, value):
        """从译文同步滚动到原文"""
        if self.sync_scroll and self.sync_scroll.isChecked():
            self.ui.pdf_view_orig.verticalScrollBar().setValue(value)

    def zoom_in_preview(self):
        """放大预览"""
        if hasattr(self, 'pdf_doc_orig') and self.pdf_doc_orig:
            current_zoom = self.ui.pdf_view_orig.zoomFactor()
            new_zoom = min(current_zoom * 1.2, 5.0)  # 限制最大缩放到 500%
            self._update_zoom(new_zoom)

    def zoom_out_preview(self):
        """缩小预览"""
        if hasattr(self, 'pdf_doc_orig') and self.pdf_doc_orig:
            current_zoom = self.ui.pdf_view_orig.zoomFactor()
            new_zoom = max(current_zoom / 1.2, 0.1)  # 限制最小缩放到 10%
            self._update_zoom(new_zoom)

    def _update_zoom(self, zoom_factor):
        """更新缩放级别"""
        if not hasattr(self, 'pdf_doc_orig') or not self.pdf_doc_orig:
            return

        # 更新缩放级别显示
        zoom_percentage = int(zoom_factor * 100)
        if hasattr(self.ui, 'zoom_level_input') and self.ui.zoom_level_input:
            self.ui.zoom_level_input.setText(f"{zoom_percentage}%")

        # 设置原文PDF的缩放
        if self.ui.pdf_view_orig.zoomMode() != self.ui.pdf_view_orig.ZoomMode.Custom:
            self.ui.pdf_view_orig.setZoomMode(self.ui.pdf_view_orig.ZoomMode.Custom)
        self.ui.pdf_view_orig.setZoomFactor(zoom_factor)

        # 如果启用了同步缩放，也设置译文PDF的缩放
        if self.sync_zoom and self.sync_zoom.isChecked() and hasattr(self, 'pdf_doc_trans') and self.pdf_doc_trans:
            if self.ui.pdf_view_trans.zoomMode() != self.ui.pdf_view_trans.ZoomMode.Custom:
                self.ui.pdf_view_trans.setZoomMode(self.ui.pdf_view_trans.ZoomMode.Custom)
            self.ui.pdf_view_trans.setZoomFactor(zoom_factor)

    def toggle_options_enabled(self, checked):
        """ 根据复选框状态启用/禁用选项组内的小部件。 """
        # 在尝试设置启用状态之前确保小部件存在
        if hasattr(self.ui, 'page_input') and self.ui.page_input:
            self.ui.page_input.setEnabled(checked)
        if hasattr(self.ui, 'thread_spinbox') and self.ui.thread_spinbox:
            self.ui.thread_spinbox.setEnabled(checked)
        # （可选）在禁用时更改组框内容区域的视觉样式
        # 这可能需要更复杂的QSS或遍历子小部件的样式

    def apply_manual_zoom(self):
        """应用在QLineEdit中手动输入的缩放级别。"""
        if not (hasattr(self.ui, 'zoom_level_input') and self.ui.zoom_level_input):
            return

        current_text = self.ui.zoom_level_input.text().strip()
        current_zoom_factor = self.ui.pdf_view_orig.zoomFactor() # 获取当前因子用于回退

        try:
            # 如果存在"%"，则删除并转换为浮点数
            if current_text.endswith('%'):
                value = float(current_text[:-1])
            else:
                value = float(current_text)
            
            if not (10 <= value <= 500): # 缩放百分比范围：10% 至 500%
                raise ValueError("Zoom percentage out of range (10-500)")

            new_zoom_factor = value / 100.0
            self._update_zoom(new_zoom_factor)

        except ValueError as e:
            # 输入无效，恢复到当前缩放显示或显示错误
            print(f"Invalid zoom input: {current_text}. Error: {e}")
            # 将QLineEdit中的文本恢复为当前实际缩放级别
            self.ui.zoom_level_input.setText(f"{int(current_zoom_factor * 100)}%")
            QMessageBox.warning(self, "无效缩放值", f"请输入10到500之间的数字作为缩放百分比。原始值 '{current_text}' 无效。")

    def toggle_preview_visibility(self, checked):
        """显示或隐藏右侧预览面板和相关控件。"""
        if hasattr(self.ui, 'right_widget'):
            self.ui.right_widget.setVisible(checked)
            # 如果面板变得可见并且之前已折叠，则调整拆分器位置
            if checked and hasattr(self.ui, 'pdf_splitter'):
                # 确保拆分器在隐藏时提供合理的默认大小
                total_width = self.ui.pdf_splitter.width()
                if total_width > 0 : # 检查宽度是否可用
                    sizes = self.ui.pdf_splitter.sizes()
                    if sum(sizes) == 0 or sizes[0] == 0 or sizes[1] == 0: # 如果已折叠或未初始化
                         self.ui.pdf_splitter.setSizes([total_width // 2, total_width // 2])
        
        # 同时也切换预览控制组（缩放控件）的可见性
        if hasattr(self.ui, 'preview_group'):
            self.ui.preview_group.setVisible(checked)

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # 应用自定义样式表
    app.setStyleSheet(APP_STYLESHEET)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())