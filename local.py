import pymysql
import requests

def check_internet_connection():
    try:
        response = requests.get('https://www.google.com', timeout=5)
        return response.status_code == 200
    except requests.ConnectionError:
        return False

# Check internet connection before proceeding
if not check_internet_connection():
    print("No internet connection. Syncing aborted.")
else:
    try:
        # Local MySQL database connection
        local_conn = pymysql.connect(
            host='localhost',
            user='root',
            password='Robot123#',
            database='robotdb'
        )

        # AWS RDS MySQL connection
        master_conn = pymysql.connect(
            host='13.247.23.5',
            user='robot',
            password='robot123#',
            database='robotdb'
        )

    except pymysql.MySQLError as e:
        if e.args[0] == 2003:  # Error code for "Can't connect to MySQL server"
            print("No internet connection or MySQL server is unreachable.")
        else:
            print(f"Error: {e}")
    else:
        local_cursor = local_conn.cursor()
        master_cursor = master_conn.cursor()

        # Fetch all table names from AWS RDS database
        local_cursor.execute("SHOW TABLES")
        tables = local_cursor.fetchall()

        for table in tables:
            table_name = table[0]
            print(f"Syncing data from table: {table_name}")

            # Fetch data from each table in AWS RDS database
            local_cursor.execute(f"SELECT * FROM {table_name}")
            rows = local_cursor.fetchall()

            # Get column names for the table
            local_cursor.execute(f"SHOW COLUMNS FROM {table_name}")
            columns = [f"`{column[0]}`" for column in local_cursor.fetchall()]

            # Prepare insert query for local database with ON DUPLICATE KEY UPDATE
            placeholders = ', '.join(['%s'] * len(columns))
            columns_list = ', '.join(columns)
            update_clause = ', '.join([f"{col}=VALUES({col})" for col in columns])
            insert_query = f"""
                INSERT INTO `{table_name}` ({columns_list})
                VALUES ({placeholders})
                ON DUPLICATE KEY UPDATE {update_clause}
            """

            for row in rows:
                try:
                    master_cursor.execute(insert_query, row)
                    master_conn.commit()
                except pymysql.MySQLError as e:
                    print(f"Error inserting data into {table_name}: {e}")

        # Close connections
        local_cursor.close()
        local_conn.close()
        master_cursor.close()
        master_conn.close()

        print("Data sync complete.")
