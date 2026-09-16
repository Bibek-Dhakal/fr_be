from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def hello_server():
    return {"message": "Hello, server!"}
