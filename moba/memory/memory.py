import os

from moba.memory.user_memory import UserMemory
from moba.memory.app_memory import AppMemory
from moba.memory.task_memory import TaskMemory
from moba.utils.utils import save_json, load_json_if_exist
from moba.utils.utils import cosine_similarity


class Memory:
    def __init__(self, config):
        self.embeddings = {}

        base_path = config["STORAGE_PATH"]
        if not base_path:
            base_path = os.path.dirname(__file__)
            base_path = os.path.join(base_path, "..")
            base_path = os.path.join(base_path, "..")

        self.storage_path = os.path.join(base_path, "storage")

        self.user_path = os.path.join(self.storage_path, "user")
        self.app_path = os.path.join(self.storage_path, "app")
        self.task_path = os.path.join(self.storage_path, "task")
        self.emb_path = os.path.join(self.storage_path, "embedding.json")

        self.user_memory = UserMemory(self.user_path)
        self.app_memory = AppMemory(self.app_path)
        self.task_memory = TaskMemory(self.task_path)

        self.load_all()

    def retrieve_history(self, history, v, emb_model=None):
        sims = [(key, cosine_similarity(self.get_embedding(v, emb_model=emb_model), self.get_embedding(key, emb_model=emb_model))) for key, _ in history.items()]
        sims = sorted(sims, key=lambda x: x[1], reverse=True)[0]
        return sims[0]

    def get_embedding(self, key, emb_model=None):
        if key not in self.embeddings and emb_model:
            embed = emb_model.generate_embedding(key)
            print("Get embedding: " + key)
            self.embeddings[key] = embed
            return embed
        else:
            return self.embeddings[key]

    def save_embeddings(self):
        save_json(self.emb_path, self.embeddings)

    def save_all(self):
        os.makedirs(self.storage_path, exist_ok=True)
        self.user_memory.save_all()
        self.app_memory.save_all()
        self.task_memory.save_all()

        save_json(self.emb_path, self.embeddings)

    def load_all(self):
        os.makedirs(self.storage_path, exist_ok=True)
        self.user_memory.load_all()
        self.app_memory.load_all()
        self.task_memory.load_all()

        self.embeddings = load_json_if_exist(self.emb_path, default={})

    def is_empty(self):
        return len(self._nodes) == 0
