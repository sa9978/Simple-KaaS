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

    def new_update(self,app_name,isSuccessfull):
        cursor = self.mydb.cursor()

        cursor.execute(f"SELECT * FROM states where app_name = %s", [app_name])

        result = cursor.fetchall()
        cursor = self.mydb.cursor()
        if len(result)!=0:
            if isSuccessfull:
                sql = f"UPDATE states SET success_count = success_count + 1,  last_success= CURRENT_TIMESTAMP WHERE app_name= %s"
                
            else:
                sql = f"UPDATE states SET failure_count = failure_count + 1,  last_failure= CURRENT_TIMESTAMP WHERE app_name= %s"
            val = [app_name]    
            cursor.execute(sql,val)
        else: 
            if isSuccessfull:
                sql = "INSERT INTO states (app_name, success_count, last_success) VALUES (%s,1,CURRENT_TIMESTAMP)"

                cursor.execute(sql, [app_name])
                
            else:
                sql = "INSERT INTO states (app_name, failure_count, last_failure) VALUES (%s,1,CURRENT_TIMESTAMP)"

                cursor.execute(sql, [app_name])

        self.mydb.commit()

        
    def current_state(self):
        cursor = self.mydb.cursor()
        cursor.execute("SELECT * FROM states")

        myresult = cursor.fetchall()

        return myresult

