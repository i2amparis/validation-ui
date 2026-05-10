FROM debian:bookworm-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY . .

#ARG GITHUB_TOKEN
#RUN git config --global url."https://${GITHUB_TOKEN}@github.com/".insteadOf "https://github.com/"

RUN uv sync

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["uv", "run", "streamlit", "run", "ui/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
