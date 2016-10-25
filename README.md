# What is usine ?

Usine as been built to give helper commands to [ikaaro](https://github.com/hforge/ikaaro) instances.
You can easily, deploy on remote, restart, stop, reindex...

# How to configure

1. Create a `.usine` folder in your $HOME directory
2. Create a `instances.ini` file inside this directory
3. Install usine (via `python setup.py install`) inside your wanted local venv

# What contains `instances.ini` ?

For V2 usage
```
# Server definitions
[server $SERVER_NAME]
host = $HOST:$PORT # SSH connexion

# Venv definitions
[pyenv $SERVER_NAME/$PYENV_NAME]
location = $USER@$SERVER_NAME:$PYENV_LOCATION
sources_location = $SOURCES_LOCATION
sources_version = branch:$SOURCES_BRANCH_NAME  # use tag: for a specific tag
log_location = $LOG_LOCATION  # Make sure the directory exists and you have write access

# Ikaaro instances definitions
[ikaaro $INSTANCE_NAME]
pyenv = $SERVER_NAME/$PYENV_NAME
path = $IKAARO_INSTANCE_LOCATION # Inside the venv
uri = $IKAARO_INSTANCE_URI
port = $IKAARO_INSTANCE_PORT
```

# First use

1. Clone your source repo inside the `$SOURCES_LOCATION` directory
2. Make sure to install itools manually first
3. Create your `$LOG_LOCATION` directory, and make the user write access
4. Define your requirements inside your sources `requirements.txt` file
5. Use commands from your local Venv where Usine is installed

# Commands

## Deploy

`$ bin/usine.py pyenv $SERVER_NAME/$PYENV_NAME deploy_v2`
Will connect to ssh to the remote host (if it is a remote host),
fetch sources, install `requirements.txt` using `pip`, and install sources inside the venv,
restart instances.

Logs will be generated:
 - `/var/log/ikaaro-install-requirements.log.log`
 - `/var/log/ikaaro-install-python.log`