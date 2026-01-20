from fastapi import FastAPI

app = FastAPI(title="FastAPI Backend")

@app.get("/")
def root():
    return {"message": "API running"}
