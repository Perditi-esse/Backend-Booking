# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.10-slim

WORKDIR /code
COPY . /code
RUN python -m pip install -r requirements.txt



CMD [ "uvicorn", "main:app", "--host", "0.0.0.0","--port","80" ]


