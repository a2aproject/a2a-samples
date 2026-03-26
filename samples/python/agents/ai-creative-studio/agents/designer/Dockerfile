FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user for security
RUN adduser --disabled-password --gecos "" agentuser && chown -R agentuser:agentuser /app

# Copy agent code
COPY --chown=agentuser:agentuser agent.py .
COPY --chown=agentuser:agentuser __init__.py .

# Switch to non-root user
USER agentuser

# Set PATH for user-installed packages
ENV PATH="/home/agentuser/.local/bin:$PATH"

# Expose port (Cloud Run will set this automatically)
ENV PORT=8080
ENV HOST=0.0.0.0
EXPOSE 8080

# Run A2A server
CMD ["python", "agent.py"]
