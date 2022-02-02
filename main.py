from datetime import datetime
from typing import Dict
from dotenv import dotenv_values
from bs4 import BeautifulSoup
import requests
import time
import mysql.connector

config = dotenv_values('.env')

USERNAME = config['ADMIN_PANEL_USERNAME']
PASSWORD = config['ADMIN_PANEL_PASSWORD']
URL = config['ADMIN_PANEL_URL'] + '/userRpm/StatusRpm.htm'
REFRESH = int(config['REFRESH'])

mysql_config = {
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
    'latest_sent_bytes': 0
}


def main() -> None:
    while True:
        latest_traffic_stats = get_latest_traffic_stats()
        if update_straffic_stats(latest_traffic_stats):
            bps_received_rate = get_bps_rate_received()
            bps_sent_rate = get_bps_rate_sent()

            save_to_database(bps_received_rate, bps_sent_rate)
            print(f'Received: {bps_received_rate} - Sent: {bps_sent_rate}')

        time.sleep(REFRESH)


def get_latest_traffic_stats() -> Dict[str, int]:
    res = requests.get(URL, auth=requests.auth.HTTPBasicAuth(USERNAME, PASSWORD))
    res.raise_for_status()

    soup = BeautifulSoup(res.text, features="html.parser")
    for script in soup.find_all('script'):
        if "var statistList" in str(script):
            rates = [int(rate) for rate in str(script).split('\n')[2].split(', ')[:-1]]
            return {'received_bytes': rates[0], 'sent_bytes': rates[1], 'received_packets': rates[2], 'sent_packets': rates[3]}
    
    raise Exception('Unable to find "statistList" variable')

# Return False if the "previous" values are 0 (first script execution) or 
# if the "previous" values are greater than "latest" values (AP reboot)
def update_straffic_stats(latest_traffic_stats) -> bool:
    traffic_stats['previous_received_bytes'] = traffic_stats['latest_received_bytes']
    traffic_stats['previous_sent_bytes'] = traffic_stats['latest_sent_bytes']
    traffic_stats['latest_received_bytes'] = latest_traffic_stats['received_bytes']
    traffic_stats['latest_sent_bytes'] = latest_traffic_stats['sent_bytes']

    return not ((traffic_stats['previous_received_bytes'] == 0 
                and traffic_stats['previous_sent_bytes'] == 0) or (
                    traffic_stats['previous_received_bytes'] > traffic_stats['latest_received_bytes'] 
                    and traffic_stats['previous_sent_bytes'] > traffic_stats['latest_sent_bytes']))



def get_bps_rate_received() -> int:
    delta = traffic_stats['latest_received_bytes'] - traffic_stats['previous_received_bytes']
    return delta / REFRESH * 8

def get_bps_rate_sent() -> int:
    delta = traffic_stats['latest_sent_bytes'] - traffic_stats['previous_sent_bytes']
    return delta / REFRESH * 8

def save_to_database(bps_received, bps_sent) -> None:
    conn = mysql.connector.connect(**mysql_config)
    cursor = conn.cursor()

    query = "INSERT INTO wifi_traffic_stats (datetime, bps_received, bps_sent) VALUES (%s, %s, %s)"
    values = (datetime.now(), bps_received, bps_sent)
    cursor.execute(query, values)

    conn.commit()
    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
