import os

from moba.utils.utils import save_json, load_json_if_exist


class UserMemory:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.file_path = os.path.join(base_dir, "user_memory.json")
        self.user_query = UserQuery()

    def add_query(self, query):
        self.user_query.add_query(query)

    def save_all(self):
        os.makedirs(self.base_dir, exist_ok=True)
        self.user_query.save_to_file(self.file_path)

    def load_all(self):
        os.makedirs(self.base_dir, exist_ok=True)
        self.user_query = UserQuery.load_from_file(self.file_path)


class UserQuery:
    def __init__(self, query_list=[]):
        self.query_list = query_list

    def add_query(self, query):
        self.query_list.append(query)

    def save_to_file(self, file_path):
        save_json(file_path, self.query_list)

    @staticmethod
    def load_from_file(file_path):
        data = load_json_if_exist(file_path, default=[])
        return UserQuery(data)
