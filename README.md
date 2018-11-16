# photobooth

Capitole du Libre Photobooth

Run for development with:

```
mkvirtualenv -p /usr/bin/python3 photobooth
pip install -r requirements.txt

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
docker-compose up -d --build
```
