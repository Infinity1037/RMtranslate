import html
import re
import hashlib
import random
import logging
import requests
import deepl
from azure.ai.translation.text import TextTranslationClient
from azure.core.credentials import AzureKeyCredential
from tencentcloud.common import credential
from tencentcloud.tmt.v20180321.models import (
    TextTranslateRequest,
    TextTranslateResponse,
)
from tencentcloud.tmt.v20180321.tmt_client import TmtClient

from .base import BaseTranslator, remove_control_characters

logger = logging.getLogger(__name__)

class GoogleTranslator(BaseTranslator):
    name = "google"
    lang_map = {"zh": "zh-CN"}

    def __init__(self, lang_in, lang_out, model, ignore_cache=False, **kwargs):
        super().__init__(lang_in, lang_out, model, ignore_cache)
        self.session = requests.Session()
        self.endpoint = "https://translate.google.com/m"
        self.headers = {
            "User-Agent": "Mozilla/4.0 (compatible;MSIE 6.0;Windows NT 5.1;SV1;.NET CLR 1.1.4322;.NET CLR 2.0.50727;.NET CLR 3.0.04506.30)"  # noqa: E501
        }

    def do_translate(self, text):
        text = text[:5000]  # 谷歌翻译最大长度限制
        try:
            response = self.session.get(
                self.endpoint,
                params={"tl": self.lang_out, "sl": self.lang_in, "q": text},
                headers=self.headers,
                timeout=10 # 添加超时设置
            )
            response.raise_for_status() # 对于错误响应(4xx或5xx)抛出HTTPError
            re_result = re.findall(
                r'(?s)class="(?:t0|result-container)">(.*?)<', response.text
            )
            if not re_result:
                 # 可能HTML结构已更改，记录响应以便调试
                 logger.warning(f"无法解析谷歌翻译响应，文本: '{text[:50]}...' 响应内容: {response.text[:500]}")
                 raise ValueError("无法解析谷歌翻译响应")

            result = html.unescape(re_result[0])
            return remove_control_characters(result)

        except requests.exceptions.Timeout:
            logger.error("谷歌翻译请求超时。")
            raise
        except requests.exceptions.RequestException as e:
             logger.error(f"谷歌翻译请求失败: {e}")
             raise
        except Exception as e:
            logger.error(f"谷歌翻译过程中出错: {e}")
            raise # 重新抛出其他异常

class BingTranslator(BaseTranslator):
    # https://github.com/immersive-translate/old-immersive-translate/blob/6df13da22664bea2f51efe5db64c63aca59c4e79/src/background/translationService.js
    name = "bing"
    lang_map = {"zh": "zh-Hans"}

    def __init__(self, lang_in, lang_out, model, ignore_cache=False, **kwargs):
        super().__init__(lang_in, lang_out, model, ignore_cache)
        self.session = requests.Session()
        self.endpoint = "https://www.bing.com/translator"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",  # noqa: E501
            "Referer": "https://www.bing.com/translator",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.sid_data = None

    def find_sid(self):
        if self.sid_data:
            return self.sid_data
        try:
            response = self.session.get(self.endpoint, headers=self.headers, timeout=10)
            response.raise_for_status()
            url = response.url # 使用重定向后的最终URL
            ig = re.findall(r'IG:"([A-Fa-f0-9]+)"', response.text)[0]
            iid = re.findall(r'data-iid="(translator\.)(((?!\.).)+)"', response.text)[0][0]
            key_token_match = re.findall(r'params_AbusePreventionHelper\s?=\s?\[([0-9]+),\"([^\"]+)\",', response.text)
            if not key_token_match:
                 raise ValueError("无法找到必应翻译的密钥和令牌")
            key, token = key_token_match[0]

            self.sid_data = (url, ig, iid, key, token)
            return self.sid_data
        except requests.exceptions.Timeout:
             logger.error("必应翻译SID请求超时。")
             raise
        except requests.exceptions.RequestException as e:
            logger.error(f"必应翻译SID请求失败: {e}")
            raise
        except IndexError as e:
            logger.error(f"无法解析必应SID页面结构: {e}. 响应: {response.text[:500]}")
            raise ValueError("无法解析必应SID页面结构") from e
        except Exception as e:
            logger.error(f"寻找必应SID时出错: {e}")
            raise

    def do_translate(self, text):
        text = text[:1000]  # 必应翻译最大长度限制
        try:
            url, ig, iid, key, token = self.find_sid()
            translate_url = f"{url.split('/translator')[0]}/ttranslatev3?isVertical=1&=&IG={ig}&IID={iid}"

            response = self.session.post(
                translate_url,
                data={
                    "fromLang": self.lang_in,
                    "to": self.lang_out,
                    "text": text,
                    "token": token,
                    "key": str(key), # 确保key是字符串类型
                },
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            result_json = response.json()
            if isinstance(result_json, list) and len(result_json) > 0 and "translations" in result_json[0]:
                 return result_json[0]["translations"][0]["text"]
            else:
                 logger.warning(f"意外的必应翻译响应格式: {result_json}")
                 raise ValueError("意外的必应翻译响应格式")
        except requests.exceptions.Timeout:
             logger.error("必应翻译请求超时。")
             self.sid_data = None # 超时时重置SID
             raise
        except requests.exceptions.RequestException as e:
            logger.error(f"必应翻译请求失败: {e}")
            self.sid_data = None # 失败时重置SID
            raise
        except Exception as e:
            logger.error(f"必应翻译过程中出错: {e}")
            self.sid_data = None # 其他错误时重置SID
            raise

class DeepLTranslator(BaseTranslator):
    # https://github.com/DeepLcom/deepl-python
    name = "deepl"
    envs = {
        "DEEPL_AUTH_KEY": None,
        "DEEPL_SERVER_URL": None, # 可选：用于自定义端点（如deeplx）
    }
    lang_map = {"zh": "ZH"} # DeepL使用ZH表示简体中文

    def __init__(
        self, lang_in, lang_out, model, envs=None, ignore_cache=False, **kwargs
    ):
        self.set_envs(envs)
        super().__init__(lang_in, lang_out, model, ignore_cache)
        auth_key = self.envs["DEEPL_AUTH_KEY"]
        server_url = self.envs.get("DEEPL_SERVER_URL") # 使用.get获取可选环境变量
        if not auth_key:
            raise ValueError("需要DeepL认证密钥(DEEPL_AUTH_KEY)。")
        self.client = deepl.Translator(auth_key, server_url=server_url)

    def do_translate(self, text):
        try:
            # 如果需要，将zh-Hans映射到ZH（虽然lang_map应该已处理）
            target_lang = self.lang_out.upper()
            if target_lang == 'ZH-HANS':
                target_lang = 'ZH'
            source_lang = self.lang_in.upper() if self.lang_in else None

            response = self.client.translate_text(
                text,
                source_lang=source_lang,
                target_lang=target_lang,
                # 如果需要，可以在此添加正式性选项等
            )
            return response.text
        except deepl.DeepLException as e:
            logger.error(f"DeepL API错误: {e}")
            raise
        except Exception as e:
            logger.error(f"DeepL翻译过程中出错: {e}")
            raise

class DeepLXTranslator(BaseTranslator):
    # 使用自托管或公共DeepLX实例
    name = "deeplx"
    envs = {
        "DEEPLX_ENDPOINT": "http://127.0.0.1:1188/translate", # 默认为本地
        "DEEPLX_ACCESS_TOKEN": None,
    }
    lang_map = {"zh": "ZH"} # DeepL使用ZH表示简体中文

    def __init__(
        self, lang_in, lang_out, model, envs=None, ignore_cache=False, **kwargs
    ):
        self.set_envs(envs)
        super().__init__(lang_in, lang_out, model, ignore_cache)
        self.endpoint = self.envs["DEEPLX_ENDPOINT"]
        self.access_token = self.envs.get("DEEPLX_ACCESS_TOKEN") # 可选令牌
        self.session = requests.Session()

    def do_translate(self, text):
        try:
            # 如果需要，将zh-Hans映射到ZH
            target_lang = self.lang_out.upper()
            if target_lang == 'ZH-HANS':
                target_lang = 'ZH'
            source_lang = self.lang_in.upper() if self.lang_in else "AUTO"

            payload = {
                "text": text,
                "source_lang": source_lang,
                "target_lang": target_lang,
            }
            headers = {}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            
            response = self.session.post(self.endpoint, json=payload, timeout=20) # 增加超时时间
            response.raise_for_status()
            
            result = response.json()
            if "data" in result:
                return result["data"]
            else:
                logger.warning(f"意外的DeepLX响应格式: {result}")
                raise ValueError("意外的DeepLX响应格式")
        except requests.exceptions.RequestException as e:
            logger.error(f"DeepLX请求失败: {e}")
            raise
        except Exception as e:
            logger.error(f"DeepLX翻译过程中出错: {e}")
            raise

class AzureTranslator(BaseTranslator):
    # https://github.com/Azure/azure-sdk-for-python
    name = "azure"
    envs = {
        "AZURE_ENDPOINT": "https://api.cognitive.microsofttranslator.com", # 全球端点
        #"AZURE_ENDPOINT": "https://api.translator.azure.cn", # 中国端点
        "AZURE_API_KEY": None,
        "AZURE_REGION": None, # SDK需要
    }
    lang_map = {"zh": "zh-Hans"}

    def __init__(
        self, lang_in, lang_out, model, envs=None, ignore_cache=False, **kwargs
    ):
        self.set_envs(envs)
        super().__init__(lang_in, lang_out, model, ignore_cache)
        api_key = self.envs["AZURE_API_KEY"]
        endpoint = self.envs["AZURE_ENDPOINT"]
        region = self.envs["AZURE_REGION"]
        if not api_key:
            raise ValueError("需要Azure API密钥(AZURE_API_KEY)。")
        if not endpoint:
            raise ValueError("需要Azure终端点(AZURE_ENDPOINT)。")
        if not region:
            raise ValueError("需要Azure区域(AZURE_REGION)。")
        self.client = TextTranslationClient(endpoint=endpoint,
                                     credential=AzureKeyCredential(api_key))
        self.region = region

    def do_translate(self, text) -> str:
        try:
            # 使用TextTranslationClient
            # 注意：凭证可能会根据端点略有不同（全球与区域）
            response = self.client.translate(
                content=[text],
                source_language=self.lang_in,
                target_languages=[self.lang_out],
                region=self.region
            )
            if response and len(response) > 0 and len(response[0].translations) > 0:
                return response[0].translations[0].text
            else:
                logger.warning("没有从Azure收到翻译。")
                raise ValueError("没有从Azure收到翻译。")
        except Exception as e:
            logger.error(f"Azure翻译过程中出错: {e}")
            raise

class TencentTranslator(BaseTranslator):
    # https://github.com/TencentCloud/tencentcloud-sdk-python
    name = "tencent"
    envs = {
        "TENCENT_SECRET_ID": None,
        "TENCENT_SECRET_KEY": None,
        "TENCENT_REGION": "ap-shanghai",  # 默认区域
    }
    # 腾讯语言映射似乎兼容，除非出现问题，否则不需要显式映射

    def __init__(
        self, lang_in, lang_out, model, envs=None, ignore_cache=False, **kwargs
    ):
        self.set_envs(envs)
        super().__init__(lang_in, lang_out, model, ignore_cache)
        secret_id = self.envs["TENCENT_SECRET_ID"]
        secret_key = self.envs["TENCENT_SECRET_KEY"]
        region = self.envs["TENCENT_REGION"]
        if not secret_id or not secret_key:
            raise ValueError("需要腾讯云Secret ID和Secret Key。")
        cred = credential.Credential(secret_id, secret_key)
        self.client = TmtClient(cred, region)

    def do_translate(self, text):
        try:
            req = TextTranslateRequest()
            req.SourceText = text
            req.Source = self.lang_in
            req.Target = self.lang_out
            req.ProjectId = 0 # 默认项目ID
            
            resp = self.client.TextTranslate(req)
            
            # 如果需要，检查错误响应结构
            # if isinstance(resp, AbstractModel) and hasattr(resp, 'Error'):
            #     # 处理API错误
            #     pass
            
            return resp.TargetText
        except Exception as e:
            # 记录腾讯云SDK异常详情（如果可用）
            logger.error(f"腾讯云翻译错误: {e}")
            raise

class BaiduTranslator(BaseTranslator):
    # https://fanyi-api.baidu.com/doc/21
    name = "baidu"
    envs = {
        "BAIDU_APP_ID": None,
        "BAIDU_SECRET_KEY": None,
    }
    lang_map = {
        "zh": "zh", # 百度使用'zh'表示简体中文
        # 根据百度文档需要添加其他映射
    }

    def __init__(
        self, lang_in, lang_out, model, envs=None, ignore_cache=False, **kwargs
    ):
        self.set_envs(envs)
        # 使用百度特定的语言映射
        temp_lang_in = self.lang_map.get(lang_in.lower(), lang_in)
        temp_lang_out = self.lang_map.get(lang_out.lower(), lang_out)
        
        # 使用可能已映射的语言重新初始化BaseTranslator
        super().__init__(temp_lang_in, temp_lang_out, model, ignore_cache)
        
        self.app_id = self.envs["BAIDU_APP_ID"]
        self.secret_key = self.envs["BAIDU_SECRET_KEY"]
        if not self.app_id or not self.secret_key:
            raise ValueError("需要百度APP ID和密钥")
        
        self.session = requests.Session()
        self.endpoint = "https://fanyi-api.baidu.com/api/trans/vip/translate"

    def make_md5(self, s, encoding='utf-8'):
        return hashlib.md5(s.encode(encoding)).hexdigest()

    def do_translate(self, text: str) -> str:
        try:
            salt = random.randint(32768, 65536)
            sign = self.make_md5(self.app_id + text + str(salt) + self.secret_key)
            
            params = {
                "appid": self.app_id,
                "q": text,
                "from": self.lang_in, # 使用可能已映射的lang_in
                "to": self.lang_out,   # 使用可能已映射的lang_out
                "salt": salt,
                "sign": sign
            }
            
            response = self.session.get(
                self.endpoint, 
                params=params, 
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            
            if "error_code" in result:
                # 你可能想将错误代码映射到更具体的异常
                error_msg = f"百度API错误: {result.get('error_code')}, {result.get('error_msg', '')}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            if "trans_result" in result and len(result["trans_result"]) > 0:
                return result["trans_result"][0]["dst"]
            else:
                raise ValueError(f"百度返回了无效的翻译结果: {result}")
        except Exception as e:
            logger.error(f"百度翻译过程中出错: {e}")
            raise

class ArgosTranslator(BaseTranslator):
    name = "argos"
    # Argos使用标准ISO 639-1代码（例如'en', 'zh'）
    # lang_map = {} # 通常不需要特定映射

    def __init__(self, lang_in, lang_out, model, ignore_cache=False, **kwargs):
        super().__init__(lang_in, lang_out, model, ignore_cache)
        try:
            import argostranslate.package
            import argostranslate.translate

            # 查找已安装的语言
            from_lang = argostranslate.translate.get_language_from_code(self.lang_in)
            to_lang = argostranslate.translate.get_language_from_code(self.lang_out)
            
            package = from_lang.get_translation(to_lang)
            if not package:
                 # 可选：尝试安装包？
                 # argostranslate.package.update_package_index()
                 # available_packages = argostranslate.package.get_available_packages()
                 # package_to_install = next(filter(...))
                 # argostranslate.package.install_from_path(package_to_install.download())
                 raise ValueError(f"从{self.lang_in}到{self.lang_out}的Argos翻译包不可用")
            
            self.translator = package
        except ImportError:
            logger.error("无法导入argostranslate，请使用pip install argostranslate安装它。")
            raise ValueError("缺少argostranslate包")
        except Exception as e:
            logger.error(f"初始化Argos翻译器时出错: {e}")
            raise

    def translate(self, text: str, ignore_cache: bool = False):
        # 加载翻译模型
        if not hasattr(self, 'translator') or not self.translator:
            logger.error("未能正确初始化Argos翻译器")
            raise ValueError("未能正确初始化Argos翻译器")
        
        # 覆盖translate方法来处理潜在的句子分割（如果需要）
        return super().translate(text, ignore_cache)

    def do_translate(self, text: str) -> str:
        try:
            # 翻译
            result = self.translator.translate(text)
            return result
        except Exception as e:
            # 捕获可能的CTranslate2异常（如果使用该后端）
            logger.error(f"Argos翻译过程中出错: {e}")
            raise 