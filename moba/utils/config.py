import os
import yaml
import json


def load_config():
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(cur_dir, '..', 'config.yaml')

    config = dict()
    with open(config_path, "r") as file:
        yaml_data = yaml.safe_load(file)
    config.update(yaml_data)
    return config


def save_config(config):
    config_path = config["PATHS"]["exp_workspace"] + "/config.json"
    with open(config_path, "w", encoding="utf-8") as file:
        json.dump(config, file, indent=4, ensure_ascii=False)


class Trajectory():
    def __init__(self, config):
        self.trajectory_path = config["PATHS"]["exp_workspace"] + "/trajectory.json"

        self.trajectory = {
            "config": config,
            "trajectory": [],
            "requests": []
        }

    def add_request(self, function, prompt, response):
        self.trajectory["requests"].append({"function": function, "prompt": prompt, "response": response})
        self.save()

    def add_step(self, step):
        self.trajectory["trajectory"].append(step)
        self.save()

    def save(self):
        with open(self.trajectory_path, "w", encoding="utf-8") as file:
            json.dump(self.trajectory, file, indent=4, ensure_ascii=False)
