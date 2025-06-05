from fastapi import FastAPI
from app.api.routes import auth, users, documents
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(documents.router)

@app.get("/")
def read_root():
    return {"msg": "AURA GDPR Backend is running"}
