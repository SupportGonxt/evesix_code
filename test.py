import socket
import pymysql
import time

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
aws_port = 3306  # Default MariaDB/MySQL port
aws_conn = None

def fetch_tables(conn):
    query = "SHOW TABLES"
    with conn.cursor() as cursor:
        cursor.execute(query)
        tables = cursor.fetchall()
    return [table[0] for table in tables]

def fetch_table_data(conn, table_name):
    query = f"SELECT * FROM {table_name}"
    with conn.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute(query)
        result = cursor.fetchall()
    return result

def update_or_insert_data(table_name, table_data, aws_conn):
    with aws_conn.cursor() as cursor:
        for row in table_data:
            columns = ', '.join(row.keys())
            placeholders = ', '.join(['%s'] * len(row))
            updates = ', '.join([f"{col} = VALUES({col})" for col in row.keys()])
            query = f"""
                INSERT INTO {table_name} ({columns})
                VALUES ({placeholders})
                ON DUPLICATE KEY UPDATE {updates}
            """
            cursor.execute(query, list(row.values()))
            aws_conn.commit()
        print(f"Data synced to table {table_name} successfully.")

if __name__ == "__main__":
    while not is_network_reachable(aws_host, aws_port):
        print("Network unreachable. Retrying in 10 seconds...")
        time.sleep(10)  # Wait for 10 seconds before retrying

    print("Network reachable. Proceeding with sync...")
    
    try:
        aws_conn = pymysql.connect(
            host=aws_host,
            user='robot',
            password='robot123#',
            database='robotdb'
        )

        # Fetch and sync table data
        table_data = fetch_table_data(local_conn, "robotdb.device_data")
        update_or_insert_data("robotdb.device_data", table_data, aws_conn)
        print("Sync completed successfully.")

        # Close the AWS connection
        aws_conn.close()
    except pymysql.MySQLError as e:
        print(f"Error during sync: {e}")

    # Close the local connection
    local_conn.close()