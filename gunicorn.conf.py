# Picked up automatically by gunicorn from the working directory (the systemd unit
# passes -w/-b on the command line; everything else lives here).
#
# Uploading a reel to Instagram takes well over gunicorn's 30s default, which would
# kill the worker mid-post (seen by callers as a dropped connection).
timeout = 300
graceful_timeout = 60
