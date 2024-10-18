import os
import cv2
import numpy as np

from moba.utils.utils import save_json, load_json_if_exist
from moba.process import vh_proc


class AppMemory:
    def __init__(self, base_dir):
        self.apps = {}
        self.base_dir = base_dir

    def add_app(self, app_name):
        if app_name not in self.apps:
            self.apps[app_name] = AppData(app_name)

    def get_app(self, app_name):
        return self.apps.get(app_name)

    def add_page(self, app_name, obs):
        cur_app: AppData = self.get_app(app_name)
        page_name = str(len(cur_app.pages))
        cur_app.add_page(page_name, obs)
        return page_name

    def save_all(self):
        os.makedirs(self.base_dir, exist_ok=True)

        app: AppData
        for app in self.apps.values():
            app.save_to_dir(self.base_dir)

    def load_all(self):
        os.makedirs(self.base_dir, exist_ok=True)

        for app_name in os.listdir(self.base_dir):
            app_dir = os.path.join(self.base_dir, app_name)
            if os.path.isdir(app_dir):
                app_data = AppData.load_from_dir(app_dir)
                self.apps[app_name] = app_data


class AppData:
    def __init__(self, app_name):
        self.app_name = app_name
        self.pages = {}

    def add_page(self, page_name, page_desc=None, page_action=None):
        self.pages[page_name] = PageData(page_name, page_desc, page_action)

    def save_to_dir(self, base_dir):
        app_dir = os.path.join(base_dir, self.app_name)
        os.makedirs(app_dir, exist_ok=True)

        page: PageData
        for page in self.pages.values():
            # page_path = os.path.join(app_dir, page.page_name + ".json")
            page.save_to_file(app_dir, xml_path=None, img_path=None)

    @staticmethod
    def load_from_dir(app_dir):
        app_name = os.path.basename(app_dir)
        app_data = AppData(app_name)
        for file_name in os.listdir(app_dir):
            if file_name.endswith('.json'):
                page_data = PageData.load_from_file(app_dir, file_name.split(".")[0])
                app_data.pages[page_data.page_name] = page_data
        return app_data


class PageData:
    def __init__(self, page_name, page_desc=None, activity=None, package=None, xml=None, img=None):
        self.page_name = page_name
        self.page_desc = page_desc
        self.activity = activity
        self.package = package
        self.xml = xml
        self.img = img

    def save_to_file(self, dir_path, xml_path=None, img_path=None):
        os.makedirs(dir_path, exist_ok=True)
        dir_name = os.path.dirname(dir_path)
        file_path = os.path.join(dir_path, self.page_name + ".json")
        data = {
            "page_name": self.page_name,
            "page_desc": self.page_desc,
            "activity": self.activity,
            "package": self.package,
        }
        save_json(file_path, data)

        import shutil
        if xml_path:
            tar_xml_path = os.path.join(dir_name, dir_name + ".xml")
            shutil.copyfile(xml_path, tar_xml_path)
        if img_path:
            tar_img_path = os.path.join(dir_name, dir_name + ".png")
            shutil.copyfile(img_path, tar_img_path)

    @staticmethod
    def load_from_file(dir_path, page_name):
        os.makedirs(dir_path, exist_ok=True)

        dir_name = os.path.dirname(dir_path)
        image_path = os.path.join(dir_path, page_name + ".png")
        file_path = os.path.join(dir_path, page_name + ".json")
        xml_path = os.path.join(dir_path, page_name + ".xml")

        data = load_json_if_exist(file_path)
        page_name = data.get("page_name", "")
        page_desc = data.get("page_desc", "")
        activity = data.get("activity", "")
        package = data.get("package", "")

        img = None
        xml = None
        if os.path.exists(image_path):
            img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if os.path.exists(xml_path):
            xml = vh_proc.extract_elements(xml_path)

        return PageData(page_name, page_desc, activity, package, xml, img)
