from abc import abstractmethod


class BaseController:
    def __init__(self):
        pass

    @abstractmethod
    def get_application_list(self):
        pass

    @abstractmethod
    def get_screenshot(self, prefix, save_dir):
        pass

    @abstractmethod
    def get_vhtree(self):
        pass

    @abstractmethod
    def execute_action(self):
        pass
