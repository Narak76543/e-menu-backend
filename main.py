
from api.admin_user.views import init_admin_auth
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()
init_admin_auth(app)

if not os.path.exists("static/images"):
    os.makedirs("static/images")

# Mount the static folder
app.mount("/static", StaticFiles(directory="static"), name="static")


from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.register import *