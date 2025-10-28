# app/main.py

from app import create_app
import uvicorn

app = create_app()

@app.get("/")
def root():
    return {"status": "ok"}
    
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
