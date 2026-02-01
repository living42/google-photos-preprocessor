FROM debian:trixie

# Prevent interactive prompts during apt
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    exiftool \
    curl \
    unzip \
    python3 \
    python3-pip \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install motionphoto2 binary
ARG MOTION_PHOTO2_VERSION=2.7.7
RUN curl -L -o /tmp/motionphoto2.zip \
    "https://github.com/PetrVys/MotionPhoto2/releases/download/v${MOTION_PHOTO2_VERSION}/MotionPhoto2_Linux_v${MOTION_PHOTO2_VERSION}.zip" \
    && unzip /tmp/motionphoto2.zip -d /tmp \
    && mv /tmp/motionphoto2 /usr/local/bin/motionphoto2 \
    && chmod +x /usr/local/bin/motionphoto2 \
    && rm -rf /tmp/*

# Set up application directory
WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Copy application code
COPY src/ ./src/

# Copy entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Define volume mounts
VOLUME ["/data/source", "/data/output", "/data"]

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]
