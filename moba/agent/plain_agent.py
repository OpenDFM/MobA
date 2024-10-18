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


class PlainAgent:
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
        self.tmp_history = {}
        self.memory.user_memory.add_query(config["task"])

        self.use_memory = config["USE_MEMORY"]
        self.local_agent = LocalAgent(controller, config, models, self.traj, logger)
        print_with_color("🤖 : Plain Agent of MobA is initialized!", "green", logger=self.logger)
        
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

    def check_open_app_needed(self, goal, cur_package):
        goal = goal.lower()
        if ("open" in goal or "launch" in goal) and "app" in goal:
            return True
        cur_package = cur_package.lower()
        if "launcher" in cur_package:
            return True
        return False
    def execute_step(self, step_count):
        # Get the current task node
        cur_task_node = self.final_task_node
        # set the basic information of the task node
        cur_task_node.set_basic(package_name=self.current_ui["activity"][0], activitry_name=self.current_ui["activity"][1])
        cur_goal_desc = cur_task_node.get_goal_desc()
        
        self.memory.task_memory.set_cur_task_node(cur_task_node)

        is_open_app_needed = self.check_open_app_needed(cur_goal_desc, self.current_ui["activity"][0])  # If current screen is launcher or the subgoal is to open an app

        # Get the current action
        status, action_str, action, element_list, obs, thought, output = self.local_agent.get_target_action_plain(cur_goal_desc, self.current_ui, self.memory, is_open_app_needed,self.logger)
        
        # add memory if the goal is not finished
        if not status:
            self.memory.app_memory.add_app(self.current_ui["activity"][0])
            page_name = self.memory.app_memory.add_page(self.current_ui["activity"][0], obs)
            if output and len(output):
                self.memory.task_memory.add_output(cur_task_node, output)
            cur_task_node.set_page(page_name=page_name, app_name=self.current_ui["activity"][0], action=action_str, obs=obs, thought=thought)

        # Execute the action
        # 这里需要重新加入新的open app的逻辑
        # 暂时无法运行
        self.controller.execute_action(action, element_list)
        time.sleep(2)
        print_with_color(f"🤖 : The action {action_str} is executed.", "green", logger=self.logger)
        self.memory.task_memory.set_last_action_node(cur_task_node)

        # Get current ui information, update trajectory
        self.update_traj(action, step_count)
        
        if step_count == 0 and not status:
            self.tmp_history[cur_goal_desc] = [Task(action_str, cur_task_node.app_name, cur_task_node.page_name, obs, thought)]
        elif not status:
            self.tmp_history[cur_goal_desc].append(Task(action_str, cur_task_node.app_name, cur_task_node.page_name, obs, thought))
        
        if status:
            self.memory.task_memory.task_history.history = self.tmp_history
            self.memory.save_all()
            
        return status,True
