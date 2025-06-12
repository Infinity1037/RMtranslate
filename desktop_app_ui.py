from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog, 
    QComboBox, QLineEdit, QProgressBar, QCheckBox, QSpinBox, QGroupBox, 
    QStatusBar, QSplitter, QApplication # 需要QApplication来获取样式
)
from PySide6.QtCore import Qt, QSize # 导入QSize用于图标大小设置
from PySide6.QtGui import QIcon, QAction # 导入QIcon用于按钮图标
import os

# 假设desktop_app_widgets在同一目录下
from desktop_app_widgets import ZoomablePdfView 

# service_map在主应用中定义，通过MainWindow实例隐式传递

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setWindowTitle("英文文献翻译器")
        MainWindow.setGeometry(100, 100, 1300, 750)
        
        # 使用应用程序样式获取标准图标
        style = QApplication.style()
        icon_select_file = QIcon(style.standardIcon(style.StandardPixmap.SP_DialogOpenButton))
        icon_select_folder = QIcon(style.standardIcon(style.StandardPixmap.SP_DirOpenIcon))
        icon_start = QIcon(style.standardIcon(style.StandardPixmap.SP_MediaPlay))
        icon_cancel = QIcon(style.standardIcon(style.StandardPixmap.SP_MediaStop))
        icon_open_file = QIcon(style.standardIcon(style.StandardPixmap.SP_FileIcon))
        icon_open_folder = QIcon(style.standardIcon(style.StandardPixmap.SP_DirIcon))
        
        # --- 主窗口部件和布局 --- 
        main_widget = QWidget(MainWindow)
        main_h_layout = QHBoxLayout(main_widget)
        main_h_layout.setContentsMargins(5, 5, 5, 5)
        main_h_layout.setSpacing(10)
        MainWindow.setCentralWidget(main_widget)

        # --- 左侧控制面板 --- 
        control_panel_widget = QWidget()
        control_panel_widget.setFixedWidth(350)
        control_layout = QVBoxLayout(control_panel_widget)
        control_layout.setContentsMargins(10, 10, 10, 10)
        control_layout.setSpacing(12)

        # 文件选择区域
        file_group = QGroupBox("输入文件")
        file_group_layout = QVBoxLayout(file_group)
        file_h_layout = QHBoxLayout()
        self.file_label = QLabel("未选择文件")
        self.file_label.setWordWrap(True)
        select_button = QPushButton(" 选择 PDF 文件")
        select_button.setIcon(icon_select_file)
        self.select_file_button = select_button
        file_h_layout.addWidget(self.file_label, 1)
        file_h_layout.addWidget(select_button)
        file_group_layout.addLayout(file_h_layout)
        control_layout.addWidget(file_group)

        # 输出目录选择区域
        output_group = QGroupBox("输出目录")
        output_group_layout = QVBoxLayout(output_group)
        output_h_layout = QHBoxLayout()
        self.output_dir_label = QLabel(f"{MainWindow.output_dir}")
        self.output_dir_label.setWordWrap(True)
        change_dir_button = QPushButton(" 更改")
        change_dir_button.setIcon(icon_select_folder)
        self.change_dir_button = change_dir_button
        output_h_layout.addWidget(self.output_dir_label, 1)
        output_h_layout.addWidget(change_dir_button)
        output_group_layout.addLayout(output_h_layout)
        control_layout.addWidget(output_group)
        
        # --- 预览窗口可见性切换 --- (现在是一个可选中的QGroupBox)
        self.preview_visibility_group = QGroupBox("预览窗口")
        self.preview_visibility_group.setCheckable(True)
        self.preview_visibility_group.setChecked(True) # 默认为可见/选中状态
        control_layout.addWidget(self.preview_visibility_group)

        # --- 添加预览切换和控制 --- 
        self.preview_group = QGroupBox("")
        preview_group_layout = QVBoxLayout(self.preview_group)
        
        # 预览控制区
        preview_controls_layout = QHBoxLayout()
        preview_controls_layout.setSpacing(10)  # 设置控件之间的间距
        
        # 同步控制（隐藏但可用）
        sync_controls = QWidget()
        sync_layout = QVBoxLayout(sync_controls)
        self.sync_scroll = QCheckBox("")
        self.sync_scroll.setObjectName("syncScroll")
        self.sync_scroll.setChecked(True)
        self.sync_zoom = QCheckBox("")
        self.sync_zoom.setObjectName("syncZoom")
        self.sync_zoom.setChecked(True)
        sync_layout.addWidget(self.sync_scroll)
        sync_layout.addWidget(self.sync_zoom)
        sync_controls.setVisible(False) # 隐藏整个同步控制组件
        preview_controls_layout.addWidget(sync_controls)
        
        # 添加"缩放比例"标签并设置对齐方式
        zoom_label = QLabel("缩放比例")
        zoom_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # 右对齐
        zoom_label.setFixedWidth(70)  # 减小宽度
        preview_controls_layout.addWidget(zoom_label)
        
        # 缩放控制
        zoom_controls = QWidget()
        zoom_layout = QHBoxLayout(zoom_controls)
        zoom_layout.setSpacing(5)  # 设置缩放控件之间的间距
        self.zoom_out = QPushButton("-")
        self.zoom_out.setObjectName("zoomOut")
        self.zoom_level_input = QLineEdit("100%")
        self.zoom_level_input.setObjectName("zoomLevelInput")
        self.zoom_level_input.setFixedWidth(55) # 调整宽度以适应如 "100%" 或 "500%"
        self.zoom_level_input.setAlignment(Qt.AlignCenter)
        self.zoom_in = QPushButton("+")
        self.zoom_in.setObjectName("zoomIn")
        zoom_layout.addWidget(self.zoom_out)
        zoom_layout.addWidget(self.zoom_level_input)
        zoom_layout.addWidget(self.zoom_in)
        preview_controls_layout.addWidget(zoom_controls)
        
        preview_group_layout.addLayout(preview_controls_layout)
        control_layout.addWidget(self.preview_group)
        
        # --- 翻译设置 --- 
        settings_group = QGroupBox("翻译设置")
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setSpacing(8)
        
        # 翻译服务选择
        service_layout = QHBoxLayout()
        service_layout.addWidget(QLabel("翻译服务:"))
        self.service_combo = QComboBox()
        service_layout.addWidget(self.service_combo)
        settings_layout.addLayout(service_layout)

        # 凭证分组框
        self.credentials_group = QGroupBox("服务凭证/设置")
        self.credentials_layout = QVBoxLayout()
        self.credentials_widgets = {}
        self.credentials_group.setLayout(self.credentials_layout)
        self.credentials_group.setVisible(False)
        settings_layout.addWidget(self.credentials_group)

        # 选项分组框
        self.options_group = QGroupBox("翻译选项")
        self.options_group.setCheckable(True)
        self.options_group.setChecked(False)
        options_layout = QVBoxLayout(self.options_group)
        options_layout.setSpacing(6)
        page_layout = QHBoxLayout()
        page_layout.addWidget(QLabel("翻译页码 (e.g., 1-3,5):"))
        self.page_input = QLineEdit()
        page_layout.addWidget(self.page_input)
        options_layout.addLayout(page_layout)
        thread_layout = QHBoxLayout()
        thread_layout.addWidget(QLabel("处理线程数:"))
        self.thread_spinbox = QSpinBox()
        self.thread_spinbox.setMinimum(1)
        self.thread_spinbox.setValue(4)
        self.thread_spinbox.setMaximum(os.cpu_count() or 8)
        thread_layout.addWidget(self.thread_spinbox)
        thread_layout.addStretch()
        options_layout.addLayout(thread_layout)
        settings_layout.addWidget(self.options_group)
        
        control_layout.addWidget(settings_group)
        
        # --- 空白填充区 --- 
        control_layout.addStretch(1)

        # --- 进度条和操作按钮 --- 
        progress_action_group = QWidget()
        progress_action_layout = QVBoxLayout(progress_action_group)
        progress_action_layout.setContentsMargins(0,0,0,0)
        progress_action_layout.setSpacing(8)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        progress_action_layout.addWidget(self.progress_bar)

        # 操作按钮
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)
        self.start_button = QPushButton(" 开始翻译")
        self.start_button.setIcon(icon_start)
        self.cancel_button = QPushButton(" 取消")
        self.cancel_button.setIcon(icon_cancel)
        self.cancel_button.setEnabled(False)
        action_layout.addStretch()
        action_layout.addWidget(self.start_button)
        action_layout.addWidget(self.cancel_button)
        action_layout.addStretch()
        progress_action_layout.addLayout(action_layout)

        # 结果按钮布局
        self.result_buttons_widget = QWidget()
        result_buttons_layout = QHBoxLayout(self.result_buttons_widget)
        result_buttons_layout.setContentsMargins(0, 5, 0, 0)
        result_buttons_layout.setSpacing(10)
        self.open_mono_button = QPushButton(" 打开翻译文件")
        self.open_mono_button.setIcon(icon_open_file)
        self.open_folder_button = QPushButton(" 打开输出文件夹")
        self.open_folder_button.setIcon(icon_open_folder)
        result_buttons_layout.addStretch()
        result_buttons_layout.addWidget(self.open_mono_button)
        result_buttons_layout.addWidget(self.open_folder_button)
        result_buttons_layout.addStretch()
        self.result_buttons_widget.setVisible(False)
        progress_action_layout.addWidget(self.result_buttons_widget)
        
        control_layout.addWidget(progress_action_group)

        # --- 右侧预览面板 --- 
        self.right_widget = QWidget()
        preview_layout = QVBoxLayout(self.right_widget)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        # 水平分割器，用于两个PDF视图
        self.pdf_splitter = QSplitter(Qt.Horizontal)

        # 原始PDF视图
        self.pdf_view_orig = ZoomablePdfView()
        self.pdf_splitter.addWidget(self.pdf_view_orig)

        # 翻译后的PDF视图
        self.pdf_view_trans = ZoomablePdfView()
        self.pdf_splitter.addWidget(self.pdf_view_trans)

        # 连接滚动同步
        self.pdf_view_orig.scrollPositionChanged.connect(self.pdf_view_trans.syncScroll)
        self.pdf_view_trans.scrollPositionChanged.connect(self.pdf_view_orig.syncScroll)

        preview_layout.addWidget(self.pdf_splitter)

        # --- 将面板添加到主布局 --- 
        main_h_layout.addWidget(control_panel_widget)
        main_h_layout.addWidget(self.right_widget, 1)

        # --- 状态栏 --- 
        self.status_bar = QStatusBar()
        MainWindow.setStatusBar(self.status_bar)
        
        # --- 连接信号（延迟到MainWindow.__init__中） ---
        self.retranslateUi(MainWindow)

    def retranslateUi(self, MainWindow):
        # 更新工具提示或其他可翻译的字符串（如需要）
        self.select_file_button.setToolTip("选择要翻译的本地 PDF 文件")
        self.change_dir_button.setToolTip("选择翻译结果保存的文件夹")
        self.start_button.setToolTip("根据当前设置开始翻译选定的 PDF 文件")
        self.cancel_button.setToolTip("取消当前正在进行的翻译任务")
        pass 