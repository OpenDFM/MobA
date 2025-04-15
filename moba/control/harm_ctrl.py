import os  # used for creating directory
import pdb
import re
import subprocess
import time

import sys

from moba.process import vh_proc
from moba.prompts.prompts import success_exp_prompt

sys.path.append('../..')  # Add the path to the project to the sys.path, in case you want to test this script independently
from moba.utils.utils import print_with_color, user_check
from moba.control.ctrl import BaseController


def command_executor(command, max_retry=3):
    """
    Execute command and return the result
    :param command: shell command
    :param max_retry: maximum number of retries
    :return: execution success, result
    """
    i = 0
    while True:
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            print_with_color(f"Command executed: {command}", "green")
            return True, result.stdout.strip()

        print_with_color(f"Error occurred executing command: {command}", "red")
        print_with_color(result.stderr, "red")

        i += 1
        if i > max_retry:
            return False, None

        time.sleep(i)

        print_with_color("Retry executing", "yellow")


def get_hdc_devices():
    """
    List all connected Harmony devices
    :return: list of devices
    """
    device_list = []
    command = "hdc list targets"
    execution_success, result = command_executor(command)
    if execution_success:
        device_list = result.split("\n")
    return device_list


def select_hdc_devices(device_list):
    """
    Select an Harmony device from the list
    :param device_list: list of devices
    :return: selected device name
    """
    if not device_list:
        print_with_color("ERROR: No device found!", "red")
        sys.exit()
    print_with_color(f"List of devices attached:", "yellow")
    for i, device in enumerate(device_list):
        print_with_color(f"({i + 1})\t{device}", "yellow")
    if len(device_list) == 1:
        device_index = 1
        device = device_list[0]
    else:
        while True:
            print_with_color("Please choose the Harmony device by entering its index:", "blue")
            device_index = input()
            if isinstance(device_index, int) and 0 < device_index <= len(device_list):
                device = device_list[device_index - 1]
                break
    print_with_color(f"Device selected: ({device_index}) {device}", "green")
    return device


def find_element_by_index(element_list, index):
    """
    Find element by index
    :param element_list: list of elements
    :param index: index of the element
    :return: element
    """
    for elem in element_list:
        if elem.index == index:
            return elem
    return None


class HarmonyController(BaseController):
    def __init__(self, config, device):
        self.config = config
        self.device = device
        self.width = self.get_screen_size()[0]
        self.height = self.get_screen_size()[1]
        self.unicode_input = False
        self.default_ime = ""
        self.hdc_max_retry = config["COMMAND_MAX_TRY"]
        self.package_list = self.get_application_list()

    def get_application_list(self, system=True, third_party=True):
        """
        Get the list of installed applications on the Harmony device
        :return: list of applications
        """
        if system and third_party:
            command = f"hdc -t {self.device} shell bm dump -a"
        elif system:
            # hdc does not support selection
            command = f"hdc -t {self.device} shell bm dump -a"
        elif third_party:
            # hdc does not support selection
            command = f"hdc -t {self.device} shell bm dump -a"
        success, result = command_executor(command, self.hdc_max_retry)
        if success:
            # print(result)
            result=result.split("\n")[1:]
            return [r.strip() for r in result]
        else:
            return []

    def install_application(self, hap_path):
        """
        Install an application on the Harmony device
        :param hap_path: path to the hap file
        :return: execution success
        """
        def parse_hap(hap_path):
            import zipfile
            import json
            import os
            import shutil
            import tempfile
            
            if not zipfile.is_zipfile(hap_path):
                return "Unknown"
            
            temp_dir = tempfile.mkdtemp()
            
            try:
                with zipfile.ZipFile(hap_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                config_path = os.path.join(temp_dir, 'config.json')
                if not os.path.exists(config_path):
                    package_name = "Unknown"
                    return package_name
                
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                package_name = config.get('app', {}).get('bundleName', 'Unknown')
            finally:
                shutil.rmtree(temp_dir)
            return package_name
        
        package_name = parse_hap(hap_path)
        
        print_with_color(f"Installing application {package_name} from {hap_path}", "yellow")
        command2 = f"hdc -t {self.device} install {hap_path}"
        success, result = command_executor(command2)
        if success:
            print_with_color(f"Application {package_name} installed", "green")
            return package_name
        else:
            return None

    def uninstall_application(self, package_name):
        """
        Uninstall an application on the Harmony device
        :param package_name: package name of the application
        :return: execution success
        """
        print_with_color(f"You are going to uninstall the application: {package_name}", "red")
        print_with_color("Are you sure you want to uninstall the application? (Y/N)", "yellow")
        if not user_check():
            print_with_color("Uninstallation canceled", "yellow")
            return False
        command = f"hdc -t {self.device} uninstall {package_name}"
        success, result = command_executor(command)
        return success

    def open_application(self, package_name, activity_name=None):
        """
        Open an application on the Android device
        :param package_name: package name of the application (in HarmonyOS, it is the same as the bundle name)
        :param activity_name: activity name of the application (in HarmonyOS, it is the same as the ability name)
        :return: execution success
        """
        if not activity_name:
            command1= f"hdc -t {self.device} shell bm dump -n {package_name} | findstr \\\"mainAbility\\\": "
            success, result = command_executor(command1)
            if success:
                activity_name = result.split('"')[3]
            else:
                print_with_color("ERROR: Unable to get the main activity name", "red")
                return False
            
        command2= f"hdc -t {self.device} shell aa start -a {activity_name} -b {package_name}"
        
        success, result = command_executor(command2)
        return success

    def close_application(self, package_name):
        """
        Close an application on the Harmony device
        :param package_name: package name of the application
        :return: execution success
        """
        if not package_name:
            package_name, _ = self.get_activity()
        command = f"hdc -t {self.device} shell aa force-stop {package_name}"
        success, result = command_executor(command)
        return success

    def get_screen_size(self):
        """
        Get the screen size of the Harmony device
        :return: width, height
        """
        command = f"hdc -t {self.device} shell hidumper -s RenderService -a screen | findstr activeMode"
        success, result = command_executor(command)
        if success:
            size_str = result.split("activeMode: ")[1].split(", refreshrate")[0].strip()
            width, height = size_str.split("x")
            return int(width), int(height)
        else:
            print_with_color("Error getting screen size", "red")
            return None, None

    def get_screenshot(self, prefix, save_dir):
        """
        Get a screenshot of the Harmony device and save it on the computer
        :param prefix: prefix for the screenshot file name
        :param save_dir: directory to save the screenshot
        :return: path to the screenshot
        """
        # Check if the save_dir exists, if not, create it
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        command = f"hdc -t {self.device} shell snapshot_display -f /data/local/tmp/{prefix}.jpeg"
        command2 = f"hdc -t {self.device} file recv /data/local/tmp/{prefix}.jpeg {save_dir}/{prefix}.jpeg "
        command3 = f"hdc -t {self.device} shell rm -f /data/local/tmp/{prefix}.jpeg"
        success, result = command_executor(command, 1)
        if success:
            success, result = command_executor(command2, 1)
        if success:
            success, result = command_executor(command3, 1)
        else:
            # exit()
            # if no screenshot is generated, return None
            return None
        return os.path.normpath(f"{save_dir}/{prefix}.png")

    def get_xml(self, prefix, save_dir):
        """
        Get the XML file of the current screen on the Harmony device
        :param prefix: prefix for the XML file name
        :param save_dir: directory to save the XML file
        :return: path to the XML file
        """
        # Check if the save_dir exists, if not, create it
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        command = f"hdc -t {self.device} shell uitest dumpLayout -p /data/local/tmp/{prefix}.xml"
        command2 = f"hdc -t {self.device} pull /data/local/tmp/{prefix}.xml {save_dir}"
        command3 = f"hdc -t {self.device} shell rm -f /data/local/tmp/{prefix}.xml"
        success, result = command_executor(command, 1)
        if success:
            success, result = command_executor(command2, 1)
        if success:
            success, result = command_executor(command3, 1)
        else:
            # exit()
            # if no xml file is generated, return None
            return None
        return os.path.normpath(f"{save_dir}/{prefix}.xml")

    def get_activity(self):
        """
        Get the current activity name (ability)
        :return: activity name
        """
        command = f"hdc -t {self.device} shell aa dump -l | findstr 'Mission ID'"
        success, result = command_executor(command)
        try:
            info = re.findall(r"#\[#(.*?)]", result)
            info_list = info[0].split(":")
            package_name = info_list[0].strip()
            activity_name = info_list[-1].strip()
            return package_name, activity_name
        except:
            return "", ""

    # -----------------Actions---------------------------
    # ---------atomic actions-----------
    def locate_element(self, element_list, text="", resource_id="", class_name=""):
        """
        Locate an element by text, resource_id, class_name, package, or content_desc
        :param text: text or content-desc of the element
        :param resource_id: resource_id of the element
        :param class_name: class of the element
        :return: element
        """

        selected_elements = []

        for elem in element_list:
            if ((text in elem.attributes["text"]) or (text in elem.attributes["content-desc"])) and (resource_id in elem.id) and (class_name in elem.attributes["class"]):
                selected_elements.append(elem)
                break

        if not selected_elements:
            x, y = -1, -1
        else:
            x, y = selected_elements[0].center[0], selected_elements[0].center[1]

        print(x, y)

        return x, y

    def click_by_coordiate(self, x, y):
        """
        Tap on the screen by coordinate
        :param x: x coordinate
        :param y: y coordinate
        :return: execution success
        """
        command = f"hdc -t {self.device} uitest uiInput click {x} {y}"
        success, result = command_executor(command)

    def long_press_by_coordinate(self, x, y, duration=1000):
        """
        Long press on the screen by coordinate
        :param x: x coordinate
        :param y: y coordinate
        :param duration: duration of long press
        :return: execution success
        """
        command = f"hdc -t {self.device} shell uitest uiInput longClick {x} {y} "
        success, result = command_executor(command)

    # todo:tap_by_element

    def swipe(self, x, y, direction, distance="MEDIUM", duration=1000):
        """
        Swipe on the screen
        :param x: x coordinate
        :param y: y coordinate
        :param direction: direction of swipe
        :param distance: distance of swipe
        :param duration: duration of swipe
        :return: execution success
        """
        # distance: short, medium, long, or a number
        # short: 1/10
        # medium: 1/5 height
        # long: 1/2 height
        if distance.upper() == "LONG":
            distance = int(self.height / 2)
        elif distance.upper() == "MEDIUM":
            distance = int(self.height / 5)
        elif distance.upper() == "SHORT":
            distance = int(self.height / 10)
        elif isinstance(distance, int):
            pass
        else:
            print_with_color(f"ERROR: Invalid distance: {distance}", "red")
            
        swipe_speed=min(40000,max(200,distance/(duration/1000)))

        if direction.upper() == "UP":
            command = f"hdc -t {self.device} shell uitest uiInput swipe {x} {y} {x} {y - distance} {swipe_speed}"
        elif direction.upper() == "DOWN":
            command = f"hdc -t {self.device} shell uitest uiInput swipe {x} {y} {x} {y + distance} {swipe_speed}"
        elif direction.upper() == "LEFT":
            command = f"hdc -t {self.device} shell uitest uiInput swipe {x} {y} {x - distance} {y} {swipe_speed}"
        elif direction.upper() == "RIGHT":
            command = f"hdc -t {self.device} shell uitest uiInput swipe {x} {y} {x + distance} {y} {swipe_speed}"
        else:
            print_with_color(f"ERROR: Invalid direction: {direction}", "red")

        success, result = command_executor(command)

    def drag(self, start_x, start_y, end_x, end_y, duration=1000):
        """
        Drag from start coordinates to end coordinates on the screen
        :param start_x: x coordinate of start point
        :param start_y: y coordinate of start point
        :param end_x: x coordinate of end point
        :param end_y: y coordinate of end point
        :param duration: duration of drag
        :return: execution success
        """
        
        distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
        swipe_speed = min(40000, max(200, distance / (duration / 1000)))
        
        command = f"hdc -t {self.device} shell uitest uiInput drag  {start_x} {start_y} {end_x} {end_y} {swipe_speed}"
        success, result = command_executor(command)

    def swipe_precise(self, start, end, duration=400):
        """
        Swipe precisely from start coordinates to end coordinates on the screen
        :param start: start coordinates
        :param end: end coordinates
        :param duration: duration of swipe
        :return: execution success
        """
        start_x, start_y = start
        end_x, end_y = end
        distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
        swipe_speed = min(40000, max(200, distance / (duration / 1000)))
    
        command = f"hdc -t {self.device} shell uitest uiInput swipe {start_x} {start_y} {end_x} {end_y} {swipe_speed}"
        success, result = command_executor(command)

    def type_text(self, text, x=self.width/2, y=self.height/2):
        """
        Type text
        :param text: text to be typed
        :return: execution success
        """
        command = f"hdc -t {self.device} shell uitest uiInput inputText {x} {y} '{text}'"
        success, result = command_executor(command)

    def clear_text(self,del_length=100):
        command_1 = f"hdc -t {self.device} shell input keyevent KEYCODE_MOVE_END"
        success, result = command_executor(command_1)

        for _ in range(del_length):
            command_2 = f"hdc -t {self.device} shell input keyevent KEYCODE_DEL"
            success, result = command_executor(command_2)

    def back(self):
        """
        Press the back button
        :return: execution success
        """
        command = f"adb -s {self.device} shell input keyevent KEYCODE_BACK"
        success, result = command_executor(command)

    # ---------combination of actions-----------
    def box_input(self, x, y, text,del_length=100):
        """
        Perform a combination of actions to click on the search box, type text in it, and click search
        :param x: x coordinate of the search box
        :param y: y coordinate of the search box
        :param text: text to be typed in the search box
        :return: execution success
        """
        # Tap on the search box and type the text
        self.click_by_coordiate(x, y)
        time.sleep(0.5)
        self.clear_text(del_length+10)
        self.type_text(text)

        # Click the search button(keyboard enter)
        command = f"adb -s {self.device} shell input keyevent KEYCODE_ENTER"
        success, result = command_executor(command)

    # ---------actions from the parsed model response-----------
    def execute_action(self, param, element_list):
        """
        Execute actions from the parsed model response
        :param param: action parameters
        :param element_list: list of elements
        """
        # Handle cases such as 'ERROR', 'FINISH', and undefined situations in the external logic.
        # execute_action only handle specific actions

        action = param[0]

        print("------------Function: execute_action-------------")
        print("Param:", param)

        match action:
            case "OPEN_APP":
                """
                ['OPEN_APP', 'com.tencent.mm', '.ui.LauncherUI']
                """
                package_name = param[1]
                activity_name = param[2]
                self.open_application(package_name, activity_name)
            case "CLOSE_APP":
                """
                ['CLOSE_APP', 'com.tencent.mm']
                """
                package_name = param[1]
                self.close_application(package_name)
            case "CLICK":
                """
                ['CLICK', 2]
                """
                element_index = param[1]
                # elem = element_list[element_index - 1]
                elem = find_element_by_index(element_list, element_index)
                # x, y = elem.center[0], elem.topleft[1] + (elem.bottomright[1] - elem.topleft[1]) / 10
                x, y = elem.center[0], elem.center[1]
                self.click_by_coordiate(x, y)
            case "CLICK_BY_COORDINATE":
                """
                ['CLICK_BY_COORDINATE', 500, 500]
                """
                x = int(param[1] / 1000 * self.width)
                y = int(param[2] / 1000 * self.height)
                self.click_by_coordiate(x, y)
            case "DOUBLE_CLICK":
                """
                ['DOUBLE_CLICK', 2]
                """
                element_index = param[1]
                # elem = element_list[element_index - 1]
                elem = find_element_by_index(element_list, element_index)
                x, y = elem.center[0], elem.center[1]
                self.click_by_coordiate(x, y)
                time.sleep(0.5)
                self.click_by_coordiate(x, y)
            case "LONG_PRESS":
                """
                ['LONG_PRESS', 2]
                """
                element_index = param[1]
                # elem = element_list[element_index - 1]
                elem = find_element_by_index(element_list, element_index)
                x, y = elem.center[0], elem.center[1]
                self.long_press_by_coordinate(x, y)
            case "SWIPE":
                """
                ['SWIPE', 'up', 'long']
                """
                x, y = self.width / 2, self.height / 2
                direction = param[1]
                distance = param[2]
                self.swipe(x, y, direction, distance)
            case "SCROLL":
                """
                ['SCROLL', 2, 'left', 'medium']
                """
                element_index = param[1]
                # elem = element_list[element_index - 1]
                elem = find_element_by_index(element_list, element_index)
                x, y = elem.center[0], elem.center[1]
                direction = param[2]
                distance = param[3]
                self.swipe(x, y, direction, distance)

            # todo: drag
            case "TYPE":
                """
                ['TYPE', 'Hello, world']
                """
                text = param[1]
                self.type_text(text)
            case "BACK":
                """
                ['BACK']
                """
                self.back()
            case "BOX_INPUT":
                """
                ['BOX_INPUT', 2, 'settings']
                """
                element_index = param[1]
                # elem = element_list[element_index - 1]
                elem = find_element_by_index(element_list, element_index)
                x, y = elem.center[0], elem.center[1]
                del_length = len(elem.attributes.get("text",""))
                text = param[2]
                self.box_input(x, y, text,del_length)
            case "BUY_TRAIN_TICKET":
                """
                ['BUY_TRAIN_TICKET', 'Beijing', 'Shanghai']
                """
                departure = param[1]
                destination = param[2]
                print_with_color(f"Buying train ticket from {departure} to {destination}", "yellow")
                if departure == "HERE":
                    # 进入选择出发地页面
                    x, y = self.locate_element(element_list, resource_id="com.MobileTicket:id/home_page_train_dep1")
                    self.click_by_coordiate(x, y)
                    # 更新vh
                    xml_path = self.get_xml('0', self.config["PATHS"]["exp_workspace"])
                    element_list = vh_proc.extract_elements(xml_path)
                    # 点击定位按钮
                    x, y = self.locate_element(element_list, text="我的位置")
                    self.click_by_coordiate(x, y + 100)
                    # 更新vh
                    xml_path = self.get_xml('0', self.config["PATHS"]["exp_workspace"])
                    element_list = vh_proc.extract_elements(xml_path)
                else:
                    while True:
                        x, y = self.locate_element(element_list, resource_id="com.MobileTicket:id/home_page_train_dep1", text=departure)
                        if x >= 0 and y >= 0:
                            break
                        x, y = self.locate_element(element_list, resource_id="com.MobileTicket:id/home_page_train_dep1")
                        self.click_by_coordiate(x, y)
                        # 更新vh
                        xml_path = self.get_xml('0', self.config["PATHS"]["exp_workspace"])
                        element_list = vh_proc.extract_elements(xml_path)
                        # 点击搜索框
                        x, y = self.locate_element(element_list, class_name="android.widget.EditText")
                        self.click_type(x, y, departure)
                        time.sleep(0.5)
                        # 选择第一个
                        self.click_by_coordiate(x, y + 100)
                        # 更新vh
                        xml_path = self.get_xml('0', self.config["PATHS"]["exp_workspace"])
                        element_list = vh_proc.extract_elements(xml_path)

                if destination == "HERE":
                    # 进入选择目的地页面
                    x, y = self.locate_element(element_list, resource_id="com.MobileTicket:id/home_page_train_arr1")
                    self.click_by_coordiate(x, y)
                    # 更新vh
                    xml_path = self.get_xml('0', self.config["PATHS"]["exp_workspace"])
                    element_list = vh_proc.extract_elements(xml_path)
                    # 点击定位按钮
                    x, y = self.locate_element(element_list, text="我的位置")
                    self.click_by_coordiate(x, y + 100)
                    # 更新vh
                    xml_path = self.get_xml('0', self.config["PATHS"]["exp_workspace"])
                    element_list = vh_proc.extract_elements(xml_path)
                else:
                    while True:
                        x, y = self.locate_element(element_list, resource_id="com.MobileTicket:id/home_page_train_arr1", text=destination)
                        if x >= 0 and y >= 0:
                            break
                        x, y = self.locate_element(element_list, resource_id="com.MobileTicket:id/home_page_train_arr1")
                        self.click_by_coordiate(x, y)
                        # 更新vh
                        xml_path = self.get_xml('0', self.config["PATHS"]["exp_workspace"])
                        element_list = vh_proc.extract_elements(xml_path)
                        # 点击搜索框
                        x, y = self.locate_element(element_list, class_name="android.widget.EditText")
                        self.click_type(x, y, destination)
                        time.sleep(0.5)
                        # 选择第一个
                        self.click_by_coordiate(x, y + 100)
                        # 更新vh
                        xml_path = self.get_xml('0', self.config["PATHS"]["exp_workspace"])
                        element_list = vh_proc.extract_elements(xml_path)

                x, y = self.locate_element(element_list, text="查询车票")
                self.click_by_coordiate(x, y)
            case "FINISH":
                print_with_color("Task finished", "green")
            case _:
                print_with_color(f"ERROR: Invalid action: {action}", "red")
                return False, None
