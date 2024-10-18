import pdb
import sys
import time

sys.path.append("../..")

from moba.process.input_prompter import generate_target_action_prompt, generate_target_app_prompt, generate_target_action_plain_prompt
from moba.process.output_parser import parse_target_action_response, parse_target_app_response, parse_target_action_plain_response
from moba.utils.utils import print_with_color


class LocalAgent:
    def __init__(self, controller, config, models, traj, logger=None):
        self.controller = controller
        self.config = config
        self.use_memory = config["USE_MEMORY"]
        self.model = models["LOCAL"]
        self.embedding_model = models["EMBEDDING"]
        self.traj = traj
        self.logger = logger
        print_with_color("🤖 : Local Agent of MobA is initialized!", "green", logger=self.logger)

    def get_target_action_plain(self, goal_desc, current_ui, memory, is_open_app_needed=False, logger=None):
        action_prompt, image_list, element_list = generate_target_action_plain_prompt(current_ui, self.config, goal_desc, memory, is_open_app_needed=is_open_app_needed, emb_model=self.embedding_model, use_memory=self.config["USE_MEMORY"])
        response, _ = self.model.generate_response(action_prompt, image_list)
        self.traj.add_request(function="get_target_action_plain", prompt=action_prompt, response=response)
        Observation, Thought, Status, Action, action_list, Message = parse_target_action_plain_response(response, logger=logger)

        if action_list[0][:8] == "OPEN_APP":
            description = action_list[1]
            Action, action_list = self.get_target_app(self.controller.package_list, memory, description, self.logger)
            action_list[1] = action_list[1].split(":")[-1]

        return Status, Action, action_list, element_list, Observation, Thought, Message

    def get_target_action(self, goal_desc, current_ui, memory, is_open_app_needed=False, logger=None):
        action_prompt, image_list, element_list = generate_target_action_prompt(current_ui, self.config, goal_desc, memory, is_open_app_needed=is_open_app_needed, emb_model=self.embedding_model, use_memory=self.config["USE_MEMORY"])
        response, _ = self.model.generate_response(action_prompt, image_list)
        self.traj.add_request(function="get_target_action", prompt=action_prompt, response=response)
        Observation, Thought, CanComplete, Action, action_list, Message = parse_target_action_response(response, logger=logger)

        if action_list[0][:8] == "OPEN_APP":
            description = action_list[1]
            Action, action_list = self.get_target_app(self.controller.package_list, memory, description, self.logger)
            action_list[1] = action_list[1].split(":")[-1]
            CanComplete = max(CanComplete, 0.5)

        return CanComplete, Action, action_list, element_list, Observation, Thought, Message

    def get_target_app(self, package_list, memory, description, logger=None):
        open_app_prompt = generate_target_app_prompt(package_list, memory, self.config, description)
        response, _ = self.model.generate_response(open_app_prompt, [])
        self.traj.add_request(function="get_target_app", prompt=open_app_prompt, response=response)
        Action, action_list = parse_target_app_response(response, logger=logger)
        return Action, action_list
