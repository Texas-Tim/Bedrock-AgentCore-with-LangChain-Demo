FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
WORKDIR /app

ENV UV_SYSTEM_PYTHON=1 UV_COMPILE_BYTECODE=1

# Install probe-target binaries so binary-absence isn't the reason a probe fails.
# mount-s3 for S3 Mountpoint (FUSE), nfs-common for mount.nfs4, libcap2-bin for capsh.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        wget \
        nfs-common \
        fuse3 \
        libfuse2 \
        libcap2-bin \
    && wget -q https://s3.amazonaws.com/mountpoint-s3-release/latest/arm64/mount-s3.deb \
    && apt-get install -y ./mount-s3.deb \
    && rm mount-s3.deb \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN uv pip install -r requirements.txt

ENV AWS_REGION=us-east-1
ENV AWS_DEFAULT_REGION=us-east-1
ENV DOCKER_CONTAINER=1

EXPOSE 8080

COPY . .

CMD ["python", "agent.py"]
