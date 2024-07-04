import json 
import psycopg2

class DB:
    def __init__(self) -> None:
        dbname = "kaas"
        user = "postgres"
        password = "asdf"
        host = "postgres-db-postgresql-ha-pgpool"  # Replace with your PostgreSQL service name in Kubernetes
        port = "5432"  # Replace with your PostgreSQL port if different

        self.conn_string = f"dbname='{dbname}' user='{user}' password='{password}' host='{host}' port='{port}'"

        self.__connect_to_db_server__()
        
        self.__create_table__()


    def __connect_to_db_server__(self):
        
        self.mydb = psycopg2.connect(self.conn_string)
    

    def __create_table__(self):
        mycursor = self.mydb.cursor()
        mycursor.execute("""
            CREATE TABLE IF NOT EXISTS states (
                id SERIAL PRIMARY KEY, 
                app_name VARCHAR(255), 
                failure_count INT DEFAULT 0, 
                success_count INT DEFAULT 0, 
                last_failure TIMESTAMP, 
                last_success TIMESTAMP, 
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        mycursor.close()

    def get_app_info(self,app_name):
        cursor = self.mydb.cursor()
        cursor.execute(f"SELECT * FROM states where app_name = %s",[app_name])

        myresult = cursor.fetchall()
        return myresult

        
    def current_state(self):
        cursor = self.mydb.cursor()
        cursor.execute("SELECT * FROM states")

        myresult = cursor.fetchall()

        return myresult

