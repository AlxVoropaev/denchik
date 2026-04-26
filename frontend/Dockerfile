FROM node:20-bookworm-slim AS base
WORKDIR /app

# System deps for Playwright (only used in `make e2e`)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173
# NB: stays as root in dev for the same reason as backend/Dockerfile —
# docker-compose bind-mounts ./frontend:/app, and a fixed-UID `node` user
# inside the container cannot read host-owned files when the host directory
# is mode 0700 (which it is on this developer's box). A production build
# should switch to USER node and use a copy-only image, not a bind mount.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
