import os
import pdb
import re
import json

from moba.prompts import prompts
from moba.utils.utils import print_with_color
from moba.process import img_proc, vh_proc


def load_actions():
    json_path = os.path.join(os.path.dirname(__file__), "../prompts/actions.json")
    with open(json_path, "r", encoding="utf-8") as f:
        actions = json.load(f)
    action_prompts = {
        "system": "",
        "combination": "",
        "single": ""
        # "api": "",
    }

    for action in actions.keys():
        if actions[action]["type"] not in action_prompts.keys() or actions[action]["status"] == "deactivated":
            continue
        action_prompt = f"""Action [{action}]
    Description: {actions[action]["description"]}
    Usage: {actions[action]["usage"]}
    Example: {actions[action]["example"]}
"""
        action_prompts[actions[action]["type"]] += action_prompt

    return action_prompts


def load_package_list():
    json_path = os.path.join(os.path.dirname(__file__), "../prompts/package_list.json")
    with open(json_path, "r", encoding="utf-8") as f:
        package_list = json.load(f)

    package_prompt = ""
    for package in package_list:
        package_prompt += f"{package}: {' '.join(package_list[package]['description'])}\n"

    return package_prompt


def get_image_list(image_path, element_list, image_mode):
    if image_mode > 0:
        if len(element_list) > 0:
            marked_image_path = img_proc.mark_screenshot(image_path, element_list)
            print_with_color(f"The marked screenshot saved to {marked_image_path}", "yellow")
        else:
            image_mode = 0

    match image_mode:
        case -1:  # no image
            image_list = []
        case 0:  # only the original image
            image_list = [image_path]
        case 1:  # only the marked image
            image_list = [marked_image_path]
        case 2:  # both the original and marked images
            image_list = [image_path, marked_image_path]
        case 3:  # concatenate the images, (left: original, right: marked)
            concatenate_image = img_proc.concatenate_images(image_path, marked_image_path)
            image_list = [concatenate_image]
        case _:
            raise ValueError("Invalid IMAGE_MODE value.")

    image_prompt = prompts.image_prompt[str(image_mode)]

    return image_list, image_prompt



def generate_target_action_plain_prompt(current_ui, config, goal_desc, memory, is_open_app_needed=False,emb_model=None, use_memory=True):
    image_path, xml_path, cur_package, cur_activity = current_ui["image_path"], current_ui["xml_path"], current_ui["activity"][0], current_ui["activity"][1]

    action_prompts = load_actions()
    system_prompt = prompts.system_prompt
    for action_type in action_prompts.keys():
        system_prompt = re.sub(rf"<{action_type}_action_list>", action_prompts[action_type], system_prompt)

    action_prompt = prompts.get_action_plain_prompt
    action_prompt = re.sub(r"<current_date>",  config["current_date"], action_prompt)
    action_prompt = re.sub(r"<current_time>",  config["current_time"], action_prompt)

    goal_desc = "\"" + goal_desc + "\"."

    if len(memory.task_memory.output_history) and use_memory:
        key = memory.retrieve_history(memory.task_memory.output_history, memory.task_memory.cur_task_node.goal_desc, emb_model=emb_model)
        output_desc = memory.task_memory.output_history[key]
        goal_desc += f" The historical execution output is '{output_desc}'. "
        goal_desc += f"You need to use the output to determine whether the current Goal needs to be completed and how to complete it. "

    last_action_prompt = ""
    if memory.task_memory.last_action_node and use_memory:
        last_action_prompt = re.sub(r"<action_node_desc>", "The details of your last executed node are as follows", last_action_prompt)
        last_action_prompt = re.sub(r"<goal_desc>", memory.task_memory.last_action_node.goal_desc, last_action_prompt)
        last_action_prompt = re.sub(r"<last_obs>", memory.task_memory.last_action_node.obs, last_action_prompt)
        last_action_prompt = re.sub(r"<last_action>", memory.task_memory.last_action_node.action, last_action_prompt)
        last_action_prompt = re.sub(r"<last_thought>", memory.task_memory.last_action_node.thought, last_action_prompt)
        goal_desc += '\n' + last_action_prompt

    history = memory.task_memory.task_history.history
    history_prompt = ""
    if len(history) and use_memory:
        history_prompt = "You can refer to the track of the successful tasks below:\n"
        tar_goal = memory.retrieve_history(history, goal_desc, emb_model=emb_model)
        history_prompt += f"goal:\n{tar_goal}\n"
        history_prompt += "track:\n"
        for idx, task in enumerate(history[tar_goal]):
            history_prompt += f"{idx+1}: \n"
            history_prompt += f"action: {task.desc}\n"
            history_prompt += f"observation: {task.obs}\n"
            history_prompt += f"thought: {task.thought}\n"
            
    action_prompt = re.sub(r"<history_prompt>", history_prompt, action_prompt)

    action_prompt = re.sub(r"<goal_desc>", goal_desc[:-2], action_prompt)
    action_prompt += "\n"

    action_prompt = re.sub(r"<current_activity>", cur_activity, action_prompt)
    action_prompt = re.sub(r"<current_package>", cur_package, action_prompt)

    if xml_path and not is_open_app_needed:
        element_list = vh_proc.extract_elements(xml_path)
        element_list_clean = vh_proc.clean_element_list(element_list)
        xml_prompt = re.sub(r"<xml_info>", element_list_clean, prompts.xml_prompt["1"])
    else:
        element_list = []
        element_list_clean = ""
        xml_prompt = prompts.xml_prompt["-1" if is_open_app_needed else "0"]

    image_list, image_prompt = get_image_list(image_path, element_list, config["IMAGE_MODE"] if not is_open_app_needed else -1)

    action_prompt = re.sub(r"<xml_desc>", xml_prompt, action_prompt)
    action_prompt = re.sub(r"<img_desc>", image_prompt, action_prompt)

    action_prompt = system_prompt + action_prompt

    print(action_prompt)
    return action_prompt, image_list, element_list


def generate_target_action_prompt(current_ui, config, goal_desc, memory, is_open_app_needed=False, emb_model=None, use_memory=True):
    image_path, xml_path, cur_package, cur_activity = current_ui["image_path"], current_ui["xml_path"], current_ui["activity"][0], current_ui["activity"][1]

    action_prompts = load_actions()
    system_prompt = prompts.system_prompt
    for action_type in action_prompts.keys():
        system_prompt = re.sub(rf"<{action_type}_action_list>", action_prompts[action_type], system_prompt)

    action_prompt_1 = prompts.get_action_prompt_1
    action_prompt_1 = re.sub(r"<current_date>", config["current_date"], action_prompt_1)
    action_prompt_1 = re.sub(r"<current_time>", config["current_time"], action_prompt_1)

    cur_task_node = memory.task_memory.cur_task_node

    current_goal=goal_desc

    if cur_task_node.par and use_memory:
        current_goal += f"\", which is a sub-goal of \"{cur_task_node.par.goal_desc}"

    goal_desc = ""

    if len(memory.task_memory.output_history) and use_memory:
        key = memory.retrieve_history(memory.task_memory.output_history, memory.task_memory.cur_task_node.goal_desc, emb_model=emb_model)
        output_desc = memory.task_memory.output_history[key]
        goal_desc += f"The historical execution output is \"{output_desc}\". "
        goal_desc += f"You need to use the output to determine whether the current Goal needs to be completed and how to complete it."    
    
    last_suc_prompt = ""
    last_fail_prompt = ""
    last_status = False
    
    if memory.task_memory.last_suc_task_node and use_memory:
        last_suc_prompt = prompts.last_node_prompt 
        if memory.task_memory.last_suc_task_node == memory.task_memory.last_action_node:
            last_status = True
            last_suc_prompt = re.sub(r"<action_node_desc>", "Your previous action's status is Success, and the details are as follows", last_suc_prompt)
        else:
            last_suc_prompt = re.sub(r"<action_node_desc>", "The details of your last successfully node are as follows", last_suc_prompt)

        last_suc_prompt = re.sub(r"<last_goal_desc>", memory.task_memory.last_suc_task_node.goal_desc, last_suc_prompt)
        last_suc_prompt = re.sub(r"<last_obs>", memory.task_memory.last_suc_task_node.obs, last_suc_prompt)
        last_suc_prompt = re.sub(r"<last_action>", memory.task_memory.last_suc_task_node.action, last_suc_prompt)
        last_suc_prompt = re.sub(r"<last_thought>", memory.task_memory.last_suc_task_node.thought, last_suc_prompt)
        
    if memory.task_memory.last_fail_task_node and use_memory:
        last_fail_prompt = prompts.last_node_prompt 
        if memory.task_memory.last_fail_task_node == memory.task_memory.last_action_node:
            last_fail_prompt = re.sub(r"<action_node_desc>", "Your previous action's status is Failed, and the details are as follows", last_fail_prompt)
        else:
            last_fail_prompt = re.sub(r"<action_node_desc>", "The details of your last failed node are as follows", last_fail_prompt)
            
        last_fail_prompt = re.sub(r"<last_goal_desc>", memory.task_memory.last_fail_task_node.goal_desc, last_fail_prompt)
        last_fail_prompt = re.sub(r"<last_obs>", memory.task_memory.last_fail_task_node.obs, last_fail_prompt)
        last_fail_prompt = re.sub(r"<last_action>", memory.task_memory.last_fail_task_node.action, last_fail_prompt)
        last_fail_prompt = re.sub(r"<last_thought>", memory.task_memory.last_fail_task_node.thought, last_fail_prompt)

    if len(last_suc_prompt) and last_status:
        goal_desc += '\n' + last_suc_prompt + '\n' + last_fail_prompt
    
    if len(last_fail_prompt) and not last_status:
        goal_desc += '\n' + last_fail_prompt + '\n' + last_suc_prompt
    
    if goal_desc.endswith('\n'):
        goal_desc = goal_desc[:-1]

    action_prompt_1  = re.sub(r"<final_goal>", config["task"],action_prompt_1)
    action_prompt_1  = re.sub(r"<current_goal>", current_goal,action_prompt_1)
    action_prompt_1 = re.sub(r"<goal_desc>", goal_desc, action_prompt_1)

    if (len(memory.task_memory.success_history.history)) and use_memory and not last_status:
        key = memory.retrieve_history(memory.task_memory.success_history.history, memory.task_memory.cur_task_node.goal_desc, emb_model=emb_model)
        res = memory.task_memory.success_history.history[key][0]
        success_prompt = prompts.success_exp_prompt
        success_prompt = re.sub(r"<suc_goal_desc>", res.goal_desc, success_prompt)
        success_prompt = re.sub(r"<suc_obs>", res.obs, success_prompt)
        success_prompt = re.sub(r"<suc_action>", res.action, success_prompt)
        success_prompt = re.sub(r"<suc_thought>", res.thought, success_prompt)
        action_prompt_1 += success_prompt + "\n"

    if (len(memory.task_memory.failure_history.history)) and use_memory and last_status:
        key = memory.retrieve_history(memory.task_memory.failure_history.history, memory.task_memory.cur_task_node.goal_desc, emb_model=emb_model)
        res = memory.task_memory.failure_history.history[key][0]
        failure_prompt = prompts.failure_exp_prompt
        failure_prompt = re.sub(r"<fail_goal_desc>", res.goal_desc, failure_prompt)
        failure_prompt = re.sub(r"<fail_obs>", res.obs, failure_prompt)
        failure_prompt = re.sub(r"<fail_action>", res.action, failure_prompt)
        failure_prompt = re.sub(r"<fail_thought>", res.thought, failure_prompt)
        action_prompt_1 += failure_prompt + "\n"

    action_prompt_2 = prompts.get_action_prompt_2
    action_prompt_2 = re.sub(r"<current_activity>", cur_activity, action_prompt_2)
    action_prompt_2 = re.sub(r"<current_package>", cur_package, action_prompt_2)

    if xml_path and not is_open_app_needed:
        element_list = vh_proc.extract_elements(xml_path)
        element_list_clean = vh_proc.clean_element_list(element_list)
        xml_prompt = re.sub(r"<xml_info>", element_list_clean, prompts.xml_prompt["1"])
    else:
        element_list = []
        element_list_clean = ""
        xml_prompt = prompts.xml_prompt["-1" if is_open_app_needed else "0"]
    image_list, image_prompt = get_image_list(image_path, element_list, config["IMAGE_MODE"] if not is_open_app_needed else -1)

    action_prompt_2 = re.sub(r"<xml_desc>", xml_prompt, action_prompt_2)
    action_prompt_2 = re.sub(r"<img_desc>", image_prompt, action_prompt_2)

    action_prompt = system_prompt + action_prompt_1 + action_prompt_2

    print(action_prompt)
    return action_prompt, image_list, element_list


def generate_target_app_prompt(package_list, memory, config, description):
    if config["OPEN_APP_METHOD"] == 1:
        package_prompt = "\n".join(package_list)
    else:
        package_list_path = os.path.join(os.path.dirname(__file__), "../prompts/package_list.json")
        with open(package_list_path, "r", encoding="utf-8") as f:
            package_list = json.load(f)
        package_prompt = str(package_list)

    task_prompt = prompts.get_app_prompt
    task_prompt = re.sub(r"<package_list>", package_prompt, task_prompt)
    task_prompt = re.sub(r"<task_desc>", memory.task_memory.cur_task_node.goal_desc, task_prompt)
    task_prompt = re.sub(r"<app_description>", description, task_prompt)
    print(task_prompt)

    return task_prompt


def get_reflect_image_list(image_path, last_image_path, image_mode):
    match image_mode:
        case -1:  # no image
            image_list = []
        case 0:  # only the current image
            image_list = [image_path]
        case 1:  # only the previous image
            image_list = [last_image_path]
        case 2:  # both the previous and current images
            image_list = [last_image_path,image_path]
        case 3:  # concatenate the images, (left: previous, right: current)
            concatenate_image = img_proc.concatenate_images( last_image_path, image_path)
            image_list = [concatenate_image]
        case _:
            raise ValueError("Invalid REFLECT_IMAGE_MODE value.")

    image_prompt = prompts.image_prompt[str(image_mode)]

    return image_list, image_prompt


def generate_validate_and_reflect_prompt(current_ui, last_ui, config, memory, emb_model=None, use_memory=True):
    image_path, xml_path, cur_package, cur_activity = current_ui["image_path"], current_ui["xml_path"], current_ui["activity"][0], current_ui["activity"][1]
    last_image_path, last_xml_path, last_package, last_activity = last_ui["image_path"], last_ui["xml_path"], last_ui["activity"][0], last_ui["activity"][1]

    validate_and_reflect_prompt = prompts.validate_and_reflect_prompt
    validate_and_reflect_prompt = re.sub(r"<current_date>", config["current_date"], validate_and_reflect_prompt)
    validate_and_reflect_prompt = re.sub(r"<current_time>", config["current_time"], validate_and_reflect_prompt)

    cur_task_node = memory.task_memory.cur_task_node

    goal_desc = cur_task_node.goal_desc
    if len(memory.task_memory.output_history) and use_memory:
        output_desc = memory.retrieve_history(memory.task_memory.output_history, memory.task_memory.cur_task_node.goal_desc, emb_model=emb_model)
        goal_desc += f"The historical execution output is {output_desc}. "
        goal_desc += f"You need to use the output to determine whether the current goal is completed"

    validate_and_reflect_prompt = re.sub(r"<final_goal>", config["task"], validate_and_reflect_prompt)
    validate_and_reflect_prompt = re.sub(r"<last_goal>", goal_desc, validate_and_reflect_prompt)
    validate_and_reflect_prompt = re.sub(r"<last_action>", cur_task_node.action, validate_and_reflect_prompt)
    validate_and_reflect_prompt = re.sub(r"<last_round_obs>", cur_task_node.obs, validate_and_reflect_prompt)
    validate_and_reflect_prompt = re.sub(r"<last_round_thought>", cur_task_node.thought, validate_and_reflect_prompt)
    validate_and_reflect_prompt = re.sub(r"<last_activity>", last_activity, validate_and_reflect_prompt)
    validate_and_reflect_prompt = re.sub(r"<last_package>", last_package, validate_and_reflect_prompt)

    validate_and_reflect_prompt = re.sub(r"<current_activity>", cur_activity, validate_and_reflect_prompt)
    validate_and_reflect_prompt = re.sub(r"<current_package>", cur_package, validate_and_reflect_prompt)

    if config["REFLECT_IMAGE_MODE"] == -1:
        element_list = vh_proc.extract_elements(xml_path)
        element_list_clean = vh_proc.clean_element_list(element_list)
        xml_prompt = re.sub(r"<xml_info>", element_list_clean, prompts.xml_prompt["1"])
        last_element_list = vh_proc.extract_elements(last_xml_path)
        last_element_list_clean = vh_proc.clean_element_list(last_element_list)
        last_xml_prompt = re.sub(r"<xml_info>", last_element_list_clean, prompts.xml_prompt["1"])
        xml_instruct_prompt=prompts.xml_instruction_prompt
    else:
        xml_prompt = prompts.xml_prompt["-1"]
        last_xml_prompt = ""
        xml_instruct_prompt=""
    image_list, image_prompt = get_reflect_image_list(image_path, last_image_path, config["REFLECT_IMAGE_MODE"])

    validate_and_reflect_prompt = re.sub(r"<xml_desc>", xml_prompt + last_xml_prompt, validate_and_reflect_prompt)
    validate_and_reflect_prompt = re.sub(r"<img_desc>", image_prompt, validate_and_reflect_prompt)
    validate_and_reflect_prompt = re.sub(r"<xml_instruct>", xml_instruct_prompt, validate_and_reflect_prompt)


    print(validate_and_reflect_prompt)

    return validate_and_reflect_prompt, image_list


def generate_split_goal_prompt(current_ui, config, goal_desc, memory, emb_model=None, use_memory=True):
    image_path, xml_path, cur_package, cur_activity = current_ui["image_path"], current_ui["xml_path"], current_ui["activity"][0], current_ui["activity"][1]

    action_prompts = load_actions()
    system_prompt = prompts.system_prompt
    for action_type in action_prompts.keys():
        system_prompt = re.sub(rf"<{action_type}_action_list>", action_prompts[action_type], system_prompt)

    history = memory.task_memory.task_history.history
    split_prompt = prompts.split_goal_prompt
    split_prompt = re.sub(r"<current_date>", config["current_date"], split_prompt)
    split_prompt = re.sub(r"<current_time>", config["current_time"], split_prompt)

    history_prompt = ""
    if len(history) and use_memory:
        history_prompt = "You can refer to the decomposition of the successful tasks below:\n"
        tar_goal = memory.retrieve_history(history, goal_desc, emb_model=emb_model)

        history_prompt += f"goal:\n{tar_goal}\n"
        history_prompt += "subgoals:\n"
        history_prompt += str([tar.desc for tar in history[tar_goal]]) + "\n"

        if len(history[tar_goal]) <= 1:
            history_prompt=""
        # 如果需要补充history prompt, 可以在这里添加
        # history_prompt += "The details of the subgoals are as follows:\n"
        # for idx, task in enumerate(history[tar_goal]):
        #     history_prompt += f"{idx+1}: \n"
        #     history_prompt += f"goal_desc: {task.desc}\n"
        #     history_prompt += f"observation: {task.obs}\n"
        #     history_prompt += f"thought: {task.thought}\n"
        #     history_prompt += f"action: {task.action}\n"
        
    if len(history_prompt):
        history_prompt = "\n" + history_prompt + "\n"
    
    split_prompt = re.sub(r"<history_prompt>", history_prompt, split_prompt)

    cur_task_node = memory.task_memory.cur_task_node
    
    if cur_task_node.par and use_memory:
        goal_desc += f"The goal is a subgoal of {cur_task_node.par.goal_desc}. "
    if memory.task_memory.last_suc_task_node and use_memory:
        goal_desc += f"The last successful goal is {memory.task_memory.last_suc_task_node.goal_desc}. "
        goal_desc += f"The last action is {memory.task_memory.last_suc_task_node.action}. "
    if memory.task_memory.last_fail_task_node and use_memory:
        goal_desc += f"The last failed goal is {memory.task_memory.last_fail_task_node.goal_desc}. "
        goal_desc += f"The action is {memory.task_memory.last_fail_task_node.action}. "

    if len(memory.task_memory.output_history) and use_memory:
        key = memory.retrieve_history(memory.task_memory.output_history, memory.task_memory.cur_task_node.goal_desc, emb_model=emb_model)
        output_desc = memory.task_memory.output_history[key]
        goal_desc += f"The historical execution output is {output_desc}. "
        goal_desc += f"You need to use the output to determine how to split the current goal. "

    split_prompt = re.sub(r"<goal_desc>", goal_desc[:-2], split_prompt)
    split_prompt = re.sub(r"<current_activity>", cur_activity, split_prompt)
    split_prompt = re.sub(r"<current_package>", cur_package, split_prompt)

    if xml_path and config["SPLIT_IMAGE_MODE"] !=0:
        element_list = vh_proc.extract_elements(xml_path)
        element_list_clean = vh_proc.clean_element_list(element_list)
        xml_prompt = re.sub(r"<xml_info>", element_list_clean, prompts.xml_prompt["1"])
        xml_instruct_prompt = prompts.xml_instruction_prompt
    else:
        element_list = []
        element_list_clean = ""
        xml_prompt = prompts.xml_prompt["0"]
        xml_instruct_prompt = ""
    image_list, image_prompt = get_image_list(image_path, element_list, config["SPLIT_IMAGE_MODE"])

    split_prompt = re.sub(r"<xml_desc>", xml_prompt, split_prompt)
    split_prompt = re.sub(r"<img_desc>", image_prompt, split_prompt)
    split_prompt = re.sub(r"<xml_instruct>", xml_instruct_prompt, split_prompt)

    split_prompt = system_prompt + split_prompt
    print(split_prompt)

    return split_prompt, image_list
