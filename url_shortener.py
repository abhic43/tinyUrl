from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel, HttpUrl
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
import hashlib
import string
import random
import os
from urllib.parse import urlparse
from typing import Optional

# Initialize FastAPI app
app = FastAPI(title="URL Shortener Service")

# Environment variables for configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:@localhost:5432/url_shortener")
SHORT_CODE_LENGTH = int(os.getenv("SHORT_CODE_LENGTH", "7"))  # Ensure default is a string "7"
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# SQLAlchemy setup
engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=10)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database model
class URL(Base):
    __tablename__ = "urls"
    id = Column(Integer, primary_key=True, index=True)
    original_url = Column(String, nullable=False)
    short_code = Column(String, unique=True, index=True, nullable=False)

# Initialize database
def init_db():
    Base.metadata.create_all(bind=engine)

# Dependency for database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic model for input validation
class URLRequest(BaseModel):
    url: HttpUrl

# Generate short code
def generate_short_code(url: str) -> str:
    hash_object = hashlib.md5(url.encode())
    return hash_object.hexdigest()[:SHORT_CODE_LENGTH]

# Generate random short code as fallback
def generate_random_code() -> str:
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(SHORT_CODE_LENGTH))

# Create short URL
@app.post("/shorten", status_code=status.HTTP_201_CREATED)
async def shorten_url(url_request: URLRequest, db: Session = Depends(get_db)):
    original_url = str(url_request.url)
    short_code = generate_short_code(original_url)
    
    for _ in range(3):  # Retry up to 3 times for unique short code
        db_url = URL(original_url=original_url, short_code=short_code)
        try:
            db.add(db_url)
            db.commit()
            db.refresh(db_url)
            return {"short_url": f"{BASE_URL}/{short_code}", "original_url": original_url}
        except IntegrityError:
            db.rollback()
            short_code = generate_random_code()
    
    raise HTTPException(status_code=500, detail="Failed to generate unique short code")

# Redirect to original URL
@app.get("/{short_code}", response_class=RedirectResponse)
async def redirect_url(short_code: str, db: Session = Depends(get_db)):
    db_url = db.query(URL).filter(URL.short_code == short_code).first()
    if not db_url:
        raise HTTPException(status_code=404, detail="Short URL not found")
    return RedirectResponse(db_url.original_url)

# Optional HTML frontend
@app.get("/", response_class=HTMLResponse)
async def get_frontend():
    return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>URL Shortener</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                .message { color: green; }
                .error { color: red; }
                input[type=text] { width: 100%; padding: 8px; margin: 10px 0; }
                input[type=submit] { padding: 8px 16px; }
            </style>
            <script>
                async function shortenUrl() {
                    const urlInput = document.getElementById('url').value;
                    const resultDiv = document.getElementById('result');
                    const errorDiv = document.getElementById('error');
                    resultDiv.innerHTML = '';
                    errorDiv.innerHTML = '';
                    
                    try {
                        const response = await fetch('/shorten', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({url: urlInput})
                        });
                        const data = await response.json();
                        if (response.ok) {
                            resultDiv.innerHTML = `Shortened URL: <a href="${data.short_url}">${data.short_url}</a>`;
                        } else {
                            errorDiv.innerHTML = data.detail;
                        }
                    } catch (err) {
                        errorDiv.innerHTML = 'Failed to shorten URL';
                    }
                }
            </script>
        </head>
        <body>
            <h1>URL Shortener</h1>
            <div id="error" class="error"></div>
            <form onsubmit="event.preventDefault(); shortenUrl();">
                <input type="text" id="url" placeholder="Enter URL to shorten">
                <input type="submit" value="Shorten">
            </form>
            <div id="result"></div>
        </body>
        </html>
    """

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)