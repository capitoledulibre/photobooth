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

```sh
sudo apt install pipx
pipx ensurepath
echo "Restart your shell if you just installed pipx
pipx install pre-commit uv
pre-commit install
```

On MacOS:
```sh
brew install python@3.12 postgresql pipx uv
pipx ensurepath
echo "Restart your shell if you just installed pipx"
pipx install pre-commit
pre-commit install
```

```sh
uv sync
uv run python manage.py migrate
uv run python manage.py runserver 8005
```

Then visit http://localhost:8005

To run with Docker:

* You need an ssh/id_rsa key that is allowed to rsync files to the remote
  server (see settings/production.py). This file need to be readable by user
  "daemon" inside the container (world readable is fine).
* Run:

```sh
docker compose up -d --build
```


## Upgrade packages on MacOS::

```sh
uv lock --upgrade
uv export --no-dev --no-hashes > requirements.txt
pre-commit autoupdate
```
