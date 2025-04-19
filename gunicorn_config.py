"""Gunicorn configuration file"""
import multiprocessing

# Server socket
bind = "unix:/run/gunicorn.sock"
workers = multiprocessing.cpu_count() * 2 + 1

# Logging
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"

# Process naming
proc_name = "hoto"

# SSL Configuration
keyfile = "/etc/letsencrypt/live/your-domain.com/privkey.pem"
certfile = "/etc/letsencrypt/live/your-domain.com/fullchain.pem"

# Worker timeout
timeout = 120 