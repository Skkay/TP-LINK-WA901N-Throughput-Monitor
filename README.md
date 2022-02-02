# TP-LINK L-WA901N Throughput Monitor 
Get and estimate throughput using the total bytes received and sent information on TP-LINK L-WA901N administration page. Save values in a MySQL database in order to use them with Grafana.

## Configuration and run
- Create `.env` file with:
```dotenv
REFRESH_RATE=60 # In seconds

ADMIN_PANEL_URL="http://192.168.1.254"
ADMIN_PANEL_USERNAME=username
ADMIN_PANEL_PASSWORD=password

MYSQL_USER=username
MYSQL_PASSWORD=password
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=database
```

- Install requirements.txt
```
python -m pip install -r requirements.txt
```

- Run
```
python main.py
```
