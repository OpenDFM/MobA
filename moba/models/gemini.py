import pdb
import time

import google.generativeai as genai

from moba.models.base import BaseModel
from moba.utils.utils import print_with_color, encode_image_PIL


class GeminiModel(BaseModel):
    def __init__(self, model_version, configs, model_type):
        super().__init__()
        genai.configure(api_key=configs["GEMINI_API_KEY"], transport='rest')
        block_type = "BLOCK_ONLY_HIGH"
        self.safety_settings = [{
            "category": "HARM_CATEGORY_DANGEROUS",
            "threshold": block_type,
        }, {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": block_type,
        }, {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": block_type,
        }, {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": block_type,
        }, {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": block_type,
        }, ]

        self.model = genai.GenerativeModel(model_name=model_version, safety_settings=self.safety_settings)
        self.tokens = {
            "prompt_tokens": 0,
            "completion_tokens": 0
        }
        self.price = configs['PRICE'].get(model_version, [0.00125, 0.005])
        self.max_image_size = configs["MAX_IMAGE_SIZE"]
        self.model_type = model_type
        self.max_try = configs["API_MAX_TRY"]

    def calculate_usage(self, response):
        response_dict = response.to_dict()
        prompt_tokens = response_dict["usage_metadata"]["prompt_token_count"]
        completion_tokens = response_dict["usage_metadata"]["candidates_token_count"]
        self.tokens["prompt_tokens"] += prompt_tokens
        self.tokens["completion_tokens"] += completion_tokens
        print(f"[{self.model_type}] Prompt tokens: {prompt_tokens}, Completion tokens: {completion_tokens}, Cost: ${'{0:.3f}'.format(prompt_tokens / 1000 * self.price[0] + completion_tokens / 1000 * self.price[1])}")

    def calculate_usage_total(self):
        print(f"[{self.model_type}] Total prompt tokens: {self.tokens['prompt_tokens']}, Total completion tokens: {self.tokens['completion_tokens']}, Total cost: ${'{0:.3f}'.format(self.tokens['prompt_tokens'] / 1000 * self.price[0] + self.tokens['completion_tokens'] / 1000 * self.price[1])}")

    def prepare_inputs(self, text, image_list):
        messages = [text, ]
        if image_list:
            for image_path in image_list:
                image = encode_image_PIL(image_path, max_size=self.max_image_size)
                messages.append(image)
        return messages

    def generate_response(self, text, image_list):
        messages = self.prepare_inputs(text, image_list)
        response = ""
        i = 0
        while i < self.max_try:
            try:
                response_ = self.model.generate_content(messages)
                response = response_.text.strip()
                self.calculate_usage(response_)
            except KeyboardInterrupt:
                raise Exception("Terminated by user.")
            except Exception as e:
                print(e)
                i += 1
                time.sleep(1 + i)
                print_with_color(f"Failed to get response. Retry {i} times.", "yellow")
            else:
                break
        if i >= self.max_try:
            raise Exception("Failed to generate response.")

        messages = [str(m) for m in messages]
        return response, messages


if __name__ == '__main__':
    from moba.utils.config import load_config

    configs = load_config()

    print_with_color("Start loading model...", "green")
    model = GeminiModel("gemini-1.5-pro-latest", configs, "GLOBAL")
    text = "Which element on the screen should I click if I want to create an alarm?"
    image_list = ["../../assets/test_case_1_marked.png"]

    print_with_color("Start generating response...", "green")
    response, messages = model.generate_response(text, image_list)

    print_with_color(messages, "yellow")
    print_with_color(response, "cyan")
    model.calulate_useage_total()
    print_with_color("Done.", "green")
