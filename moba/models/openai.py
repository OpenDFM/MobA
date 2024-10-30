import pdb
import time

import requests

from moba.models.base import BaseModel
from moba.utils.utils import print_with_color, encode_image_base64


class OpenAIModel(BaseModel):
    def __init__(self, model_version, configs, model_type):  # TODO: merge configs and args
        super().__init__()
        self.base_url = configs["OPENAI_API_BASE_URL"]
        self.api_key = configs["OPENAI_API_KEY"]
        self.header = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        if model_type == "EMBEDDING":
            self.post_dict = {
                "model": model_version,
                "input": ""
            }
            self.base_url = self.base_url.replace("chat/completions", "embeddings")
        else:
            self.post_dict = {
                "model": model_version,
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
        self.price = configs['PRICE'].get(model_version, [0.01, 0.03])
        self.max_image_size = configs["MAX_IMAGE_SIZE"]
        self.model_type = model_type
        self.max_try = configs["API_MAX_TRY"]

    def calculate_usage(self, response):
        prompt_tokens = response["usage"]["prompt_tokens"]
        completion_tokens = response["usage"].get("completion_tokens", 0)
        self.tokens["prompt_tokens"] += prompt_tokens
        self.tokens["completion_tokens"] += completion_tokens
        print(f"[{self.model_type}] Prompt tokens: {prompt_tokens}, Completion tokens: {completion_tokens}, Cost: ${'{0:.3f}'.format(prompt_tokens / 1000 * self.price[0] + completion_tokens / 1000 * self.price[1])}")

    def calculate_usage_total(self):
        print(f"[{self.model_type}] Total prompt tokens: {self.tokens['prompt_tokens']}, Total completion tokens: {self.tokens['completion_tokens']}, Total cost: ${'{0:.3f}'.format(self.tokens['prompt_tokens'] / 1000 * self.price[0] + self.tokens['completion_tokens'] / 1000 * self.price[1])}")

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
        self.post_dict["input"] = text
        response = ""
        i = 0
        while i < self.max_try:
            try:
                response_ = requests.post(self.base_url, json=self.post_dict, headers=self.header)
                response_ = response_.json()
                response = response_["data"][0]["embedding"]
                self.calculate_usage(response_)
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
        if i >= self.max_try:
            raise Exception("Failed to get response.")
        return response

    def generate_response(self, text, image_list):
        messages = self.prepare_inputs(text, image_list)
        self.post_dict["messages"] = messages
        response = ""
        response_ = None
        i = 0
        while i < self.max_try:
            try:
                response_ = requests.post(self.base_url, json=self.post_dict, headers=self.header)
                response_ = response_.json()
                response = response_["choices"][0]["message"]["content"]
                self.calculate_usage(response_)
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
        if i >= self.max_try:
            raise Exception("Failed to get response.")

        if not isinstance(messages[0]["content"], str):
            for i in range(len(messages[0]["content"])):
                if messages[0]["content"][i]["type"] == "image_url":
                    messages[0]["content"][i]["image_url"]["url"] = messages[0]["content"][i]["image_url"]["url"][:64] + "..."

        return response, messages


if __name__ == '__main__':
    from moba.utils.config import load_config

    configs = load_config()
    configs["MAX_IMAGE_SIZE"] = 512

    print_with_color("Start loading model...", "green")
    model = OpenAIModel("gpt-4o-mini", configs, "GLOBAL")
    model_embed = OpenAIModel("text-embedding-3-small", configs, "EMBEDDING")
    text = "Which element on the screen should I click if I want to create an alarm?"
    image_list = ["../../assets/test_case_1_marked.png"]

    print_with_color("Start generating response...", "green")
    response, messages = model.generate_response(text, image_list)

    print_with_color(messages, "yellow")
    print_with_color(response, "cyan")
    model.calulate_useage_total()

    print_with_color("Start generating embedding...", "green")
    response = model_embed.generate_embedding(text)

    print_with_color(str(response[:10]).replace("]", ", ...]"), "cyan")
    print_with_color(f"Embedding length: {len(response)}", "cyan")
    model_embed.calulate_useage_total()
    print_with_color("Done.", "green")
