# simple fastapi app to rebuild the docker-composer and restart it

from fastapi import Body, FastAPI
from uvicorn import run
import subprocess

app = FastAPI()

@app.post("/")
def read_root(body = Body(...)):
    subprocess.run(["docker-compose", "up", "--force-recreate", "--build", "--remove-orphans"])
    return {"message": "restarted"}

if __name__ == "__main__":
    run(app, host="127.0.0.1", port=8123)
