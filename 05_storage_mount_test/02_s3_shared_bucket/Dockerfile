FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
WORKDIR /app

ENV UV_SYSTEM_PYTHON=1 UV_COMPILE_BYTECODE=1

COPY requirements.txt requirements.txt
RUN uv pip install -r requirements.txt

ENV AWS_REGION=us-east-1
ENV AWS_DEFAULT_REGION=us-east-1
ENV DOCKER_CONTAINER=1

EXPOSE 8080

COPY . .

# CMD is set at deploy time by the agentcore CLI based on the -e entrypoint.
# Both writer_agent.py and reader_agent.py share this image — the CLI picks
# which one to run via the container command.
