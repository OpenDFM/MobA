import os
from moba.utils.utils import save_json, load_json_if_exist


class TaskMemory:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.cur_task_node: TaskNode = None
        self.last_action_node: TaskNode = None
        self.last_suc_task_node: TaskNode = None
        self.last_fail_task_node: TaskNode = None

        self.task_history = TaskHistory()
        self.success_history = ExpHistory()
        self.failure_history = ExpHistory()
        self.output_history = {}

        self.task_history_path = os.path.join(base_dir, "task_history.json")
        self.failure_path = os.path.join(base_dir, "failure.json")
        self.success_path = os.path.join(base_dir, "success.json")

    def get_cur_task_node(self):
        return self.cur_task_node

    def set_cur_task_node(self, task_node):
        self.cur_task_node = task_node

    def set_last_action_node(self, task_node):
        self.last_action_node = task_node
    
    def add_output(self, task_node, output):
        self.output_history[task_node.goal_desc] = output
    
    def add_failure(self, task_node, obs, thought, reflection):
        self.last_fail_task_node = task_node
        self.failure_history.add_task(task_node.goal_desc, [task_node])
        task_node.obs = obs
        task_node.thought = thought
        task_node.reflection = reflection

    def add_success(self, task_node, output):
        self.last_suc_task_node = task_node
        self.success_history.add_task(task_node.goal_desc, [task_node])
        if output and len(output):
            self.output_history[task_node.goal_desc] = output

    def save_suc_fail(self):
        os.makedirs(self.base_dir, exist_ok=True)
        self.failure_history.save_to_file(self.failure_path)
        self.success_history.save_to_file(self.success_path)

    def save_all(self):
        os.makedirs(self.base_dir, exist_ok=True)
        self.task_history.save_to_file(self.task_history_path)
        self.failure_history.save_to_file(self.failure_path)
        self.success_history.save_to_file(self.success_path)

    def load_all(self):
        os.makedirs(self.base_dir, exist_ok=True)
        self.task_history = TaskHistory.load_from_file(self.task_history_path)
        self.failure_history = ExpHistory.load_from_file(self.failure_path)
        self.success_history = ExpHistory.load_from_file(self.success_path)


class TaskNode:
    def __init__(self, goal_desc, cnt):
        self.goal_desc = goal_desc
        self.children = []
        self.par: TaskNode = None
        self.status = 0
        self.is_fin = False
        self.skip = False

        self.cnt = cnt
        self.action = ""

        self.page_name = ""
        self.app_name = ""
        self.activity = ""
        self.package = ""

        self.obs = ""
        self.thought = ""
        self.reflection = ""

    def get_goal_desc(self):
        return self.goal_desc

    def set_basic(self, package_name=None, activitry_name=None):
        self.package = package_name
        self.activity = activitry_name

    def set_page(self, page_name=None, app_name=None, action=None, obs=None, thought=None):
        self.page_name = page_name
        self.app_name = app_name
        self.action = action
        self.obs = obs
        self.thought = thought

    def to_dict(self):
        return {
            "desc": self.goal_desc,
            "status": self.status,
            "is_fin": self.is_fin,
            "skip": self.skip,
            "cnt": self.cnt,
            "action": self.action,
            "page_name": self.page_name,
            "app_name": self.app_name,
            "activity": self.activity,
            "package": self.package,
            "obs": self.obs,
            "thought": self.thought,
            "reflection": self.reflection
        }

    @staticmethod
    def from_dict(data):
        task_node = TaskNode(data["desc"], data["cnt"])
        task_node.status = data["status"]
        task_node.is_fin = data["is_fin"]
        task_node.skip = data["skip"]
        task_node.action = data["action"]
        task_node.page_name = data["page_name"]
        task_node.app_name = data["app_name"]
        task_node.activity = data["activity"]
        task_node.package = data["package"]
        task_node.obs = data["obs"]
        task_node.thought = data["thought"]
        task_node.reflection = data["reflection"]
        return task_node


class Task:
    def __init__(self, desc, app_name, page_id, obs, thought, action=""):
        self.desc = desc
        self.app_name = app_name
        self.page_id = page_id
        self.obs = obs
        self.thought = thought
        self.action = action

    def to_dict(self):
        return {
            "desc": self.desc,
            "page_id": self.page_id,
            "app_name": self.app_name,
            "obs": self.obs,
            "thought": self.thought,
            "action": self.action
        }

    @staticmethod
    def from_dict(data):
        return Task(data["desc"], data["page_id"], data["app_name"], data["obs"], data["thought"], data["action"])


class ExpHistory:
    def __init__(self, history={}):
        self.history = history

    def add_task(self, task_name, task_list):
        self.history[task_name] = task_list

    def save_to_file(self, file_path):
        task_data = {task_name: [task.to_dict() for task in task_list] for task_name, task_list in self.history.items()}
        save_json(file_path, task_data)

    @staticmethod
    def load_from_file(file_path):
        # return TaskHistory(load_json_if_exist(file_path, default={}))
        task_data = load_json_if_exist(file_path, default={})
        return ExpHistory({task_name: [TaskNode.from_dict(task) for task in task_list] for task_name, task_list in task_data.items()})


class TaskHistory:
    def __init__(self, history={}):
        self.history = history

    def add_task(self, task_name, task_list):
        self.history[task_name] = task_list

    def save_to_file(self, file_path):
        task_data = {task_name: [task.to_dict() for task in task_list] for task_name, task_list in self.history.items()}
        save_json(file_path, task_data)

    @staticmethod
    def load_from_file(file_path):
        # return TaskHistory(load_json_if_exist(file_path, default={}))
        task_data = load_json_if_exist(file_path, default={})
        return TaskHistory({task_name: [Task.from_dict(task) for task in task_list] for task_name, task_list in task_data.items()})
