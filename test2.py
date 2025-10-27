import socket
import pymysql
import time
from pymysql.err import OperationalError

def is_network_reachable(host, port):
    try:
        with socket.create_connection((host, port), timeout=5):
            return True
    except (socket.timeout, socket.error):
        return False

# Local MariaDB connection
local_conn = pymysql.connect(
    host='localhost',
    user='root',
    password='Robot123#',
    database='robotdb'
)

# AWS RDS MariaDB details
aws_host = '13.247.23.5'
aws_port = 3306
aws_conn = None

def fetch_table_data(conn, table_name):
    query = f"SELECT * FROM {table_name}"
    with conn.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute(query)
        result = cursor.fetchall()
    return result

def update_or_insert_data(table_name, table_data, aws_conn):
    BATCH_SIZE = 100
    with aws_conn.cursor() as cursor:
        for i in range(0, len(table_data), BATCH_SIZE):
            batch = table_data[i:i + BATCH_SIZE]
            for row in batch:
                columns = ', '.join(row.keys())
                placeholders = ', '.join(['%s'] * len(row))
                updates = ', '.join([f"{col} = VALUES({col})" for col in row.keys()])
                query = f"""
                    INSERT INTO {table_name} ({columns})
                    VALUES ({placeholders})
                    ON DUPLICATE KEY UPDATE {updates}
                """
                MAX_RETRIES = 5
                for attempt in range(MAX_RETRIES):
                    try:
                        cursor.execute(query, list(row.values()))
                        aws_conn.commit()
                        break
                    except OperationalError as e:
                        if e.args[0] == 1205:
                            print(f"Lock wait timeout exceeded. Retrying (Attempt {attempt + 1})...")
                            time.sleep(5)
                        else:
                            raise e
            print(f"Batch {i // BATCH_SIZE + 1} synced successfully.")

if __name__ == "__main__":
    while not is_network_reachable(aws_host, aws_port):
        print("Network unreachable. Retrying in 10 seconds...")
        time.sleep(10)

    print("Network reachable. Proceeding with sync...")
    try:
        aws_conn = pymysql.connect(
            host=aws_host,
            user='robot',
            password='robot123#',
            database='robotdb'
        )
        table_data = fetch_table_data(local_conn, "robotdb.device_data")
        update_or_insert_data("robotdb.device_data", table_data, aws_conn)
        print("Sync completed successfully.")
        aws_conn.close()
    except pymysql.MySQLError as e:
        print(f"Error during sync: {e}")

    local_conn.close()