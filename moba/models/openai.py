import pdb
import time
from abc import abstractmethod
import re
import sys

sys.path.append('../..')  # Add the path to the project to the sys.path, in case you want to test this script independently

import requests

from moba.utils.utils import print_with_color, encode_image_base64, encode_image_PIL
from moba.prompts.prompts import *

from moba.utils.config import load_config

from moba.models.base import BaseModel

configs = load_config()


class OpenAIModel(BaseModel):
    def __init__(self, model, configs, model_type):  # TODO: merge configs and args
        super().__init__()
        self.base_url = configs["OPENAI_API_BASE_URL"]
        self.api_key = configs["OPENAI_API_KEY"]
        self.header = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        self.post_dict = {
            "model": model,
            "messages": [],
            # "max_tokens": 500,
            "temperature": 0.1,
            "top_p": 1,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0,
        }
        self.tokens = {
            "prompt_tokens": 0,
            "completion_tokens": 0
        }
        self.price = configs['PRICE'].get(model, [0.01, 0.03])
        self.max_image_size = configs["MAX_IMAGE_SIZE"]
        self.model_type = model_type

    def calculate_usage(self, response):
        prompt_tokens = response["usage"]["prompt_tokens"]
        completion_tokens = response["usage"].get("completion_tokens", 0)
        self.tokens["prompt_tokens"] += prompt_tokens
        self.tokens["completion_tokens"] += completion_tokens
        print(f"[{self.model_type}] Prompt tokens: {prompt_tokens}, Completion tokens: {completion_tokens}, Cost: ${'{0:.3f}'.format(prompt_tokens / 1000 * self.price[0] + completion_tokens / 1000 * self.price[1])}")

    def calculate_usage_total(self):
        print(
            f"[{self.model_type}] Total prompt tokens: {self.tokens['prompt_tokens']}, Total completion tokens: {self.tokens['completion_tokens']}, Total cost: ${'{0:.3f}'.format(self.tokens['prompt_tokens'] / 1000 * self.price[0] + self.tokens['completion_tokens'] / 1000 * self.price[1])}")

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
        self.post_dict["messages"] = messages
        response = ""
        response_ = None
        i = 0
        MAX_RETRY = configs["API_MAX_TRY"]
        while i < MAX_RETRY:
            try:
                response_ = requests.post(self.base_url, json=self.post_dict, headers=self.header)
                response_ = response_.json()
                response = response_["choices"][0]["message"]["content"]
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

        if not isinstance(messages[0]["content"], str):
            for i in range(len(messages[0]["content"])):
                if messages[0]["content"][i]["type"] == "image_url":
                    messages[0]["content"][i]["image_url"]["url"] = messages[0]["content"][i]["image_url"]["url"][:64] + "..."

        return response, messages
