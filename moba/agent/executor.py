import os
import subprocess
import threading
import time
import argparse
import sys
import platform
from importlib import import_module
from datetime import datetime

# Add the path to the project to the sys.path
sys.path.append('../..')

from moba.utils.android_util import SocketUtil
from moba.utils.config import load_config, save_config
from moba.utils.logger import Logger
from moba.control import and_ctrl
from moba.utils.utils import print_with_color,logo

from moba.agent.global_agent import GlobalAgent
from moba.agent.plain_agent import PlainAgent
from moba.process import input_prompter, output_parser


def get_system_info():
    """
    return the host system version
    """

    return platform.platform()


def setup_workspace(config, args, device):
    time_now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_dir = os.path.normpath(os.path.join(os.path.abspath(os.path.dirname(__file__)), args.log_dir))

    config["PATHS"] = {
        "log_dir": log_dir,
        "device_dir": os.path.normpath(os.path.join(log_dir, device)),
        "exp_dir": os.path.normpath(os.path.join(log_dir, device, args.exp_name)),
        "exp_workspace": os.path.normpath(os.path.join(log_dir, device, args.exp_name, time_now)),
    }

    for _, path in config["PATHS"].items():
        os.makedirs(path, exist_ok=True)

    logger = Logger(file_path=os.path.join(config["PATHS"]["exp_workspace"], "log.txt"))
    save_config(config)
    config["SYSTEM_INFO"] = get_system_info()
    config["DEVICE"] = device
    config["current_date"] = datetime.now().strftime("%Y-%m-%d, %A")
    config["current_time"] = datetime.now().strftime("%H:%M:%S")
    return logger,config


class TaskExecutor:
    def __init__(self, controller, config, models, logger):

        self.global_agent = GlobalAgent(controller, config, models, logger)
        self.plain_agent = PlainAgent(controller, config, models, logger)

        self.step_count = 0
        self.completed = False

        self.config = config
        self.models = models
        self.logger = logger

    def execute_task_plain(self, android_util):
        """
        Execute the task
        """
        print_with_color("🤖 : Start executing...", "green", logger=self.logger)
        time_start = time.time()
        try:
            while not self.completed and self.step_count < self.config["MAX_STEP"]:
                print_with_color(f"Step {self.step_count+1}", "green", pad=100, logger=self.logger)
                self.completed,do_action = self.plain_agent.execute_step(self.step_count)
                if do_action:
                    self.step_count += 1
                    print_with_color(f"🤖 : Step {self.step_count} is completed.", "green", logger=self.logger)
                time.sleep(1)
                if self.completed:
                    break
            if not self.completed:
                if self.config["ENABLE_CLIENT"]:
                    android_util.user_response("The task is not completed")
                print_with_color("🤖 : The task is not completed.", "red", logger=self.logger, log_level="error")
        except KeyboardInterrupt:
            if self.config["ENABLE_CLIENT"]:
                android_util.user_response("The task is interrupted by the user")
            print_with_color("🤖 : The task is interrupted by the user.", "red", logger=self.logger, log_level="error")
        # except Exception as e:
        #     if config["ENABLE_CLIENT"]:
        #         android_util.user_response("The task is interrupted by an error")
        #     print_with_color(f"🤖 : The task is interrupted by an error: {e}", "red", logger=self.logger, log_level="error")

        time_end = time.time()
        print_with_color(f"Total time: {time_end - time_start:.2f} seconds, Total steps: {self.step_count}", "green", logger=self.logger)
        for model in self.models.values():
            model.calulate_useage_total()     

    def execute_task(self, android_util):
        """
        Execute the task
        """
        print_with_color("🤖 : Start executing...", "green", logger=self.logger)
        time_start = time.time()
        try:
            while not self.completed and self.step_count < self.config["MAX_STEP"]:
                print_with_color(f"Step {self.step_count+1}", "green", pad=100, logger=self.logger)
                if self.config["USE_PLAN"]:
                    self.completed,do_action = self.global_agent.execute_step(self.step_count)
                else:
                    self.completed,do_action = self.plain_agent.execute_step(self.step_count)
                if do_action:
                    self.step_count += 1
                    print_with_color(f"🤖 : Step {self.step_count} is completed.", "green", logger=self.logger)
                time.sleep(1)
                if self.completed:
                    break
            if not self.completed:
                if self.config["ENABLE_CLIENT"]:
                    android_util.user_response("The task is not completed")
                print_with_color("🤖 : The task is not completed.", "red", logger=self.logger, log_level="error")
        except KeyboardInterrupt:
            if self.config["ENABLE_CLIENT"]:
                android_util.user_response("The task is interrupted by the user")
            print_with_color("🤖 : The task is interrupted by the user.", "red", logger=self.logger, log_level="error")
        # except Exception as e:
        #     if config["ENABLE_CLIENT"]:
        #         android_util.user_response("The task is interrupted by an error")
        #     print_with_color(f"🤖 : The task is interrupted by an error: {e}", "red", logger=self.logger, log_level="error")

        time_end = time.time()
        print_with_color(f"Total time: {time_end - time_start:.2f} seconds, Total steps: {self.step_count}", "green", logger=self.logger)
        for model in self.models.values():
            model.calulate_useage_total()


def main(config, args):
    logo()
    # Agent setup
    print_with_color("🤖 : Welcome to use MobA! I will help you execute the task, please follow the instructions.", "green")

    # Intialization
    device = and_ctrl.select_adb_devices(and_ctrl.get_adb_devices())
    logger,config = setup_workspace(config, args, device)
    controller = and_ctrl.AndroidController(config, device)

    # Load the M/LLM models
    models = {}
    for model_type, model_info in config["MODELS"].items():
        model_info = model_info.split(".", 1)
        model_class = model_info[0]
        model_version = model_info[1]
        module = import_module(f"moba.models.{model_class.lower()}")
        model = getattr(module, f"{model_class}Model")(model_version, config, model_type)
        print_with_color(f"Chosen {model_type} model: {model_info}", "green")
        models[model_type] = model

    # Set android input
    if config["ENABLE_CLIENT"]:
        print_with_color("📱 : Initializing client...", "yellow")
        android_util = SocketUtil(port=config["CLIENT_PORT"])
        print_with_color("📱 : The client is connected.", "green")
    else:
        android_util = None

    if config["ENABLE_CLIENT"]:
        print_with_color("Please enter the task from client:", "yellow")
        config["task"] = android_util.user_input().strip()
    else:
        print_with_color("Please enter the task from the terminal:", "yellow")
        config["task"] = input().strip()

    task_executor = TaskExecutor(controller, config, models, logger)

    # Execute the task
    task_executor.execute_task(android_util)

    if config["ENABLE_CLIENT"]:
        android_util.user_response("The task is completed")
    print_with_color("🤖 : The task is completed.", "green")
    logo()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description="Executor")
    parser.add_argument("--exp_name", "-e", default="Task", help="Name of this experiment")
    parser.add_argument("--log_dir", "-d", default="../../logs", help="The directory to log the outputs")
    parser.add_argument("--task_list", "-t", default=None, help="The file path of the task list. Use this if you want to eval multiple tasks.")  # TODO: support batch evaluation

    args = parser.parse_args()

    config = load_config()

    main(config, args)
