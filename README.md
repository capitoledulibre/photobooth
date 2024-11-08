# Photobooth

Capitole du Libre Photobooth

Simple Django Web application for a photobooth. Main features are:
- simple du deploy with Docker
- local or remote web application
- push pictures on a remote server (rsync) and display QRcode to download picture

Requirements:
- a webcam for taking pictures
- a computer with a web browser
- a mouse (a click on mouse will take pictures)

We recommend pipx usage on Ubuntu/Debian:

```
sudo apt install pipx
pipx ensurepath
echo "Restart your shell if you just installed pipx
pipx install poetry pre-commit
pre-commit install
```

On MacOS:
```
brew install python@3.12 pipx
pipx ensurepath
echo "Restart your shell if you just installed pipx"
pipx install poetry pre-commit
pre-commit install
poetry env use python3.12
```

```
poetry install --no-root --sync
poetry shell

python manage.py migrate
python manage.py runserver 8005
```

Then visit http://localhost:8005

To run with Docker:

* You need an ssh/id_rsa key that is allowed to rsync files to the remote
  server (see settings/production.py). This file need to be readable by user
  "daemon" inside the container (world readable is fine).
* Run:

```
docker compose up -d --build
```


## Upgrade packages on MacOS::

```
poetry update
poetry self add poetry-plugin-export
poetry export --without-hashes --only main -f requirements.txt --output requirements.txt

pre-commit autoupdate
```
