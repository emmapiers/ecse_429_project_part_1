'''
This module consists of cases when the API behavior is different from the documentation. 
This module shows the actual behavior working. 
The API doesn't behave as documented in these cases, but it is suceeding in an undocumented manner. 
'''
import os
import sys
import requests
import pytest
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.commands import *

#urls for the API
url = "http://localhost:4567/todos"
url_shutdown = "http://localhost:4567/shutdown"
url_docs = "http://localhost:4567/docs"

#Define todos that can be reused throughout the tests
def todo_1():
    return {
        "doneStatus": False,
        "description": "Initial test",
        "title": "Test 1"
    }

#Ensure system is ready to be tested
@pytest.fixture(scope="session", autouse=True)
def check_system_status():
    if not check_server_status():
        pytest.exit("System is not ready for testing. Exiting the test session.", returncode=1)

#Save the system state to restore after test suite is run
@pytest.fixture(scope="module")
def save_system_state():
    #Get initial state before the test
    response = requests.get(url)
    if response.status_code == 200:
        initial_todos = response.json().get('todos', [])
    else:
        initial_todos = []
    
    #Let tests run
    yield initial_todos 

    #Delete all todos
    delete_all_todos()

    #Restore the initial state
    for todo in initial_todos:
        #As per documentation, can't post with an ID 
        todo.pop("id", None)
        
        #Restore doneStatus to proper type BOOLEAN
        if todo["doneStatus"] == "false":
            todo["doneStatus"] = False
        else: 
            todo["doneStatus"] = True

        post_response = requests.post(url, json=todo)
        assert post_response.status_code == 201

#Setup environment for each test
@pytest.fixture(scope="function")
def setup_todos():
    #Remove everything from environment
    delete_all_todos()
    
    # Wait for test to execute
    yield

    #Remove everything from environment
    delete_all_todos()

#Save initial state for the unexpected behavior tests
@pytest.fixture(scope="function")
def save_initial_state(setup_todos):
    #Save the system state before the test
    response = requests.get(url)
    initial_state = response.json().get('todos', [])

    delete_all_todos()
    
    #Wait for test to execute
    yield initial_state

    #Delete anything that was created in the test
    delete_all_todos()

    #Restore initial state
    for todo in initial_state:
        requests.post(url, json=todo)

def test_todos_endpoint_OPTIONS_return_code(save_system_state, setup_todos):
    response = requests.options(url)
    
    #Actual return code but shouldn't be based on documentation
    assert response.status_code == 200

def test_todos_id_endpoint_OPTIONS_return_code(save_system_state, setup_todos):
    post_response = requests.post(url, json=todo_1())
    assert post_response.status_code == 201

    post_response_json = post_response.json()
    post_id = post_response_json.get("id")

    response = requests.options(f"{url}/{post_id}")

    #Actual return code but shouldn't be based on documentation
    assert response.status_code == 200

def test_todos_endpoint_POST_invalid_input_type(save_system_state, setup_todos):
    todo_invalid = {
        "doneStatus":False,
        "description":12, 
        "title":"Homework XX"
    }
    response = requests.post(url, json=todo_invalid)
    assert response.status_code == 201

    response_json = response.json()
     
    #Actual behavior but should not be based on documentation
    expected_description = float(todo_invalid["description"])
    expected_description = str(expected_description)

    assert response_json["title"] == todo_invalid["title"]
    assert response_json["description"] == expected_description

    if response_json["doneStatus"] == "true":
         response_json["doneStatus"] = True
    elif response_json["doneStatus"] == "false":
         response_json["doneStatus"] = False
   
    assert response_json["doneStatus"] == todo_invalid["doneStatus"]
    assert "id" in response_json