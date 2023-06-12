# simple fastapi app to rebuild the docker-composer and restart it

from fastapi import Body, FastAPI, BackgroundTasks
from uvicorn import run
import subprocess

app = FastAPI()


def rebuild_image():
    subprocess.run(["docker-compose", "build", "--no-cache"])
    subprocess.run(["docker-compose", "down"])
    subprocess.run(["docker-compose", "up", "-d"])

@app.post("/")
def read_root(background_tasks: BackgroundTasks, body = Body(...)):
    background_tasks.add_task(rebuild_image)
    return {"message": "restarted"}

if __name__ == "__main__":
    run(app, host="127.0.0.1", port=8123)
