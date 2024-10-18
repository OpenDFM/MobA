import pdb
import time
from abc import abstractmethod
import re
import sys

sys.path.append('../..')  # Add the path to the project to the sys.path, in case you want to test this script independently

import requests

from moba.utils.utils import print_with_color, encode_image_base64, encode_image_PIL

from moba.utils.config import load_config

configs = load_config()


class BaseModel:
    def __init__(self):
        pass

    @abstractmethod
    def calulate_useage(self, response):
        pass

    @abstractmethod
    def calulate_useage_total(self):
        pass

    @abstractmethod
    def prepare_inputs(self, text, image_list):
        pass

    @abstractmethod
    def generate_response(self, text, image_list):
        pass


if __name__ == '__main__':
    model_type, model = configs["MODELS"]["MAIN"].split(".")

    model = getattr(__import__(f"moba.models.{model_type.lower()}", fromlist=[model_type]), f"{model_type}Model")(model, configs)
    text = "Which element on the screen should I click if I want to create an alarm?"
    image_list = ["../test_sample/1.png"]
    print_with_color("Start generating response...", "green")
    response, messages = model.generate_response(text, image_list)

    print_with_color(messages, "yellow")
    print_with_color(response, "cyan")
    model.calulate_useage_total()
    print_with_color("Done.", "green")
