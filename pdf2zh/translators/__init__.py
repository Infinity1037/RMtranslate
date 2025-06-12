from .base import BaseTranslator, remove_control_characters
from .traditional_api import (
    GoogleTranslator,
    BingTranslator,
    DeepLTranslator,
    DeepLXTranslator,
    AzureTranslator,
    TencentTranslator,
    BaiduTranslator,
    ArgosTranslator,
)

__all__ = [
    "BaseTranslator",
    "remove_control_characters",
    # 传统API翻译器
    "GoogleTranslator",
    "BingTranslator",
    "DeepLTranslator",
    "DeepLXTranslator",
    "AzureTranslator",
    "TencentTranslator",
    "BaiduTranslator",
    "ArgosTranslator",
] 