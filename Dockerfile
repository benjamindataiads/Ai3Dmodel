# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Install dependencies
COPY frontend/package*.json ./
RUN npm ci

# Build frontend
COPY frontend/ ./
RUN npm run build

# Stage 2: Backend development (for docker-compose)
FROM mambaorg/micromamba:1.5-jammy AS backend-dev

USER root
WORKDIR /app

# Install system dependencies for OpenGL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglu1-mesa \
    libxrender1 \
    libsm6 \
    libxext6 \
    libx11-6 \
    && rm -rf /var/lib/apt/lists/*

# Install CadQuery via conda (handles OpenCascade dependencies)
RUN micromamba install -y -n base -c conda-forge \
    python=3.11 \
    cadquery=2.4 \
    && micromamba clean --all --yes

# Set environment for micromamba
ENV PATH="/opt/conda/bin:$PATH"
ENV MAMBA_ROOT_PREFIX="/opt/conda"

# Fix ezdxf compatibility issue
RUN /opt/conda/bin/pip install --no-cache-dir "ezdxf>=1.0,<1.2"

# Install pip packages
COPY backend/requirements-pip.txt ./
RUN /opt/conda/bin/pip install --no-cache-dir -r requirements-pip.txt

COPY backend/ ./

EXPOSE 8000

CMD ["/opt/conda/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Stage 3: Production
FROM mambaorg/micromamba:1.5-jammy AS production

USER root
WORKDIR /app

# Install system dependencies for OpenGL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglu1-mesa \
    libxrender1 \
    libsm6 \
    libxext6 \
    libx11-6 \
    && rm -rf /var/lib/apt/lists/*

# Install CadQuery via conda
RUN micromamba install -y -n base -c conda-forge \
    python=3.11 \
    cadquery=2.4 \
    && micromamba clean --all --yes

ENV PATH="/opt/conda/bin:$PATH"
ENV MAMBA_ROOT_PREFIX="/opt/conda"

# Fix ezdxf compatibility issue
RUN /opt/conda/bin/pip install --no-cache-dir "ezdxf>=1.0,<1.2"

# Install pip packages
COPY backend/requirements-pip.txt ./
RUN /opt/conda/bin/pip install --no-cache-dir -r requirements-pip.txt

# Copy backend code
COPY backend/ ./

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist ./static

# Create temp directory
RUN mkdir -p /tmp/cad3d

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run with production settings
CMD ["/opt/conda/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
