import os
import asyncio
from asyncio import CancelledError
from PySide6.QtCore import QThread, Signal

# 导入核心翻译函数 - 如需要可调整路径
from pdf2zh.high_level import translate

class TranslationWorker(QThread):
    """ 用于运行翻译任务的工作线程 """
    progress = Signal(int, str)  # 进度百分比和描述信息
    finished = Signal(bool, str)  # 成功状态(布尔值)和仅单语言输出路径
    error = Signal(str)  # 错误信息

    def __init__(self, params):
        super().__init__()
        self.params = params
        # 确保取消事件被正确创建和传递
        if 'cancellation_event' not in self.params or not isinstance(self.params['cancellation_event'], asyncio.Event):
             self.params['cancellation_event'] = asyncio.Event()
        self.cancellation_event = self.params['cancellation_event']

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
            # 记录完整的堆栈跟踪以便更好地调试
            import traceback
            print(f"工作线程中的错误: {e}\n{traceback.format_exc()}")
            self.error.emit(f"翻译出错: {e}") # 向用户提供错误信息
            self.finished.emit(False, "") # 错误时不返回路径

    def stop(self):
        print("尝试通过设置取消事件来停止工作线程...")
        if self.cancellation_event:
             self.cancellation_event.set() 