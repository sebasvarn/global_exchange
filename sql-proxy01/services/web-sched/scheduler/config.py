import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    WORKER_SERVER = f"{os.getenv('WORKER_SERVER','web')}"
    WORKER_PORT = f"{os.getenv('WORKER_PORT','5000')}"
    WORKER_TASK = f"{os.getenv('WORKER_TASK','/task')}"
    TASK_INTERVAL_SECONDS = f"{os.getenv('TASK_INTERVAL_SECONDS','20')}"
    APP_FOLDER = f"{os.getenv('APP_FOLDER','/app/')}"