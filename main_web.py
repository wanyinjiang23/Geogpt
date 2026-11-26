"""Local web entry; the original GISAgent remains the execution backend."""
from app.web.api import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_web:app", host="127.0.0.1", port=8000)
