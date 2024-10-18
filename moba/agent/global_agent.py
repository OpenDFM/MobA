import pdb
import sys
import time

sys.path.append("../..")

from moba.process.input_prompter import generate_split_goal_prompt, generate_validate_and_reflect_prompt
from moba.process.output_parser import parse_split_goal_response, parse_validate_and_reflect_response
from moba.memory.memory import Memory
from moba.memory.task_memory import Task, TaskNode
from moba.agent.local_agent import LocalAgent
from moba.models.openai import OpenAIModel
from moba.utils.utils import print_with_color
from moba.memory.memory import Memory
from moba.memory.app_memory import AppData
from moba.memory.task_memory import TaskNode
from moba.utils.config import Trajectory


class GlobalAgent:
    def __init__(self, controller, config, models, logger=None):
        self.controller = controller
        self.logger = logger
        self.config = config
        self.current_ui = {}
        self.traj = Trajectory(config)
        self.update_traj(["START"], 0)

        self.model = models["GLOBAL"]
        self.embedding_model = models["EMBEDDING"]

        self.final_task_node = TaskNode(self.config["task"], 0)
        self.final_task_node.is_fin = True
        self.cur_task_node = self.final_task_node

        self.memory = Memory(self.config)
        self.memory.user_memory.add_query(config["task"])

        self.use_memory = config["USE_MEMORY"]
        self.local_agent = LocalAgent(controller, config, models, self.traj, logger)
        print_with_color("🤖 : Global Agent of MobA is initialized!", "green", logger=self.logger)

    def update_traj(self, action, step_count):
        # Get the current screen, XML, package, activity
        image_path, xml_path, cur_activity = self.get_ui(f"{step_count}")

        step = {
            "step": step_count,
            "activity": cur_activity,
            "action": action,
            "image_path": image_path,
            "xml_path": xml_path,
        }
        self.traj.add_step(step)
        self.current_ui = step

    def get_ui(self, prefix):
        image_path = self.controller.get_screenshot(prefix, self.config["PATHS"]["exp_workspace"])
        print_with_color(f"Screenshot saved to {image_path}", "yellow", logger=self.logger)
        xml_path = self.controller.get_xml(prefix, self.config["PATHS"]["exp_workspace"])
        if xml_path:
            print_with_color(f"XML saved to {xml_path}", "yellow", logger=self.logger)
        else:
            print_with_color("XML is not available.", "yellow", logger=self.logger)

        cur_activity = self.controller.get_activity()
        print(f"Current package: {cur_activity[0]}, current activity: {cur_activity[1]}")

        return image_path, xml_path, cur_activity

    def get_track(self, task_node):
        task_node_list = []
        if len(task_node.children):
            for child in task_node.children:
                task_node_list.extend(self.get_track(child))
        else:
            task_node_list.append(Task(task_node.goal_desc, task_node.app_name, task_node.page_name, task_node.obs, task_node.thought, task_node.action))
        return task_node_list

    def update_history(self, task_node):
        if task_node.goal_desc not in self.memory.task_memory.task_history.history:
            self.memory.task_memory.task_history.history[task_node.goal_desc] = self.get_track(task_node)

        for child in task_node.children:
            self.update_history(child)

    def check_done(self):
        return self.final_task_node.status == 1

    def update_done(self):
        self.update_history(self.final_task_node)

    def complete_current_task_node(self):
        tmp_task_node = self.cur_task_node
        while 1:
            tmp_task_node.status = 1
            if not tmp_task_node.is_fin:
                self.cur_task_node = tmp_task_node.par.children[tmp_task_node.cnt + 1]
                break
            else:
                if not tmp_task_node.par:
                    self.cur_task_node = self.final_task_node
                    break
                tmp_task_node = tmp_task_node.par
        return

    def add_subgoals(self, sub_goals):
        for ix, goal in enumerate(sub_goals):
            tmp_task_node = TaskNode(goal, ix)
            tmp_task_node.par = self.cur_task_node
            if ix == len(sub_goals) - 1:
                tmp_task_node.is_fin = True
            self.cur_task_node.children.append(tmp_task_node)
        self.cur_task_node = self.cur_task_node.children[0]

    def get_current_task_node(self):
        return self.cur_task_node

    def get_split_goal(self, goal_desc, current_ui, memory: Memory, logger=None):
        split_prompt, image_list = generate_split_goal_prompt(current_ui, self.config, goal_desc, memory, emb_model=self.embedding_model, use_memory=self.use_memory)
        response, _ = self.model.generate_response(split_prompt, image_list)
        self.traj.add_request(function="get_split_goal", prompt=split_prompt, response=response)
        Observation, Thought, SubGoals = parse_split_goal_response(response, logger=logger)
        return SubGoals

    def validate_and_reflect(self, current_ui, last_ui, memory, logger=None):
        validate_and_reflect_prompt, image_list = generate_validate_and_reflect_prompt(current_ui, last_ui, self.config, memory, emb_model=self.embedding_model, use_memory=self.config["USE_MEMORY"])
        response, _ = self.model.generate_response(validate_and_reflect_prompt, image_list)
        self.traj.add_request(function="validate_and_reflect", prompt=validate_and_reflect_prompt, response=response)
        Thought, SubGoal_Status, Goal_Status, Reflection = parse_validate_and_reflect_response(response, logger=logger)
        return SubGoal_Status, Reflection

    def check_open_app_needed(self, goal, cur_package):
        goal = goal.lower()
        if ("open" in goal or "launch" in goal) and "app" in goal:
            return True
        cur_package = cur_package.lower()
        if "launcher" in cur_package:
            return True
        return False

    def execute_step(self, step_count):
        # get and set task node
        cur_task_node = self.get_current_task_node()
        cur_task_node.set_basic(package_name=self.current_ui["activity"][0], activitry_name=self.current_ui["activity"][1])
        cur_goal_desc = cur_task_node.get_goal_desc()
        self.memory.task_memory.set_cur_task_node(cur_task_node)

        is_open_app_needed = self.check_open_app_needed(cur_goal_desc, self.current_ui["activity"][0])  # If current screen is launcher or the subgoal is to open an app

        CanComplete, action_str, action, element_list, obs, thought, message = self.local_agent.get_target_action(cur_goal_desc, self.current_ui, self.memory, is_open_app_needed=is_open_app_needed, logger=self.logger)

        # check if the goal can be completed, we will split current goal into several subgoals
        if CanComplete == 0:
            subgoals = self.get_split_goal(cur_goal_desc, self.current_ui, self.memory, self.logger)
            self.memory.task_memory.add_failure(cur_task_node, obs, thought, thought)
            self.add_subgoals(subgoals)
            return False, False

        print_with_color(f"🤖 : Execute the action {action_str}......", "blue", logger=self.logger)
        # set page and task node
        self.memory.app_memory.add_app(self.current_ui["activity"][0])
        page_name = self.memory.app_memory.add_page(self.current_ui["activity"][0], obs)
        cur_task_node.set_page(page_name=page_name, app_name=self.current_ui["activity"][0], action=action_str, obs=obs, thought=thought)

        # Execute the action
        if action[0] != "FINISH":
            self.controller.execute_action(action, element_list)
        time.sleep(2)
        print_with_color(f"🤖 : The action {action_str} is executed.", "green", logger=self.logger)
        self.memory.task_memory.set_last_action_node(cur_task_node)

        last_ui = self.current_ui
        # Get current ui information, update trajectory
        self.update_traj(action, step_count+1)

        # split codes below into another function
        # validate and generate reflection
        success, reflection = self.validate_and_reflect(self.current_ui, last_ui, self.memory, self.logger)

        if success:
            self.complete_current_task_node()
            self.memory.task_memory.add_success(cur_task_node, message)
        else:
            subgoals = self.get_split_goal(cur_goal_desc, self.current_ui, self.memory, self.logger)
            self.add_subgoals(subgoals)
            self.memory.task_memory.add_failure(cur_task_node, obs, thought, reflection)

        self.memory.task_memory.save_suc_fail()
        self.memory.save_embeddings()

        status = self.check_done()
        if status:
            self.update_done()
            self.memory.save_all()

        return status, True
