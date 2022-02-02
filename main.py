from datetime import datetime
from typing import Dict
from dotenv import dotenv_values
from bs4 import BeautifulSoup
import requests
import time
import mysql.connector

config = dotenv_values('.env')

REFRESH_RATE = int(config['REFRESH_RATE'])
ADMIN_PANEL_URL = config['ADMIN_PANEL_URL'] + '/userRpm/StatusRpm.htm'
ADMIN_PANEL_USERNAME = config['ADMIN_PANEL_USERNAME']
ADMIN_PANEL_PASSWORD = config['ADMIN_PANEL_PASSWORD']
MYSQL_CONFIG = {
    'user': config['MYSQL_USER'],
    'password': config['MYSQL_PASSWORD'],
    'host': config['MYSQL_HOST'],
    'port': config['MYSQL_PORT'],
    'database': config['MYSQL_DATABASE'],
    'raise_on_warnings': True
}

traffic_stats = {
    'previous_received_bytes': 0,
    'latest_received_bytes': 0,
    'previous_sent_bytes': 0,
    'latest_sent_bytes': 0,
    'bps_received_rate': 0,
    'bps_sent_rate': 0
}


def main() -> None:
    while True:
        update_traffic_stats()
        save_to_database()
        print(f"Received: {traffic_stats['bps_received_rate']} - Sent: {traffic_stats['bps_sent_rate']}")
        time.sleep(REFRESH_RATE)

def get_latest_traffic_stats() -> Dict[str, int]:
    res = requests.get(ADMIN_PANEL_URL, auth=requests.auth.HTTPBasicAuth(ADMIN_PANEL_USERNAME, ADMIN_PANEL_PASSWORD))
    res.raise_for_status()

    soup = BeautifulSoup(res.text, features="html.parser")
    for script in soup.find_all('script'):
        if "var statistList" in str(script):
            rates = [int(rate) for rate in str(script).split('\n')[2].split(', ')[:-1]]
            return {'received_bytes': rates[0], 'sent_bytes': rates[1], 'received_packets': rates[2], 'sent_packets': rates[3]}
    
    raise Exception('Unable to find "statistList" variable')

# Update BPS if the "previous" values are 0 (first script execution) or 
# if the "previous" values are greater than "latest" values (AP reboot)
def update_traffic_stats() -> None:
    latest_traffic_stats = get_latest_traffic_stats()

    traffic_stats['previous_received_bytes'] = traffic_stats['latest_received_bytes']
    traffic_stats['previous_sent_bytes'] = traffic_stats['latest_sent_bytes']
    traffic_stats['latest_received_bytes'] = latest_traffic_stats['received_bytes']
    traffic_stats['latest_sent_bytes'] = latest_traffic_stats['sent_bytes']

    if not ((traffic_stats['previous_received_bytes'] == 0 
                and traffic_stats['previous_sent_bytes'] == 0) or (
                    traffic_stats['previous_received_bytes'] > traffic_stats['latest_received_bytes'] 
                    and traffic_stats['previous_sent_bytes'] > traffic_stats['latest_sent_bytes'])):
        traffic_stats['bps_received_rate'] = get_bps_rate_received()
        traffic_stats['bps_sent_rate'] = get_bps_rate_sent()


def get_bps_rate_received() -> int:
    delta = traffic_stats['latest_received_bytes'] - traffic_stats['previous_received_bytes']
    return delta / REFRESH_RATE * 8

def get_bps_rate_sent() -> int:
    delta = traffic_stats['latest_sent_bytes'] - traffic_stats['previous_sent_bytes']
    return delta / REFRESH_RATE * 8

def save_to_database() -> None:
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()

    query = "INSERT INTO wifi_traffic_stats (datetime, bps_received, bps_sent) VALUES (%s, %s, %s)"
    values = (datetime.now(), traffic_stats['bps_received_rate'], traffic_stats['bps_sent_rate'])
    cursor.execute(query, values)

    conn.commit()
    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
