"""
Script to create the database tables for the RVS system
"""
import psycopg2
from psycopg2 import Error
from db_config import POSTGRES_CONFIG

def create_tables():
    try:
        # Connect to PostgreSQL database
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cursor = conn.cursor()

        # Read the SQL file
        with open('create_tables.sql', 'r') as file:
            sql_commands = file.read()

        # Execute the SQL commands
        cursor.execute(sql_commands)
        
        # Commit the changes
        conn.commit()
        print("Tables created successfully!")

    except Error as e:
        print(f"Error while creating tables: {e}")
    finally:
        if conn:
            cursor.close()
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    create_tables() 