import os  # used for creating directory
import pdb
import re
import subprocess
import time

import sys

from moba.process import vh_proc

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


def get_adb_devices():
    """
    List all connected Android devices
    :return: list of devices
    """
    device_list = []
    command = "adb devices"
    execution_success, result = command_executor(command)
    if execution_success:
        device_list = [d.split() for d in result.split("\n")[1:]]
    return device_list


def select_adb_devices(device_list):
    """
    Select an Android device from the list
    :param device_list: list of devices
    :return: selected device name
    """
    if not device_list:
        print_with_color("ERROR: No device found!", "red")
        sys.exit()
    print_with_color(f"List of devices attached:", "yellow")
    for i, device in enumerate(device_list):
        print_with_color(f"({i + 1})\t{device[0]}\t{device[1]}", "yellow")
    if len(device_list) == 1:
        device_index = 1
        device = device_list[0]
    else:
        while True:
            print_with_color("Please choose the Android device by entering its index:", "blue")
            device_index = input()
            if isinstance(device_index, int) and 0 < device_index <= len(device_list):
                device = device_list[device_index - 1]
                break
    print_with_color(f"Device selected: ({device_index}) {device[0]} {device[1]}", "green")
    return device[0]


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


class AndroidController(BaseController):
    def __init__(self, config, device):
        self.config = config
        self.device = device
        self.width = self.get_screen_size()[0]
        self.height = self.get_screen_size()[1]
        self.unicode_input = False
        self.default_ime = ""
        self.adb_max_retry = config["COMMAND_MAX_TRY"]
        self.package_list = self.get_application_list()

    def get_application_list(self, system=True, third_party=True):
        """
        Get the list of installed applications on the Android device
        :return: list of applications
        """
        if system and third_party:
            command = f"adb -s {self.device} shell pm list packages --user 0"
        elif system:
            command = f"adb -s {self.device} shell pm list packages --user 0 -s"
        elif third_party:
            command = f"adb -s {self.device} shell pm list packages --user 0 -3"
        success, result = command_executor(command, self.adb_max_retry)
        if success:
            # print(result)
            return result.split("\n")
        else:
            return []

    def install_application(self, apk_path):
        """
        Install an application on the Android device
        :param apk_path: path to the apk file
        :return: execution success
        """
        command1 = f"..\\..\\tools\\aapt-windows\\aapt.exe dump badging {apk_path} | findstr package"
        success, result = command_executor(command1)
        if success:
            package_name = result.split("'")[1]
        else:
            package_name = "Unknown"
        print_with_color(f"Installing application {package_name} from {apk_path}", "yellow")
        command2 = f"adb -s {self.device} install {apk_path}"
        success, result = command_executor(command2)
        if success:
            print_with_color(f"Application {package_name} installed", "green")
            return package_name
        else:
            return None

    def uninstall_application(self, package_name):
        """
        Uninstall an application on the Android device
        :param package_name: package name of the application
        :return: execution success
        """
        print_with_color(f"You are going to uninstall the application: {package_name}", "red")
        print_with_color("Are you sure you want to uninstall the application? (Y/N)", "yellow")
        if not user_check():
            print_with_color("Uninstallation canceled", "yellow")
            return False
        command = f"adb -s {self.device} uninstall {package_name}"
        success, result = command_executor(command)
        return success

    def open_application(self, package_name, activity_name=None):
        """
        Open an application on the Android device
        :param package_name: package name of the application
        :param activity_name: activity name of the application
        :return: execution success
        """
        if activity_name:
            command = f"adb -s {self.device} shell am start -n {package_name}/{activity_name}"
        else:
            command = f"adb -s {self.device} shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1"
        success, result = command_executor(command)
        return success

    def close_application(self, package_name):
        """
        Close an application on the Android device
        :param package_name: package name of the application
        :return: execution success
        """
        if not package_name:
            package_name, _ = self.get_activity()
        command = f"adb -s {self.device} shell am force-stop {package_name}"
        success, result = command_executor(command)
        return success

    def enable_unicode_input(self):
        """
        Enable ADBKeyboard for typing non-ASCII characters
        :return: execution success
        """

        # get the default input method
        command0 = f"adb -s {self.device} shell settings get secure default_input_method"
        success, result = command_executor(command0)
        self.default_ime = result.strip()
        if self.default_ime == "com.android.adbkeyboard/.AdbIME":
            return True

        # check if we have ADBKeyboard.apk
        command1 = f"adb -s {self.device} shell ime list -s"
        success, result = command_executor(command1)

        if "com.android.adbkeyboard/.AdbIME" in result:
            print_with_color("ADBKeyboard is already installed", "green")
        else:
            # download ADBKeyboard.apk from https://raw.github.com/senzhk/ADBKeyBoard/master/ADBKeyboard.apk
            package_path = "../../tools/ADBKeyboard.apk"
            if not os.path.exists(package_path):
                print("Downloading ADBKeyboard.apk...")
                command2 = f"wget https://raw.github.com/senzhk/ADBKeyBoard/master/ADBKeyboard.apk -O {package_path}"
                success, result = command_executor(command2)
                if not success:
                    print("Download failed.")
                    return False
            self.install_application(package_path)

        # enable ADBKeyboard
        command3 = f"adb -s {self.device} shell ime enable com.android.adbkeyboard/.AdbIME"
        command4 = f"adb -s {self.device} shell ime set com.android.adbkeyboard/.AdbIME"
        success, _ = command_executor(command3)
        if success:
            success, _ = command_executor(command4)
        if success:
            print_with_color("ADBKeyboard enabled", "green")
            return True

    def disable_unicode_input(self):
        """
        Disable ADBKeyboard and switch back to the default input method
        """
        if self.default_ime == "com.android.adbkeyboard/.AdbIME":
            return
        # disable ADBKeyboard
        command1 = f"adb -s {self.device} shell ime disable com.android.adbkeyboard/.AdbIME"
        command2 = f"adb -s {self.device} shell ime set {self.default_ime}"
        success, _ = command_executor(command1)
        if success:
            success, _ = command_executor(command2)
        self.unicode_input = False

    def get_screen_size(self):
        """
        Get the screen size of the Android device
        :return: width, height
        """
        command = f"adb -s {self.device} shell wm size"
        success, result = command_executor(command)
        if success:
            size_str = result.strip().split(": ")[1]
            # Check if the string contains "Override size"
            if "Override size" in size_str:
                size_str = size_str.replace("Override size", "").strip()
            width, height = size_str.split("x")
            return int(width), int(height)
        else:
            print_with_color("Error getting screen size", "red")
            return None, None

    def get_screenshot(self, prefix, save_dir):
        """
        Get a screenshot of the Android device and save it on the computer
        :param prefix: prefix for the screenshot file name
        :param save_dir: directory to save the screenshot
        :return: path to the screenshot
        """
        # Check if the save_dir exists, if not, create it
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        command = f"adb -s {self.device} exec-out screencap -p > {save_dir}/{prefix}.png"
        success, result = command_executor(command)
        if not success:
            exit()
        return os.path.normpath(f"{save_dir}/{prefix}.png")

    def get_xml(self, prefix, save_dir):
        """
        Get the XML file of the current screen on the Android device
        :param prefix: prefix for the XML file name
        :param save_dir: directory to save the XML file
        :return: path to the XML file
        """
        # Check if the save_dir exists, if not, create it
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        command = f"adb -s {self.device} shell uiautomator dump --compressed /sdcard/{prefix}.xml"
        command2 = f"adb -s {self.device} pull /sdcard/{prefix}.xml {save_dir}"
        command3 = f"adb -s {self.device} shell rm -f /sdcard/{prefix}.xml"
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
        Get the current activity name
        :return: activity name
        """
        command = f"adb -s {self.device} shell dumpsys activity activities | findstr mCurrentFocus"
        success, result = command_executor(command)
        try:
            info = re.findall(r"mCurrentFocus=Window\{[0-9a-f]+ u0 (.*?)}", result)
            package_name, activity_name = info[0].split("/")
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
        command = f"adb -s {self.device} shell input tap {x} {y}"
        success, result = command_executor(command)

    def long_press_by_coordinate(self, x, y, duration=1000):
        """
        Long press on the screen by coordinate
        :param x: x coordinate
        :param y: y coordinate
        :param duration: duration of long press
        :return: execution success
        """
        command = f"adb -s {self.device} shell input touchscreen swipe {x} {y} {x} {y} {duration}"
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

        if direction.upper() == "UP":
            command = f"adb -s {self.device} shell input touchscreen swipe {x} {y} {x} {y - distance} {duration}"
        elif direction.upper() == "DOWN":
            command = f"adb -s {self.device} shell input touchscreen swipe {x} {y} {x} {y + distance} {duration}"
        elif direction.upper() == "LEFT":
            command = f"adb -s {self.device} shell input touchscreen swipe {x} {y} {x - distance} {y} {duration}"
        elif direction.upper() == "RIGHT":
            command = f"adb -s {self.device} shell input touchscreen swipe {x} {y} {x + distance} {y} {duration}"
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
        command = f"adb -s {self.device} shell input touchscreen swipe {start_x} {start_y} {end_x} {end_y} {duration}"
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
        command = f"adb -s {self.device} shell input swipe {start_x} {start_y} {end_x} {end_y} {duration}"
        success, result = command_executor(command)

    def type_text(self, text):
        """
        Type text
        :param text: text to be typed
        :return: execution success
        """
        # Convert the text to unicode escape sequence
        if text.isascii():
            # ASCII characters
            command = f"adb -s {self.device} shell input text '{text}'"
            success, result = command_executor(command)
        else:
            if not self.unicode_input:
                self.unicode_input = self.enable_unicode_input()
                time.sleep(1)
            # Non-ASCII characters
            command = f"adb -s {self.device} shell am broadcast -a ADB_INPUT_TEXT --es msg '{text}'"
            success, result = command_executor(command)
            if not success or not self.unicode_input:
                print_with_color("Please switch to ADBKeyBoard to type non-ascii characters.\n"
                                 "You can download ADBKeyBoard from this repository:\n\n"
                                 "https://github.com/senzhk/ADBKeyBoard?tab=readme-ov-file#build-and-install-apk\n\n"
                                 "And follow scripts below:\n", front_color="yellow")
                print_with_color("adb install ADBKeyboard.apk\n"
                                 "adb shell ime enable com.android.adbkeyboard/.AdbIME\n"
                                 "adb shell ime set com.android.adbkeyboard/.AdbIME\n", front_color="cyan")
            # self.disable_unicode_input()

    def clear_text(self,del_length=100):
        command_1 = f"adb -s {self.device} shell input keyevent KEYCODE_MOVE_END"
        success, result = command_executor(command_1)

        for _ in range(del_length):
            command_2 = f"adb -s {self.device} shell input keyevent KEYCODE_DEL"
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
