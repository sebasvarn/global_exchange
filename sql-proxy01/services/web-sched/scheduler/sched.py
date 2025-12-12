from flask import Flask, jsonify
from logging.config import dictConfig
from flask_apscheduler import APScheduler
import logging
import requests
import os
from requests.adapters import HTTPAdapter, Retry

# Create a Flask application instance
schedapp = Flask(__name__)
schedapp.config.from_object("config.Config")
dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s schedapp %(levelname)-8s %(filename)s(%(lineno)d) %(funcName)s(): %(message)s',
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
            'formatter': 'default',
        }
    },
    'root': {
        'level': 'DEBUG',
        'handlers': ['console']
    }
})

_SERVER = schedapp.config.get("WORKER_SERVER")
_PORT = schedapp.config.get("WORKER_PORT")
_TASK = schedapp.config.get("WORKER_TASK")

# Define a simple route
@schedapp.route('/')
def index():
    logging.debug("El task es "+_SERVER+":"+_PORT+_TASK)
    return "El task es "+_SERVER+":"+_PORT+_TASK

@schedapp.route("/job/<operation>/<name>")
def job_manager(operation, name):
    logging.debug("operation: "+operation+" name: "+name)
    if operation not in ["list","stop","start"]:
        job = myscheduler.get_job(name)
        if not job:
            return jsonify({"error": "Job not found"}), 404

    try:
        if operation == "pause":
            logging.debug("pausamos job ...")
            job.pause()
            return "Job pausado"
        elif operation == "resume":
            logging.debug("reiniciamos job ...")
            job.resume()
            return "Job reiniciado"
        elif operation == "list":
            logging.debug("listamos jobs ...")
            jobs = myscheduler.get_jobs()
            lista = [{"id": job.id, "next_run_time": str(job.next_run_time), "trigger": str(job.trigger)} for job in jobs]
            return jsonify(lista)
        elif operation == "stop":
            logging.debug("detenemos todos los jobs ...")
            myscheduler.remove_all_jobs()
            return "Todos los jobs han sido detenidos"
        elif operation == "start":
            logging.debug("iniciamos job ...")
            myscheduler.add_job(id='do_de', func=do_de, trigger='interval', seconds=int(schedapp.config.get("TASK_INTERVAL_SECONDS")), max_instances=1)
            return "Job iniciado"
        else:
            return jsonify({"error": "Invalid operation"}), 400
    except Exception as e:
        logging.error(f"Error managing job: {e}")
        return jsonify({"error": str(e)}), 500

def do_de():
    logging.debug("Iniciamos el do_de")   
    resultado = []
    with myscheduler.app.app_context():
        logging.debug("Iniciamos el request")
        s = requests.Session()
        retries = Retry(total=5,
                backoff_factor=0.1,
                status_forcelist=[ 500, 502, 503, 504 ])
        s.mount('http://', HTTPAdapter(max_retries=retries))
        rsp = s.request("POST", _SERVER+":"+_PORT+_TASK)
        if rsp.status_code != 200:
            logging.debug("Error : SERVER RESPONSE STATUS CODE "+str(rsp.status_code))
            logging.debug(_SERVER+_PORT+_TASK)
            logging.debug(rsp.content.decode('utf-8'))
            error = {"Exception": rsp.content.decode('utf-8')}
            resultado.append(error)
        else:
            logging.debug(rsp.content.decode('utf-8'))
            response = {"Response":rsp.content.decode('utf-8')}
            resultado.append(response)

if not schedapp.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':    
    # Initialize APScheduler
    myscheduler = APScheduler()
    myscheduler.init_app(schedapp)
    myscheduler.start()
    myscheduler.add_job(id='do_de', func=do_de, trigger='interval', seconds=int(schedapp.config.get("TASK_INTERVAL_SECONDS")), max_instances=1)
    
