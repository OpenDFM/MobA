import pdb
import re
import sys

sys.path.append('../..')
from moba.utils.utils import print_with_color, user_check

def process_response(response,value_list):
    response = response.strip()
    response = "\n\n"+response
    for value in value_list:
        first_param_name = value
        first_param = re.findall(rf"[*#\n ]*{first_param_name}[*# ]*:[*# ]*", response)
        for i in first_param:
            response = response.replace(i, f"\n\n{first_param_name}:\n\n")
    return response + '\n\n'

def parse_str(response, value):
    match=re.findall(rf"\n\n{value}:\n\n(.+?)\n\n", response, re.DOTALL)
    if match:
        return match[0].strip()
    return ""


def parse_target_action_plain_response(response, logger=None):
    response = process_response(response,["Observation","Thought","Status","Action","Message"])

    Observation = parse_str(response, "Observation")
    Thought = parse_str(response, "Thought")
    Status_str = parse_str(response, "Status")
    Action = parse_str(response, "Action")
    Message = parse_str(response, "Message")

    Status = False
    if (Status_str.lower() == "complete"):
        Status = True
    action_list = parse_action(Action)

    print_with_color("👀 Observation:", "blue", logger=logger)
    print_with_color(Observation, "blue", logger=logger)
    print_with_color("🤔 Thought: ", "yellow", logger=logger)
    print_with_color(Thought, "yellow", logger=logger)
    print_with_color("🚦 Status: ", "yellow", logger=logger)
    print_with_color(Status, "yellow", logger=logger)
    print_with_color("🕹️ Action: ", "cyan", logger=logger)
    print_with_color(Action, "cyan", logger=logger)
    print_with_color("📨 Message: ", "cyan", logger=logger)
    print_with_color(Message, "cyan", logger=logger)

    return Observation, Thought, Status, Action, action_list, Message



def parse_target_action_response(response, logger=None):
    response = process_response(response,["Observation","Thought","CanComplete","Action","Message"])

    Observation = parse_str(response, "Observation")
    Thought = parse_str(response, "Thought")
    CanComplete_str = parse_str(response, "CanComplete")
    Action = parse_str(response, "Action")
    Message = parse_str(response, "Message")

    CanComplete_str=CanComplete_str.lower()
    match  CanComplete_str:
        case "true":
            CanComplete = 1
        case "possibly":
            CanComplete = 0.5
        case _:
            CanComplete = 0

    action_list = parse_action(Action)

    print_with_color("👀 Observation:", "blue", logger=logger)
    print_with_color(Observation, "blue", logger=logger)
    print_with_color("🤔 Thought: ", "yellow", logger=logger)
    print_with_color(Thought, "yellow", logger=logger)
    print_with_color("🚦 CanComplete: ", "yellow", logger=logger)
    print_with_color(CanComplete, "yellow", logger=logger)
    print_with_color("🕹️ Action: ", "cyan", logger=logger)
    print_with_color(Action, "cyan", logger=logger)
    print_with_color("📨 Message: ", "cyan", logger=logger)
    print_with_color(Message, "cyan", logger=logger)

    return Observation, Thought, CanComplete, Action, action_list, Message


def parse_target_app_response(response, logger=None):
    response = process_response(response,["Action"])

    Action = parse_str(response, "Action")
    action_list = parse_action(Action)

    print_with_color("🚦Get APP: ", "cyan", logger=logger)
    print_with_color(Action, "cyan", logger=logger)

    return Action, action_list


def parse_action(Action, logger=None):
    try:

        action = Action.split("(")[0]  # action_function
        print_with_color("Function: parse_response", "green", pad=100)
        print_with_color(f"Action: {action.upper()}", "yellow")

        # TODO: user check (see old code before 20240903 for reference)

        match action.upper():
            case "OPEN_APP":
                """
                OpenApp(description: Optional[str])
                return: ["OPEN_APP", package_name]
                """
                args = re.findall(r"(?i)Open_App\((.*?)\)", Action)[0]
                args = args.split(",")
                package_name = args[0].strip()
                activity_name = args[1].strip() if len(args) > 1 else ""
                return ["OPEN_APP", package_name, activity_name]
            case "CLOSE_APP":
                """
                CloseApp(package_name: Optional[str])
                return: ["CLOSE_APP", package_name]
                """
                package_name = re.findall(r"(?i)Close_App\((.*?)\)", Action)[0].strip()
                return ["CLOSE_APP", package_name]
            case "CLICK":
                """
                Click(element_index: int)
                Return: ["CLICK", element_index]
                """
                return ["CLICK", int(re.findall(r"(?i)Click\((.*?)\)", Action)[0])]
            case "CLICK_BY_COORDINATE":
                """
                Click_by_Coordinate(x: int, y: int)
                Return: ["CLICK_BY_COORDINATE", x, y]
                """
                # 提取x和y坐标
                coordinates = re.findall(r"(?i)Click_by_Coordinate\((.*?),(.*?)\)", Action)[0]
                x = int(coordinates[0].strip())
                y = int(coordinates[1].strip())
                return ["CLICK_BY_COORDINATE", x, y]
            case "DOUBLE_CLICK":
                """
                Double_Click(element_index: int)
                Return: ["DOUBLE_CLICK", element_index]
                """
                return ["DOUBLE_CLICK", int(re.findall(r"(?i)Double_Click\((.*?)\)", Action)[0])]
            case "LONG_PRESS":
                """
                Long_Press(element_index: int)
                Return: ["LONG_PRESS", element_index]
                """
                return ["LONG_PRESS", int(re.findall(r"(?i)Long_Press\((.*?)\)", Action)[0])]
            case "SWIPE":
                """
                Swipe(direction:str, distance:str)
                Return: ["SWIPE", direction, distance]

                Swipe(2, 'left', 'long')
                Expect return value: ['SWIPE', 'left', 'long']
                """
                match = re.match(r"(?i)Swipe\('(\w+)', '(\w+)'\)", Action)
                if match:
                    direction = match.group(1)
                    distance = match.group(2)
                    return ["SWIPE", direction, distance]
                else:
                    return None
            case "SCROLL":
                """
                Scroll(element_index:int, direction:str, distance:str)
                Return: ["SCROLL", element_index, direction, distance]

                Scroll(2, 'left', 'medium')
                Expect return value: ['SWIPE', 2, 'left', 'medium']
                """
                match = re.match(r"(?i)Scroll\((\d+), '(\w+)', '(\w+)'\)", Action)
                if match:
                    element_index = int(match.group(1))
                    direction = match.group(2)
                    distance = match.group(3)
                    return ["SCROLL", element_index, direction, distance]
                else:
                    return None
            case "TYPE":
                """
                Type(text: str)
                Return: ["TYPE", text]

                Type('settings')
                Expect return value: ['TYPE', 'settings']
                """
                match = re.match(r"(?i)Type\('(.+?)'\)", Action)
                if match:
                    text = match.group(1)
                    return ["TYPE", text]
                else:
                    # PRINT Error
                    print_with_color(f"ERROR: The format of the action space is not correct!", "red")
                    return None
            case "BOX_INPUT":
                """
                Box_Input(element_index:int, text: str)
                Return: ["BOX_INPUT", element_index, text]

                Box_Input(2, 'settings')
                Expect return value: ['BOX_INPUT', 2, 'settings']
                ""/''
                """
                match = re.match(r"(?i)Box_Input\((\d+), ['\"](.+?)['\"]\)", Action)
                if match:
                    element_index = int(match.group(1))
                    text = match.group(2)
                    return ["BOX_INPUT", element_index, text]
                else:
                    print_with_color(f"ERROR: The format of the action space is not correct!", "red")
                    return None
            case "BUY_TRAIN_TICKET":
                """
                Buy_Train_Ticket(departure: str, destination: str)
                Return: ["BUY_TRAIN_TICKET", departure, destination]

                Buy_Train_Ticket('Beijing', 'Shanghai')
                Return value: ['BUY_TRAIN_TICKET', 'Beijing', 'Shanghai']
                """
                args = re.findall(r"(?i)Buy_Train_Ticket\((.*?)\)", Action)[0]
                pdb.set_trace()
                args = args.split(",")
                departure = args[0].replace("'", "").replace('"', "").strip()
                destination = args[1].replace("'", "").replace('"', "").strip()
                return ["BUY_TRAIN_TICKET", departure, destination]

            case "BACK":
                return ["BACK"]

            case _:
                print_with_color(f"ERROR: Undefined action {action}!", "red")
                return ["ERROR"]
    except Exception as e:
        print_with_color(f"ERROR: an exception occurs while parsing the response: {e}", "red", logger=logger, log_level="error")


def parse_validate_and_reflect_response(response, logger=None):
    response = process_response(response,["Thought","Subgoal_Status","Goal_Status","Reflection"])

    Thought = parse_str(response, "Thought")
    Reflection = parse_str(response, "Reflection")
    Subgoal_Status_str = parse_str(response, "Subgoal_Status")
    Goal_Status_str = parse_str(response, "Goal_Status")
    Goal_Status = False
    if (Goal_Status_str.strip().lower() == "success"):
        Goal_Status = True
        Subgoal_Status = True
    else:
        Subgoal_Status = False
        if (Subgoal_Status_str.strip().lower() == "success"):
            Subgoal_Status = True

    print_with_color("🤔 Thought: ", "yellow", logger=logger)
    print_with_color(Thought, "yellow", logger=logger)
    print_with_color("🚦 Subgoal_Status: ", "cyan", logger=logger)
    print_with_color(Subgoal_Status_str, "cyan", logger=logger)
    print_with_color("🚦 Goal_Status: ", "cyan", logger=logger)
    print_with_color(Goal_Status_str, "cyan", logger=logger)
    print_with_color("🔍 Reflection: ", "magenta", logger=logger)
    print_with_color(Reflection, "magenta", logger=logger)

    return Thought, Subgoal_Status, Goal_Status, Reflection


def parse_split_goal_response(response, logger=None):
    response = process_response(response,["Observation","Thought","Subgoals"])

    Observation = parse_str(response, "Observation")
    Thought = parse_str(response, "Thought")
    Subgoals = parse_str(response, "Subgoals")

    import ast
    if Subgoals.lstrip()[0] == '[':
        Subgoals = ast.literal_eval(Subgoals)
    else:
        Subgoals = [Subgoals]

    print_with_color("👀 Observation:", "blue", logger=logger)
    print_with_color(Observation, "blue", logger=logger)
    print_with_color("🤔 Thought: ", "yellow", logger=logger)
    print_with_color(Thought, "yellow", logger=logger)
    print_with_color("🚦 Subgoals: ", "cyan", logger=logger)
    print_with_color(Subgoals, "cyan", logger=logger)

    return Observation, Thought, Subgoals

