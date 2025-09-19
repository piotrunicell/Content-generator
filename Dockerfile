# Use official Python slim image as base
FROM python:3.13-slim

# Install dependencies for Chrome and Chromedriver
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    ca-certificates

# Install Google Chrome Stable
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb


# Install Chromedriver matching Chrome version
RUN export CHROME_VERSION=$(google-chrome --version | cut -d ' ' -f3 | cut -d. -f1) && \
    echo "Installed Chrome Major Version: $CHROME_VERSION" && \
    # Download matching Chromedriver for that version
    wget -q "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/$CHROME_VERSION.0.0.0/linux64/chromedriver-linux64.zip" -O /tmp/chromedriver.zip && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
    mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    rm -rf /usr/local/bin/chromedriver-linux64 /tmp/chromedriver.zip && \
    chmod +x /usr/local/bin/chromedriver


# Cleanup apt cache
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Specify command to run the Flask app
CMD ["python", "app.py"]
