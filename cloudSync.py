import mysql.connector
import time
import socket
import sys
import platform

def check_internet(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False

# Internet check loop
print("Checking for internet connection...")
while not check_internet():
    print("No internet connection. Retrying in 10 seconds...")
    time.sleep(10)
print("Internet connection established.")

local_conn = master_conn = None
local_cursor = update_cursor = master_cursor = None
start_time = time.localtime() 
missing_count = 0;
start_record=  "";
end_record = "";
try:
    print("Connecting to local database...")
    local_conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='Robot123#',
        database='robotdb'
    )
    print("Connected to local database.")

    print("Connecting to cloud database...")
    master_conn = mysql.connector.connect(
        host='13.247.23.5',
        user='robot',
        password='robot123#',
        database='robotdb'
    )
    print("Connected to cloud database.")

    local_cursor = local_conn.cursor(dictionary=True)
    update_cursor = local_conn.cursor()
    master_cursor = master_conn.cursor()

    print("Fetching data from local data_q table where Update_status = 'no'...")
    local_cursor.execute("SELECT * FROM data_q WHERE Update_status = 'no'")
    rows = local_cursor.fetchall()
    print(f"Fetched {len(rows)} rows.")

    for index, row in enumerate(rows, start=1):
        print(f"\nProcessing row {index} with D_Number: {row['D_Number']}")
        if index == 1:
            start_record = row['D_Number']# First record

        end_record = row['D_Number']  # Will overwrite on each iteration—ends with the last one


        try:
            master_cursor.execute(
                "SELECT 1 FROM device_data WHERE D_Number = %s",
                (row['D_Number'],)
            )
            exists = master_cursor.fetchone()

            if not exists:
                print(f"D_Number {row['D_Number']} not found in cloud. Inserting...")
                insert_query = """
                    INSERT INTO device_data (
                        D_Number, Start_date, End_date, Diagnostic, Code, Serial,
                        Operator_Id, Bed_Id, Side, Insert_date
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,NOW())
                """
                master_cursor.execute(insert_query, (
                    row['D_Number'], row['Start_date'], row['End_date'],
                    row['Diagnostic'], row['Code'], row['Serial'],
                    row['Operator_Id'], row['Bed_Id'], row['Side']
                ))
                missing_count += 1  # Increment count
                print(f"Inserted D_Number {row['D_Number']} into cloud.")
            else:
                print(f"D_Number {row['D_Number']} already exists in cloud. Skipping insert.")

            update_cursor.execute(
                "UPDATE data_q SET Update_status = 'yes' WHERE D_Number = %s",
                (row['D_Number'],)
            )
            print(f"Updated local Update_status to 'yes' for D_Number {row['D_Number']}.")

        except mysql.connector.Error as e:
            print(f"Error processing row {row['D_Number']}: {e}")
            
    

    end_time = time.localtime()     
    sync_insert_query = """
        INSERT INTO sync_log (
            Sync_log_Id, Operation_type, Start_date, End_date, Number_Of_Records, Start_record,
            End_record, Output
        ) VALUES (CONCAT(%s, ' ', %s), %s, %s, %s, %s, %s, %s, %s)
    """
    values = (platform.node(), end_time,'Data Upload', start_time, end_time, missing_count,start_record, end_record,'Upload Complete')
    master_cursor.execute(sync_insert_query, values)
    print(f"Also inserted  {missing_count} rows into sync_log table.")        

    print("Fetching data from local data_q table where Update_status = 'no'...")
    local_cursor.execute("SELECT * FROM sync_log")
    rows = local_cursor.fetchall()
    print(f"Fetched {len(rows)} rows.")
    
    
    if missing_count > 0:
        for index, row in enumerate(rows, start=1):
            print(f"\nProcessing row {index} with Sync_log_Id: {row['Sync_log_Id']}")
        
            try:
                master_cursor.execute(
                    "SELECT 1 FROM sync_log WHERE Sync_log_Id = %s",
                    (row['Sync_log_Id'],)
                )
                exists = master_cursor.fetchone()

                if not exists:
                    print(f"Sync_log_Id {row['Sync_log_Id']} not found in cloud. Inserting...")
                    insert_query = """
                        INSERT INTO sync_log (
                            Sync_log_Id, Operation_type, Start_date, End_date, Number_Of_Records, Start_record, End_record, Output
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    master_cursor.execute(insert_query, (
                        row['Sync_log_Id'], row['Operation_type'], row['Start_date'],
                        row['End_date'], row['Number_Of_Records'], row['Start_record'],
                        row['End_record'], row['Output']
                    ))
                
                    print(f"Inserted Sync_log_Id {row['Sync_log_Id']} into cloud.")
                else:
                    print(f"Sync_log_Id {row['Sync_log_Id']} already exists in cloud. Skipping insert.")

           
            except mysql.connector.Error as e:
                print(f"Error processing row {row['Sync_log_Id']}: {e}")
    print("Committing changes to local and cloud databases...")
    local_conn.commit()
    master_conn.commit()
    print("Commits complete.")

except mysql.connector.Error as db_err:
    print(f"Database connection or query error: {db_err}")
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {e}")
    sys.exit(1)
finally:
    print("Closing all cursors and connections...")
    try:
        if local_cursor: local_cursor.close()
        if update_cursor: update_cursor.close()
        if master_cursor: master_cursor.close()
        if local_conn: local_conn.close()
        if master_conn: master_conn.close()
        print("All connections closed. Script complete.")
    except Exception as close_err:
        print(f"Error during cleanup: {close_err}")