#!/bin/sh
pip install -r requirements.txt
COORD_EMAIL=${COORD_EMAIL:-maria@ecovida.org} COORD_SENHA=${COORD_SENHA:-maria12345} uvicorn main:app --host 0.0.0.0 --port 8000
