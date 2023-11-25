# Test task using FastApi and SQLAlchemy

-   Python (3.12.0) was used
-   Mysql (5.7) was used

**TO run web app:**

1. Start a virtual environment: `python3 -m venv venv`
2. Activate venv: `source venv/bin/activate`(ubuntu)
3. Install required libs: `pip install -r requirements.txt`
4. Change db URI in `db.py` file
5. Run server: `python main.py`
6. Visit docs page: `127.0.0.1:8000/docs`

**To run bot:**

1. Run web app
2. Use `cd bot`
3. Use `python bot.py`
