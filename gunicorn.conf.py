bind = "0.0.0.0:8000"  # Internal port
workers = 4  # Your 6 vCPU loves this
worker_class = "sync"
timeout = 120
accesslog = "/access.log"
errorlog = "/error.log"
loglevel = "info"
reload = True  # Auto-reload on code change (dev)