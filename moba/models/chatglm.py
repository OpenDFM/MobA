import pdb
import time
from abc import abstractmethod
import re
import sys
import json
sys.path.append("../..")  # Add the path to the project to the sys.path, in case you want to test this script independently

import requests

from moba.utils.utils import print_with_color, encode_image_base64, encode_image_PIL
from moba.prompts.prompts import *

from moba.utils.config import load_config

from moba.models.base import BaseModel
from zhipuai import ZhipuAI

configs = load_config()


class ChatGLMModel(BaseModel):
    def __init__(self, model, configs, model_type):
        super().__init__()
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "OPEN_APP",
                    "description": "根据传进来的app名字，打开对应的app",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "package_name": {
                                "description": "app名字",
                                "type": "string",
                            }
                        },
                        "required": ["package_name"]
                    },
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "CLOSE_APP",
                    "description": "根据传进来的app名字，关闭对应的app",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "package_name": {
                                "description": "app名字",
                                "type": "string",
                            }
                        },
                        "required": ["package_name"]
                    },
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "CLICK",
                    "description": "根据传进来的索引，点击对应的屏幕部分",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "element_index": {
                                "description": "索引",
                                "type": "int",
                            }
                        },
                        "required": ["element_index"]
                    },
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "CLICK_BY_COORDINATE",
                    "description": "根据传进来的坐标，点击屏幕对应的位置",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "x": {
                                "description": "横坐标",
                                "type": "int",
                            },
                            "y": {
                                "description": "纵坐标",
                                "type": "int",
                            }
                        },
                        "required": ["x", "y"]
                    },
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "DOUBLE_CLICK",
                    "description": "根据传进来的索引，双击对应的屏幕部分",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "element_index": {
                                "description": "索引",
                                "type": "int",
                            }
                        },
                        "required": ["element_index"]
                    },
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "LONG_PRESS",
                    "description": "根据传进来的索引，长按对应的屏幕部分",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "element_index": {
                                "description": "索引",
                                "type": "int",
                            }
                        },
                        "required": ["element_index"]
                    },
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "BOX_INPUT",
                    "description": "在屏幕给定的索引部分里面，输入给定的文本内容",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "element_index": {
                                "description": "索引",
                                "type": "int",
                            },
                            "text": {
                                "description": "索引",
                                "type": "str",
                            },
                        },
                        "required": ["element_index", "text"]
                    },
                }
            },
        ]
        self.api_key = configs["ZHIPU_API_KEY"]
        self.client = ZhipuAI(api_key=self.api_key)
        self.tokens = {
            "prompt_tokens": 0,
            "completion_tokens": 0
        }
        self.price = configs['PRICE'].get(model, [0.01, 0.03])
        self.max_image_size = configs["MAX_IMAGE_SIZE"]
        self.model_type = model_type

    def calulate_useage(self, response):
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        self.tokens["prompt_tokens"] += prompt_tokens
        self.tokens["completion_tokens"] += completion_tokens
        print(f"[{self.model_type}] Prompt tokens: {prompt_tokens}, Completion tokens: {completion_tokens}, Cost: ${'{0:.3f}'.format(prompt_tokens / 1000 * self.price[0] + completion_tokens / 1000 * self.price[1])}")

    def calulate_useage_total(self):
        print(
            f"[{self.model_type}] Total prompt tokens: {self.tokens['prompt_tokens']}, Total completion tokens: {self.tokens['completion_tokens']}, Total cost: ${'{0:.3f}'.format(self.tokens['prompt_tokens'] / 1000 * self.price[0] + self.tokens['completion_tokens'] / 1000 * self.price[1])}")

    def OPEN_APP(self, package_name: str):
        return ["OPEN_APP", package_name]

    def CLOSE_APP(self, package_name: str):
        return ["CLOSE_APP", package_name]

    def CLICK(self, element_index: int):
        return ["CLICK", int(element_index)]

    def CLICK_BY_COORDINATE(self, x: int, y: int):
        return ["CLICK_BY_COORDINATE", x, y]

    def DOUBLE_CLICK(self, element_index: int):
        return ["DOUBLE_CLICK", element_index]

    def LONG_PRESS(self, element_index: int):
        return ["LONG_PRESS", element_index]

    def BOX_INPUT(self, element_index: int, text: str):
        return ["BOX_INPUT", element_index, text]

    def parse_function_call(self, model_response):
        # 处理函数调用结果，根据模型返回参数，调用对应的函数。
        # 调用函数返回结果后构造tool message，再次调用模型，将函数结果输入模型
        # 模型会将函数调用结果以自然语言格式返回给用户。
        if model_response.choices[0].message.tool_calls:
            tool_call = model_response.choices[0].message.tool_calls[0]
            args = tool_call.function.arguments
            function_result = {}
            match tool_call.function.name:
                case "OPEN_APP":
                    function_result = self.OPEN_APP(**json.loads(args))
                case "CLOSE_APP":
                    function_result = self.CLOSE_APP(**json.loads(args))
                case "CLICK":
                    function_result = self.CLICK(**json.loads(args))
                case "CLICK_BY_COORDINATE":
                    function_result = self.CLICK_BY_COORDINATE(**json.loads(args))
                case "DOUBLE_CLICK":
                    function_result = self.DOUBLE_CLICK(**json.loads(args))
                case "LONG_PRESS":
                    function_result = self.LONG_PRESS(**json.loads(args))
                case "BOX_INPUT":
                    function_result = self.BOX_INPUT(**json.loads(args))

            return function_result




    def prepare_inputs(self, text, image_list):
        messages = []

        if image_list:
            user_message = {
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": text
                }, ]
            }
            for image_path in image_list:
                base64_image = encode_image_base64(image_path, max_size=self.max_image_size)
                user_message["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"  # , "detail": "auto"
                    },
                }, )
            messages.append(user_message)
        else:
            messages.append({
                "role": "user",
                "content": text
            }, )
        return messages

    def generate_embedding(self, text):
        url = "https://api.xi-ai.cn/v1/embeddings"
        json_dict = {
            "model": "text-embedding-3-small",
            "input": text
        }
        i = 0
        MAX_RETRY = configs["API_MAX_TRY"]
        while i < MAX_RETRY:
            try:
                response_ = requests.post(url, json=json_dict, headers=self.header)
                response_ = response_.json()
                response = response_["data"][0]["embedding"]
                self.calulate_useage(response_)
            except KeyboardInterrupt:
                raise Exception("Terminated by user.")
            except Exception as e:
                try:
                    print(e)
                    error = response_["error"]["message"].split("(request id:")[0].strip()
                    print_with_color(error, "red")
                    print(response_.json())
                except:
                    pass
                i += 1
                time.sleep(1 + i)
                print_with_color(f"Failed to get response. Retry {i} times.", "yellow")
            else:
                break
        if i >= MAX_RETRY:
            raise Exception("Failed to get response.")
        return response


    def generate_response(self, text, image_list):
        """

        :param text: input prompt
        :param image_list: list of image paths, preferably in png format
        :return:
        """
        messages = self.prepare_inputs(text, image_list)
        response = ""
        response_ = None
        i = 0
        MAX_RETRY = configs["API_MAX_TRY"]
        while i < MAX_RETRY:
            try:
                response_ = self.client.chat.completions.create(model="glm-4v-plus", messages=messages, tools=self.tools)
                response = response_.choices[0].message.content
                self.calulate_useage(response_)
            except KeyboardInterrupt:
                raise Exception("Terminated by user.")
            except Exception as e:
                print(e)
                i += 1
                time.sleep(1 + i)
                print_with_color(f"Failed to get response. Retry {i} times.", "yellow")
            else:
                break
        if i >= MAX_RETRY:
            raise Exception("Failed to get response.")

        if not isinstance(messages[0]["content"], str):
            for i in range(len(messages[0]["content"])):
                if messages[0]["content"][i]["type"] == "image_url":
                    messages[0]["content"][i]["image_url"]["url"] = messages[0]["content"][i]["image_url"]["url"][:64] + "..."

        return response, response_


if __name__ == '__main__':
    model = ChatGLMModel("GLM", configs, "4v-plus")
    text = "Tell me the model of this aircraft"
    image_list = [r"D:\Moba\MobA-main\assets\airplane.jpeg"]
    print_with_color("Start generating response...", "green")
    response, messages = model.generate_response(text, image_list)

    print_with_color(messages, "yellow")
    print_with_color(response, "cyan")
    # model.calulate_useage_total()
    print_with_color("Done.", "green")