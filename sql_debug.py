import sqlite3

# Replace 'your_database.db' with your database file name
database_path = '/tmp/cache.db'

# Replace 'your_table' with the table name you want to view
table_name = 'cache'

def view_table(database_path, table_name):
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()

        # Query to fetch all rows from the table
        cursor.execute(f"SELECT * FROM {table_name}")

        # Fetch all rows
        rows = cursor.fetchall()

        # Get column names
        column_names = [description[0] for description in cursor.description]

        # Print the column names
        print(f"{' | '.join(column_names)}")
        print("-" * 50)

        # Print each row
        for row in rows:
            print(" | ".join(map(str, row)))

    except sqlite3.Error as e:
        print(f"Error occurred: {e}")
    finally:
        # Close the connection
        if conn:
            conn.close()

# Call the function
view_table(database_path, table_name)
