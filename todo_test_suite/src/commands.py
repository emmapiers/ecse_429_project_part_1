import requests
import time
import pytest

url = "http://localhost:4567"
url_shutdown = "http://localhost:4567/shutdown"
url_todos = "http://localhost:4567/todos"

def check_server_status():
    try: 
        response = requests.get(url)
        if response.status_code == 200:
            return True
    except requests.exceptions.ConnectionError:
        return False

def shutdown_server():
        try:
            requests.get(url_shutdown)
            #Server set up where no response is sent and connection error is raised
            print("Server is running.")
            return False
        except requests.exceptions.ConnectionError:
            print("Server is shut down.")
            return True

def delete_all_todos():
    response = requests.get(url_todos)
    todos = response.json().get('todos', [])  #Get all todos

    #Delete each todo individually
    for todo in todos:
        todo_id = todo["id"]
        delete_response = requests.delete(f"{url_todos}/{todo_id}")
        assert delete_response.status_code == 200

def main():
    shutdown_server()

if __name__ == "__main__":
    main()