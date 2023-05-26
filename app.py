import json
import random
from typing import Dict, Tuple
from uuid import uuid4
import redis
import time

from flask import Flask, request, jsonify
# from redis import Redis

app = Flask(__name__)

redis_client = redis.Redis(host="localhost", port="6379", db=0)
timestamps = {}


def validate_solver_request(solver: str, parameters: Dict[str, float]) -> bool:
    if solver != "SimulatedAnnealing":
        return False

    beta_max = parameters.get("beta_max")
    beta_min = parameters.get("beta_min")

    return (
        beta_max is not None
        and beta_min is not None
        and beta_max > 0
        and beta_min > 0
        and beta_max > beta_min
    )

@app.route('/')
def home():
    return "Hello, World!"

# 辞書型のキーを文字列に変換するための関数
def convert_dict_key_to_tuple(d: dict) -> dict:
    return {tuple(map(int, k.strip("()").split(","))): v for k, v in d.items()}


#Post Instance API
@app.route("/post_instance", methods=["POST"])
def post_instance():
    data = request.get_json()

    instance_key = str(uuid4())
    instance_data = {
        "type": data["type"],
         "instance_data": json.dumps(data["instance_data"])
    }

    # redis_client.hset(instance_key, instance_data)
    redis_client.hset(instance_key, "type", data["type"])
    redis_client.hset(instance_key, "instance_data", json.dumps(data["instance_data"]))

    return jsonify({"instance_key": instance_key})


#Solver Request API
@app.route("/solver_request", methods=["POST"])
def solver_request():
    data = request.get_json()

    instance_key = data["instance_key"]
    solver = data["solver"]
    parameters = data["parameters"]

    if not validate_solver_request(solver, parameters):
        return jsonify({"message": "Invalid solver or parameters"}), 400

    result_key = str(uuid4())
    print(f"Generated result_key: {result_key}")  # Print key
    
    timestamp = int(time.time()) 
    timestamps[result_key] = timestamp
    redis_client.hset(result_key, "status", "PENDING") #{'status':'PENDING' (5. Result key)}
 

    return jsonify({"result_key": result_key})


#解の問い合わせ（Solver Request API
@app.route("/get_result", methods=["POST"])
def get_result():
    data = request.get_json()
    result_key = data["result_key"]

    redis_result = redis_client.hgetall(result_key) 
    redis_result = {k.decode(): v.decode() for k, v in redis_result.items()}

    if not redis_result:
        return jsonify({"message": "Invalid result_key"}), 404

    timestamp = timestamps.get(result_key)
    if timestamp is None:
        return jsonify({"message": "Invalid result_key"}), 404

    status = redis_result["status"]  # ここでstatusを取得します
    
    # elapsed_time = int(time.time()) - int(redis_result["timestamp"])
    elapsed_time = int(time.time()) - timestamp
    if elapsed_time < 60:
        status = "PENDING"
    elif elapsed_time >= 60:
        status = random.choice(["SUCCESS", "FAILED"])
    
    if status == "SUCCESS":
        result = {
            "status": "SUCCESS",
            "result": {0: 0, 1: 1, 2: 1}  # 指定された結果を返す
        }
    elif status == "FAILED":
        result = {"status": "FAILED", "message": "Error message"}
    else:
        result = {"status": "PENDING"}

    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)
