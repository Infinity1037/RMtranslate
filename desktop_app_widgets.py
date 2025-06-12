from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtCore import Qt, Signal

# 尝试导入必要的PDF模块
try:
    from PySide6.QtPdfWidgets import QPdfView
    from PySide6.QtPdf import QPdfDocument
    PDF_MODULE_AVAILABLE = True

    # --- 自定义可缩放PDF视图组件 --- 
    class ZoomablePdfView(QPdfView):
        # 当滚动位置改变时发出的信号
        scrollPositionChanged = Signal(int, int)  # 水平和垂直位置参数
        # 当缩放因子改变时发出的信号
        zoomFactorChanged = Signal(float)  # 缩放因子参数

        def __init__(self, parent=None):
            super().__init__(parent)
            # 设置默认缩放模式（可选）
            self.setZoomMode(QPdfView.ZoomMode.FitInView)
            self.setPageMode(QPdfView.PageMode.MultiPage)
            # 尝试启用点击聚焦
            self.setFocusPolicy(Qt.ClickFocus) 
            
            # 连接滚动条信号
            self.horizontalScrollBar().valueChanged.connect(self._onScrollPositionChanged)
            self.verticalScrollBar().valueChanged.connect(self._onScrollPositionChanged)

        def _onScrollPositionChanged(self, _):
            """内部槽函数，用于发送滚动位置变化信号"""
            h_pos = self.horizontalScrollBar().value()
            v_pos = self.verticalScrollBar().value()
            self.scrollPositionChanged.emit(h_pos, v_pos)

        def syncScroll(self, h_pos, v_pos):
            """与另一个视图同步滚动位置"""
            self.horizontalScrollBar().setValue(h_pos)
            self.verticalScrollBar().setValue(v_pos)

        def wheelEvent(self, event):
            """处理滚轮事件实现缩放功能"""
            modifiers = QApplication.keyboardModifiers()
            
            # 处理Ctrl+滚轮实现缩放功能
            if modifiers & Qt.ControlModifier:
                delta = event.angleDelta().y()
                current_zoom = self.zoomFactor()
                
                # 计算新的缩放因子
                if delta > 0:
                    new_zoom = min(current_zoom * 1.1, 5.0)  # 放大，最大500%
                else:
                    new_zoom = max(current_zoom / 1.1, 0.1)  # 缩小，最小10%
                
                # 应用缩放
                self.setZoomMode(QPdfView.ZoomMode.Custom)
                self.setZoomFactor(new_zoom)
                
                # 发送缩放因子变化信号
                self.zoomFactorChanged.emit(new_zoom)
                
                event.accept()
                return
            
            # 处理Shift+滚轮实现水平滚动
            elif modifiers & Qt.ShiftModifier:
                h_scrollbar = self.horizontalScrollBar()
                if h_scrollbar:
                    delta = event.angleDelta().y()
                    current_value = h_scrollbar.value()
                    step = delta // 2
                    new_value = current_value - step
                    new_value = max(h_scrollbar.minimum(), min(new_value, h_scrollbar.maximum()))
                    
                    if new_value != current_value:
                        h_scrollbar.setValue(new_value)
                        event.accept()
                        return
            
            # 默认滚轮行为：垂直滚动
            super().wheelEvent(event)

        def syncZoom(self, zoom_factor):
            """与另一个视图同步缩放因子"""
            if abs(self.zoomFactor() - zoom_factor) > 1e-5:
                self.setZoomMode(QPdfView.ZoomMode.Custom)
                self.setZoomFactor(zoom_factor)
                # 发送缩放因子变化信号
                self.zoomFactorChanged.emit(zoom_factor)
                self.update()

except ImportError:
    print("Warning: PySide6.QtPdfWidgets or PySide6.QtPdf not found.")
    print("PDF preview functionality will be disabled.")
    print("Try installing with: pip install PySide6-Addons")
    PDF_MODULE_AVAILABLE = False
    QPdfDocument = None # 为了在其他地方进行类型检查，将QPdfDocument定义为None
    QPdfView = None # 为了在其他地方进行类型检查，将QPdfView定义为None

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
         def syncScroll(self, h_pos, v_pos): pass # 添加虚拟的syncScroll方法 