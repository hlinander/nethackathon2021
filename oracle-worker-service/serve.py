import fastapi
import subprocess
import threading
import time
from starlette.responses import Response
from starlette.status import HTTP_200_OK, HTTP_500_INTERNAL_SERVER_ERROR
import requests
import json
import os

app = fastapi.FastAPI()
concurrent = 0
lock = threading.Lock()
last_ping = time.time()

PORT = os.getenv("PORT", 8000)


def increase_concurrent():
    global concurrent
    with lock:
        concurrent += 1

def decrease_concurrent():
    global concurrent
    with lock:
        concurrent -= 1

def generate_tokens(prompt):
    print("Number of concurrent requests:", concurrent)
    print(f"Prompt: {prompt}")
    if concurrent >= 1:
        print("Already processing!")
        return Response("Already handling request...", status_code=HTTP_500_INTERNAL_SERVER_ERROR)
        # time.sleep(1.0)
        # print("Waiting for resources...")

    increase_concurrent()
    print("Starting ggml...")
    p = subprocess.Popen(["build/bin/main", "-m", "./convert/ckpt/ggml-model-q4_0.bin", "-t", "6", "-p", prompt],
        stdout=subprocess.PIPE
    )
    response = ""
    while True:
        out = p.stdout.read(2)
        if out == b'' and p.poll() is not None:
            break
        try:
            s = out.decode("utf-8")
        except:
            break
        response += s
        if len(response.split("\n\n")) > 1:
            break
        try:
            yield s
        except:
            print("Exception in yield!")
            break

    print("End of sequence.")

    p.terminate()
    p.wait(timeout=3)
    if p.poll() is None:
        print("Process not terminated, trying to kill.")
        p.kill()
    else:
        print("Process terminated successfully.")

    decrease_concurrent()

@app.get("/chat")
def chat(data=fastapi.Body(...)):
    if not "prompt" in data:
        return Response("No prompt in data", status_code=HTTP_500_INTERNAL_SERVER_ERROR)

    generator = generate_tokens(data["prompt"])
    response = fastapi.responses.StreamingResponse(generator, media_type="text/plain")
    return response

@app.get("/ping")
def ping():
    global last_ping
    last_ping = time.time()
    return Response(status_code=HTTP_200_OK)


def register_worker():
    worker_data = dict(
        endpoint=f"http://localhost:{PORT}"
    )
    while True:
        print(f"Trying to register worker at {worker_data}")
        try:
            response = requests.get("http://localhost:8383/register_worker", data=json.dumps(worker_data))
            if response.ok:
                print(response)
                break
        except Exception as e:
            print(e)
        
        time.sleep(5)

def check_registration():
    while True:
        if time.time() - last_ping > 10:
            register_worker()
        time.sleep(10)
        
check_registration_thread = threading.Thread(target=check_registration)
check_registration_thread.start()
#register_worker()