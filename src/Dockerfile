FROM python:3.12-slim

# Set environment variables
ENV DISPLAY=:99
ENV PYTHONPATH=/app
ENV PORT=8000

# Install system dependencies (no libgconf-2-4; add common Chrome runtime libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    wget \
    gnupg \
    unzip \
    xvfb \
    build-essential \
    libxi6 \
    # Chrome/Chromium runtime deps (Debian 12/13)
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    libxrender1 \
    xdg-utils \
 && rm -rf /var/lib/apt/lists/*

# Install Google Chrome using keyrings (no apt-key)
RUN mkdir -p /etc/apt/keyrings \
 && wget -qO- https://dl.google.com/linux/linux_signing_key.pub \
    | gpg --dearmor -o /etc/apt/keyrings/google-chrome.gpg \
 && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] https://dl.google.com/linux/chrome/deb/ stable main" \
    > /etc/apt/sources.list.d/google-chrome.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends google-chrome-stable \
 && rm -rf /var/lib/apt/lists/*

# Create app directory and set permissions
WORKDIR /app
RUN mkdir -p /app/chromedriver

# Install uv for Python dependency management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
 && mv /root/.local/bin/uv /usr/local/bin/uv

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt \
 && rm -rf /root/.cache

# Create necessary directories
RUN mkdir -p /app/logs /app/output /app/prompts /app/prompts/plans /app/prompts/features /app/prompts/add_ons

# Copy application code and prompts
COPY src/amint /app/src/amint
COPY src/amint/prompts /app/prompts

# Create non-root user
RUN useradd -m appuser && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app/prompts

# Switch to non-root user
USER appuser

# Set ChromeDriver path
ENV PATH="/app/chromedriver:${PATH}"

# Run the application
CMD ["uvicorn", "src.amint.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
