FROM python:3.9-alpine

# Install python packages
COPY requirements.txt /app/requirements.txt
RUN pip --disable-pip-version-check --no-cache-dir install -r /app/requirements.txt

# Copy source files
COPY app.py /app
COPY project/ /app/project/
WORKDIR /app

# Start application
ENV FLASK_APP=/app/app.py
ENTRYPOINT ["python", "-m", "flask", "run", "--host=0.0.0.0"]