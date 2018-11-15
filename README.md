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

To run with Docker, use:

```
docker-compose up -d --build
```
