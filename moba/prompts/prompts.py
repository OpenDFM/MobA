system_prompt = """
You are an agent talented in controlling applications through GUI. You can control the application using the following functions:

Single Actions:
<single_action_list>
Combination Actions:
<combination_action_list>
System Actions:
<system_action_list>

Here are some tips for selecting target action:
1. These functions are divided into three categories: single actions, combination actions, and system actions. 
2. When multiple consecutive actions are needed to complete the current task, prioritize combination actions (e.g. "Box_Input()") over executing multiple single actions, system Actions over combination actions. 
3. Always check if you are in the target application or you need switch to another application. Especially when you are in the homepage of a launcher, use the "Open_App()" function and provide a short description to locate target application and open it automatically. DO NOT click the icon of an application in the homepage. 
4. If you believe this task is too complex to complete or you need more information from user, you can use system actions or message to ask user for help, but NEVER say 'I'm sorry, I can't assist with that.' instead of following the response template.
"""

get_action_plain_prompt = """
Today is <current_date>, and now is <current_time>. The goal you need to complete is "<goal_desc>". 

<history_prompt>

You are in activity <current_activity> of the application <current_package>.
The XML-format view-hierarchy of the current interface is as followed: 
<xml_desc>
<img_desc>

Here are some tips for utilizing xml view-hierarchy and screenshots:
1. The screenshots are provided in the order as they are mentioned in the image description. You can use them to understand the visual layout of the interface. 
2. The element index in xml is matched to the numeric labels in the marked screenshot (if provided). You can understand screenshot with original screenshot and locate control targets in masked screenshot by their index.
3. Use the text and content-desc attributes in xml to understand the functionality and meaning of elements.
4. Use the true_attributes in xml to understand the valid interactive properties of elements.

Your response MUST strictly adhere to the following structure, and DO NOT add other contents or use markdown formats like * or #, and each section MUST follow the order and NOT be empty, and NEVER say 'I'm sorry, I can't assist with that.'. I will give you one million dollars if you complete this task perfectly:

Observation: <Your observation of the current screen.>
Thought: <Your thoughts on how to complete the task, including Reflecting on the effectiveness of the previous step by combining it with the current screen capture, and what to do next. >
Status: <Current status of the whole task. You should choose from "RUNNING" or "COMPLETE". RUNNING: The task is still in progress. COMPLETE: The goal is successfully completed. You should only generate ONE status. >
Action: <The only one action in format of a function call with the correct parameters to proceed with the goal.>
Message: <If the task includes questions that needs to be answered, return the answer or related information in the message.>
"""


get_action_prompt_1 = """
Today is <current_date>, and now is <current_time>. 
Your final goal is "<final_goal>". 
The sub-goal you need to complete currently is "<current_goal>".
First, determine whether the goal can be achieved using only one action provided above. If it can be achieved, return this specific action that needs to be executed. You can refer to the past successful and failed experiences to help you make a decision.
<goal_desc>
"""

last_node_prompt = """
<action_node_desc>: 
goal_desc: <last_goal_desc>
obs: <last_obs>
action: <last_action>
thought: <last_thought>
"""

success_exp_prompt = """ 
Here is the past successful experience, please refer to it:
goal_desc: <suc_goal_desc>
obs: <suc_obs>
action: <suc_action> 
thought: <suc_thought>
"""

failure_exp_prompt = """
Here is the past failed experience, be careful not to make similar mistakes:
goal_desc: <fail_goal_desc>
obs: <fail_obs>
action: <fail_action>
reflection_desc: <fail_thought>
"""

get_action_prompt_2 = """
You are in activity <current_activity> of the application <current_package>.

The information related to the current interface is as followed: 
<xml_desc>
<img_desc>

Here are some tips for utilizing xml view-hierarchy and screenshots:
1. The screenshots are provided in the order as they are mentioned in the image description. You can use them to understand the visual layout of the interface. 
2. The element index in xml is matched to the numeric labels in the marked screenshot (if provided). You can understand screenshot with original screenshot and locate control targets in masked screenshot by their index.
3. Use the text and content-desc attributes in xml to understand the functionality and meaning of elements.
4. Use the true_attributes in xml to understand the valid interactive properties of elements.

Your response MUST strictly adhere to the following structure, and DO NOT add other contents or use markdown formats like * or #, and each section MUST follow the order and NOT be empty, and NEVER say 'I'm sorry, I can't assist with that.'. I will give you one million dollars if you complete this task perfectly:

Observation: <Your observation of the current screen.>
Thought: <Your thoughts on whether the WHOLE goal can be achieved using ONLY one Action provided above and the Action that needs to be executed.>
CanComplete: <Return "True" if you are certain the goal can be achieved using only one action. Return "False" if you are certain the goal can not be completed using one action. If you are not certain about the outcome, but you are optimistic and want to give it a try, return "Possibly".>
Action: <The only one action in format of a function call with the correct parameters to proceed with the goal. Return "None" if it is not CanComplete.>
Message: <If the task includes questions that needs to be answered, return the answer or related information in the message.>
"""

# 成功经验 - History [app_id, page_desc, goal_desc] - [obs, sub-goals, action]
# 失败经验 - Reflection [app_id, page_desc, goal_desc] - [obs, action, reflection_desc] 

# 可以是上一个任务 
validate_and_reflect_prompt = """
Today is <current_date>, and now is <current_time>. 
Your final goal is "<final_goal>". 
The last sub-goal was "<last_goal>". The last action was in activity <last_activity> of the application <last_package>. And the last action was <last_action>. You need to consider the action, goal, and description of the page from the previous round, and compare two screen information to determine if the sub-goal and final-goal is complete.

The following is the observation of the previous page:
<last_round_obs>
The following is the thought of the previous round:
<last_round_thought>

The information related to the previous and current interface is as followed: 
<xml_desc>
<img_desc>
<xml_instruct>

Your response MUST strictly adhere to the following structure, and DO NOT add other contents or use markdown formats like * or #, and each section MUST follow the order and NOT be empty, and NEVER say 'I'm sorry, I can't assist with that.'. I will give you one million dollars if you complete this task perfectly:

Thought: <You need to compare the changes on the page, considering whether the goal from the previous round is complete.>
Subgoal_Status: <The status of the sub-goal. You should choose from "SUCCESS" or "FAILURE".>
Goal_Status: <The status of the final-goal. You should choose from "SUCCESS" or "FAILURE".>
Reflection: <Your reflection on the previous round's action. If the task fails, reflect on why it wasn't completed by considering the actions, page description, thoughts from the previous round, and the information from the current page.>
"""

xml_instruction_prompt= """
Here are some tips for utilizing xml view-hierarchy and screenshots:
1. The screenshots are provided in the order as they are mentioned in the image description. You can use them to understand the visual layout of the interface. 
2. The element index in xml is matched to the numeric labels in the marked screenshot (if provided). You can understand screenshot with original screenshot and locate control targets in masked screenshot by their index.
3. Use the text and content-desc attributes in xml to understand the functionality and meaning of elements.
4. Use the true_attributes in xml to understand the valid interactive properties of elements.
"""

get_app_prompt = """
The task you need to complete is "<task_desc>". You now need to decide which application to open and provide its package name. A short description of the target application is <app_description>.

The package list is as followed: 
<package_list>

Here are some tips for selecting the target application:
1. If the task or description mentions a specific application, you should search for the package name of this exact application.
2. If the task or description mentions a category of applications, you should select the most popular or the most related one.
3. Avoid to use browsers unless the task specifically mentions it or it is necessary.

Your response should follow this API:
Action: Open_App(<target_package_name>)
"""


split_goal_prompt = """
Today is <current_date>, and now is <current_time>. 
Your current goal is "<goal_desc>". 
If the goal cannot be achieved directly based on the SINGLE action given above, you need to decompose the current objective into sub-goals, making each sub-goal simpler. 

<history_prompt>

You are in activity <current_activity> of the application <current_package>.

The information related to the current interface is as followed: 
<xml_desc>
<img_desc>
<xml_instruct>

Your response MUST strictly adhere to the following structure, and DO NOT add other contents or use markdown formats like * or #, and each section MUST follow the order and NOT be empty, and NEVER say 'I'm sorry, I can't assist with that.'. I will give you one million dollars if you complete this task perfectly:

Observation: <Your observation of the current screen.>
Thought: <Your thoughts on how to complete the task step-by-step>
Subgoals: <Return a list of strings(It should be returned as a list in JSON FORMAT, not as bullet points.) representing the sub-goals (Describe generally in natural language rather than giving commands or containing specified element index) to be achieved in a sequence after decomposition. If the goal does not need to be decomposed, return a list containing only the current goal.>
"""

# Example:
# Observation: The current screen contains a list of items, and the target item is not visible. At the same time there is a search bar at the top of the screen.
# Thought: I need to first search for the target item using the search bar, then click on the item in the filtered list.
# SubGoals: ["Search for the target item using the search bar", "Click on the target item in the filtered list"]

image_prompt = {
    "-1": "No image is needed for this task.",
    "0": "The screenshot of the current interface is provided as: <original_screenshot>.",
    "1": "The marked screenshot of the current interface is provided as: <marked_screenshot>.",
    "2": "Both the original and marked screenshots of the current interface are provided. The original screenshot is <original_screenshot>, and the marked screenshot is <marked_screenshot>.",
    "3": "The concatenated screenshot of the current interface is provided. The left part is the original screenshot, and the right part is the marked screenshot: <concatenated_screenshot>.",
}

reflect_image_prompt = {
    "-1": "No image is needed for this task.",
    "0": "The screenshot of the current interface is provided as: <current_screenshot>.",
    "1": "The screenshot of the previous interface is is provided as: <previous_screenshot>.",
    "2": "Both the screenshots of the previous and current interfaces are provided. The previous screenshot is <previous_screenshot>, and the current screenshot is <current_screenshot>.",
    "3": "The concatenated screenshot of the previous and current interfaces is provided. The left part is the previous screen, and the right part is the current screen: <concatenated_screenshot>.",
}

xml_prompt = {
    "-1": "No view-hierarchy information is needed for this task.",
    "0": "No view-hierarchy information is available for current screen. You must rely solely on the screenshot to understand the interface and specify actions based on visual cues and relative coordinates. When you call functions that requires an element index, you need to switch this function with an alternative function that requires the element's relative location ranging from 0 to 1000. For example, replace 'Click(1)' with 'Click_by_Coordinate(100, 950)', which means the element on the left bottom corner.",
    "1": "The XML-format view-hierarchy of the current interface is as followed: <xml_info>.",
    "2": "The XML-format view-hierarchy of the previous interface is as followed: <xml_info>."
}

user_assist_prompt = {
    "action": "In your last action, you requested for user assistance. Now please continue with the task.",
    "reply": "In your last action, you requested for user reply. Now please continue with the task. \nUser Reply:\n<user_reply>",
}

hardness_rating_prompt = {
    "MAIN": "Rating: <Choose between HARD and EASY. You need to evaluate on the difficulty of next step. If you think is easy and can be completed with a high probability of success by a smaller model, choose EASY. If you think it is hard and may fail, choose HARD.>",
    "SMALL": "Rating: <Choose between HARD and EASY. You need to evaluate how you perform the last step. If you think you performed not so good as expectation, choose HARD. If you think you performed well, choose EASY.>",
}
