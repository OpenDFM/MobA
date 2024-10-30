import pdb
import time
from abc import abstractmethod
import re
import sys

sys.path.append(r'D:\Moba\MobA-main')  # Add the path to the project to the sys.path, in case you want to test this script independently

import requests

from moba.utils.utils import print_with_color, encode_image_base64, encode_image_PIL
from moba.prompts.prompts import *

from moba.utils.config import load_config

configs = load_config()

from moba.models.base import BaseModel

from PIL import Image
import torch
from transformers import AutoConfig, AutoModel, AutoTokenizer
from accelerate import init_empty_weights, infer_auto_device_map, load_checkpoint_in_model, dispatch_model


class MiniCPMModel(BaseModel):
    def __init__(self, configs):
        super().__init__()
        self.model_path = configs["MODEL_PATH"]
        print("1")
        self.config = AutoConfig.from_pretrained(
            self.model_path,
            trust_remote_code=True
        )
        print("1")
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_path,
            trust_remote_code=True
        )
        print("1")
        with init_empty_weights():
            self.model = AutoModel.from_config(self.config, torch_dtype=torch.float16, trust_remote_code=True)
        self.device_map = self.device_map_setting()
        load_checkpoint_in_model(self.model, self.model_path, device_map=self.device_map)
        self.model = dispatch_model(self.model, device_map=self.device_map)
        torch.set_grad_enabled(False)
        self.model.eval()

        # 公共部分，没动
        self.tokens = {
            "prompt_tokens": 0,
            "completion_tokens": 0
        }
        # self.price = configs['PRICE'].get(model, [0, 0])
        self.max_image_size = configs["MAX_IMAGE_SIZE"]

    def device_map_setting(self):
        max_memory_each_gpu = '10GiB'
        gpu_device_ids = [0, 2, 3]  # Define which gpu to use (now we have two GPUs, each has 16GiB memory)
        no_split_module_classes = ['SiglipVisionTransformer', 'Qwen2DecoderLayer']
        max_memory = {
            device_id: max_memory_each_gpu for device_id in gpu_device_ids
        }
        device_map = infer_auto_device_map(self.model, max_memory=max_memory,
                                           no_split_module_classes=no_split_module_classes)
        device_map["llm.model.embed_tokens"] = 0
        device_map["llm.lm_head"] = 0  # firtt and last layer should be in same device
        device_map["vpm"] = 0
        device_map["resampler"] = 0
        device_map["llm.model.layers.8"] = 1
        device_map["llm.model.layers.9"] = 1
        device_map["llm.model.layers.10"] = 1
        device_map["llm.model.layers.11"] = 1
        device_map["llm.model.layers.12"] = 1
        device_map["llm.model.layers.13"] = 1
        device_map["llm.model.layers.14"] = 1
        device_map["llm.model.layers.15"] = 1
        device_map["llm.model.layers.16"] = 1
        device_map["llm.model.layers.17"] = 1
        device_map["llm.model.layers.18"] = 0
        device_map["llm.model.layers.19"] = 0
        device_map["llm.model.layers.20"] = 0
        device_map["llm.model.layers.21"] = 0
        device_map["llm.model.layers.22"] = 1
        device_map["llm.model.layers.23"] = 1
        device_map["llm.model.layers.24"] = 1
        device_map["llm.model.layers.25"] = 1
        device_map["llm.model.layers.26"] = 1
        device_map["llm.model.layers.27"] = 1
        return device_map

    """
    def calulate_useage(self, messages, response):
        prompt_tokens = int(str(self.model_with_vision.count_tokens(messages)).strip().replace("total_tokens: ", ""))
        completion_tokens = int(str(self.model_with_vision.count_tokens(response)).strip().replace("total_tokens: ", ""))
        self.tokens["prompt_tokens"] += prompt_tokens
        self.tokens["completion_tokens"] += completion_tokens
        print(f"Prompt tokens: {prompt_tokens}, Completion tokens: {completion_tokens}, Cost: ${'{0:.2f}'.format(prompt_tokens / 1000 * self.price[0] + completion_tokens / 1000 * self.price[1])}")
    """

    def calulate_useage_total(self):
        print(
            f"Prompt tokens: {self.tokens['prompt_tokens']}, Completion tokens: {self.tokens['completion_tokens']}, Total cost: ${'{0:.2f}'.format(self.tokens['prompt_tokens'] / 1000 * self.price[0] + self.tokens['completion_tokens'] / 1000 * self.price[1])}")

    def prepare_inputs(self, text, image_list):
        messages = []
        if image_list:
            for image_path in image_list:
                image = encode_image_PIL(image_path, max_size=self.max_image_size)
                messages.append(image)
        messages.append(text)
        msgs = [{'role': 'user', 'content': messages}]
        return msgs

    def generate_response(self, text, image_list):
        messages = self.prepare_inputs(text, image_list)
        response = ""
        i = 0
        MAX_RETRY = configs["API_MAX_TRY"]
        while i < MAX_RETRY:
            try:
                response_ = self.model.chat(image=None, msgs=messages, tokenizer=self.tokenizer)
                # response = response_.text.strip()
                # self.calulate_useage(messages, response)
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
            raise Exception("Failed to generate response.")

        messages = [str(m) for m in messages]
        return response_, messages


if __name__ == '__main__':
    model = MiniCPMModel(configs)
    text = "Tell me the model of this aircraft"
    image_list = ["./assets/airplane.jpeg"]
    print_with_color("Start generating response...", "green")
    response, messages = model.generate_response(text, image_list)

    print_with_color(messages, "yellow")
    print_with_color(response, "cyan")
    # model.calulate_useage_total()
    print_with_color("Done.", "green")



