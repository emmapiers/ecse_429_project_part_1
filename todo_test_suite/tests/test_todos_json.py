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

def todo_2():
    return {
        "doneStatus": True,
        "description": "Initial test",
        "title": "Test 2"
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

def test_todos_endpoint_GET_empty(save_system_state, setup_todos):
    response = requests.get(url)
    assert response.status_code == 200

    response_json = response.json()
    todos = response_json.get('todos', [])
    
    assert len(todos) == 0

def test_todos_endpoint_GET_one(save_system_state, setup_todos):
    post_response = requests.post(url, json=todo_1())
    assert post_response.status_code == 201

    response = requests.get(url)
    assert response.status_code == 200

    response_json = response.json()
    response_todos = response_json.get('todos', [])

    #Assert length and all fields are correct
    assert len(response_todos) == 1

    assert response_todos[0]["description"] == todo_1()["description"]
    assert response_todos[0]["title"] == todo_1()["title"]
    if response_todos[0]["doneStatus"] == "false":
        response_todos[0]["doneStatus"] = False
    elif response_todos[0]["doneStatus"] == "true":
        response_todos[0]["doneStatus"] = True
        
    assert response_todos[0]["doneStatus"] == todo_1()["doneStatus"]

def test_todos_endpoint_GET_two(save_system_state, setup_todos):
    post_response_1 = requests.post(url, json=todo_1())
    assert post_response_1.status_code == 201

    post_response_2 = requests.post(url, json=todo_2())
    assert post_response_2.status_code == 201

    response = requests.get(url)
    assert response.status_code == 200

    response_json = response.json()
    response_todos = response_json.get('todos', [])
    
    assert len(response_todos) == 2

    observed_todo_1 = {
        "doneStatus": True if response_todos[0]["doneStatus"] in ["true"] else False,
        "description": response_todos[0]["description"],
        "title": response_todos[0]["title"]
    }
    observed_todo_2 = {
        "doneStatus": True if response_todos[1]["doneStatus"] in ["true"] else False,
        "description": response_todos[1]["description"],
        "title": response_todos[1]["title"]
    }

    #Asser that the posted todos are the same as the observed ones, accounting for ordering
    assert observed_todo_1 in [todo_1(), todo_2()]
    assert observed_todo_1 in [todo_1(), todo_2()]

    assert observed_todo_1 != observed_todo_2

def test_todos_endpoint_POST(save_system_state, setup_todos):
    response = requests.post(url, json=todo_1())
    assert response.status_code == 201

    response_json = response.json()
     
    #Assert all fields are correct and present
    assert response_json["title"] == todo_1()["title"]
    assert response_json["description"] == todo_1()["description"]

    if response_json["doneStatus"] == "true":
         response_json["doneStatus"] = True
    elif response_json["doneStatus"] == "false":
         response_json["doneStatus"] = False
   
    assert response_json["doneStatus"] == todo_1()["doneStatus"]
    assert "id" in response_json
    
def test_todos_endpoint_HEAD(save_system_state, setup_todos):
    response = requests.head(url)
    assert response.status_code == 200

    #Assert that expected headers are present
    assert 'Content-Type' in response.headers
    assert response.headers['Content-Type'] == 'application/json'
    
    assert 'Server' in response.headers
    assert 'Jetty' in response.headers['Server']

    assert 'Date' in response.headers

    assert 'Transfer-Encoding' in response.headers
    assert response.headers['Transfer-Encoding'] == 'chunked'

def test_todos_id_endpoint_GET(save_system_state, setup_todos):
    post_response = requests.post(url, json=todo_1())
    assert post_response.status_code == 201

    post_response_json = post_response.json()
    post_id = post_response_json.get("id")
    
    response = requests.get(f"{url}/{post_id}")
    assert response.status_code == 200

    response_json = response.json()
    response_todos = response_json.get('todos', [])

    assert response_todos[0]["description"] == todo_1()["description"]
    assert response_todos[0]["title"] == todo_1()["title"]
    
    if response_todos[0]["doneStatus"] == "false":
        response_todos[0]["doneStatus"] = False
    elif response_todos[0]["doneStatus"] == "true":
        response_todos[0]["doneStatus"] = True
   
    assert response_todos[0]["doneStatus"] == todo_1()["doneStatus"]
    assert response_todos[0]["id"] == post_id
    
def test_todos_id_endpoint_POST(save_system_state, setup_todos):
    post_response = requests.post(url, json=todo_1())
    assert post_response.status_code == 201

    post_response_json = post_response.json()
    post_id = post_response_json.get("id")

    todo_1_amended = {
        "doneStatus": True,
    }  
    #Update todo_1 with todo_1_amended
    response = requests.post(f"{url}/{post_id}", json=todo_1_amended)
    assert response.status_code == 200

    response_json = response.json()

    assert response_json["title"] == todo_1()["title"]
    assert response_json["description"] == todo_1()["description"]

    if response_json["doneStatus"] == "true":
         response_json["doneStatus"] = True
    elif response_json["doneStatus"] == "false":
         response_json["doneStatus"] = False
   
    assert response_json["doneStatus"] == todo_1_amended["doneStatus"]
    assert response_json["id"] == post_id
  
def test_todos_id_endpoint_PUT(save_system_state, setup_todos):
    post_response = requests.post(url, json=todo_1())
    assert post_response.status_code == 201

    post_response_json = post_response.json()
    post_id = post_response_json.get("id")

    todo_1_amended =  {
        "description": "New description",
        "title": "New title"
    }
    
    #Update todo_1 with todo_1_amended
    response = requests.put(f"{url}/{post_id}", json=todo_1_amended)
    assert response.status_code == 200

    response_json = response.json()

    #Assert all fields are correct and present
    assert response_json["title"] == todo_1_amended["title"]
    assert response_json["description"] == todo_1_amended["description"]

    if response_json["doneStatus"] == "true":
         response_json["doneStatus"] = True
    elif response_json["doneStatus"] == "false":
         response_json["doneStatus"] = False
   
    assert response_json["doneStatus"] == todo_1()["doneStatus"]
    assert response_json["id"] == post_id
   
def test_todos_id_endpoint_HEAD(save_system_state, setup_todos):
    post_response = requests.post(url, json=todo_1())
    assert post_response.status_code == 201

    post_response_json = post_response.json()
    post_id = post_response_json.get("id")


    response = requests.head(f"{url}/{post_id}")
    assert response.status_code == 200

    #Assert that expected headers are present
    assert 'Content-Type' in response.headers
    assert response.headers['Content-Type'] == 'application/json'
    
    assert 'Server' in response.headers
    assert 'Jetty' in response.headers['Server']

    assert 'Date' in response.headers

    assert 'Transfer-Encoding' in response.headers
    assert response.headers['Transfer-Encoding'] == 'chunked'

def test_todos_id_endpoint_DELETE_empty(save_system_state, setup_todos):
    post_response = requests.post(url, json=todo_1())
    assert post_response.status_code == 201

    post_response_json = post_response.json()
    post_id = post_response_json.get("id")

    response = requests.delete(f"{url}/{post_id}")
    assert response.status_code == 200
    
    response = requests.get(url)
    assert response.status_code == 200

    response_json = response.json()
    response_todos = response_json.get('todos', [])
    
    #Assert that after posting one todo and deleting one todo, there is no todos present
    assert len(response_todos) == 0

def test_todos_id_endpoint_DELETE_not_empty(save_system_state, setup_todos):
    post_response = requests.post(url, json=todo_1())
    assert post_response.status_code == 201

    post_response = requests.post(url, json=todo_2())
    assert post_response.status_code == 201

    post_response_json = post_response.json()
    post_id = post_response_json.get("id")

    response = requests.delete(f"{url}/{post_id}")
    assert response.status_code == 200
    
    response = requests.get(url)
    assert response.status_code == 200

    response_json = response.json()
    response_todos = response_json.get('todos', [])
    
    #Assert that after posting two todos and deleting one todo, there is one todo present
    assert len(response_todos) == 1

def test_todos_endpoint_SHUTDOWN_mock(save_system_state):
    # Mock the requests.get function to simulate the shutdown call without actually shutting down the server
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        
        #Simulate calling the shutdown endpoint
        response = requests.get(url_shutdown)

        #Ensure the mocked request was called
        mock_get.assert_called_once_with(url_shutdown)

        #Assert the response was successful mocked
        assert response.status_code == 200

def test_todos_endpoint_DOCS(save_system_state):
    response = requests.get(url_docs)
    assert response.status_code == 200
    
    assert response.headers['Content-Type'] == 'text/html'

#Show that changes to data in the system are restricted to those which should change based on the API operation
def test_todos_endpoint_GET_no_side_effects(save_initial_state, save_system_state):
    initial_state = save_initial_state

    response = requests.get(url)
    assert response.status_code == 200

    current_state = requests.get(url).json().get('todos', [])

    #Ensure that no unexpected changes occurred to the state after get call
    assert current_state== initial_state

def test_todos_endpoint_HEAD_no_side_effects(save_initial_state, save_system_state):
    initial_state = save_initial_state
    #Make sure no body text is returned
    response = requests.head(url)
    assert response.status_code == 200

    assert response.text.strip() == ""

    #Check if todos are unaffected
    current_state = requests.get(url).json().get('todos', [])
    assert current_state == initial_state

def test_todos_endpoint_id_DELETE_no_side_effects(save_initial_state, save_system_state):
    initial_state = save_initial_state

    post_response = requests.post(url, json=todo_1())
    assert post_response.status_code == 201

    #Check that todo_1 has been added
    current_state = requests.get(url).json().get('todos', [])
    assert len(current_state) == len(initial_state) + 1

    #Get the todo to delete (last one added)
    todo_to_delete = current_state[-1]
    todo_id = todo_to_delete["id"]

    delete_response = requests.delete(f"{url}/{todo_id}")
    assert delete_response.status_code == 200

    # Assert that current state matches deleted
    current_state = requests.get(url).json().get('todos', [])
    assert len(current_state) == len(initial_state)

    assert todo_to_delete not in current_state

def test_todos_endpoint_id_PUT_no_side_effects(save_initial_state, save_system_state):
    initial_state = save_initial_state

    post_response = requests.post(url, json=todo_1())
    assert post_response.status_code == 201

    post_response_json = post_response.json()
    todo_id = post_response_json.get("id")

    todo_1_amended = {
        "description": "New description",
        "title": "New title"
    }
    #Amend todo_1 to todo_1_amended
    put_response = requests.put(f"{url}/{todo_id}", json=todo_1_amended)
    assert put_response.status_code == 200

    #Assert that todo_1 was posted 
    current_state = requests.get(url).json().get('todos', [])
    assert len(current_state) == len(initial_state) + 1

    #Get the todo updated (last one added)
    updated_todo = current_state[-1]

    assert updated_todo["title"] == todo_1_amended["title"]
    assert updated_todo["description"] == todo_1_amended["description"]
   
    if updated_todo["doneStatus"]== "true":
        updated_todo["doneStatus"] = True
    elif updated_todo["doneStatus"]== "false":
        updated_todo["doneStatus"] = False

    assert updated_todo["doneStatus"] == todo_1()["doneStatus"]

    #Assert no other todos have been unexpectedly changed
    new_todos = [todo for todo in current_state if todo not in initial_state]
    assert len(new_todos) == 1
    
    unchanged_todos = [todo for todo in current_state if todo in initial_state]
    assert len(unchanged_todos) == len(initial_state)
    for initial_todo in initial_state:
        assert initial_todo in unchanged_todos


def test_todos_endpoint_POST_no_side_effects(save_initial_state, save_system_state):
    initial_state = save_initial_state

    post_response = requests.post(url, json=todo_1())
    assert post_response.status_code == 201
    
    current_state = requests.get(url).json().get('todos', [])
    
    #Assert that one todo was added
    assert len(current_state) == len(initial_state) + 1

    #Assert no other todos have been unexpectedly changed
    new_todos = [todo for todo in current_state if todo not in initial_state]
    assert len(new_todos) == 1
    
    unchanged_todos = [todo for todo in current_state if todo in initial_state]
    assert len(unchanged_todos) == len(initial_state)
    for initial_todo in initial_state:
        assert initial_todo in unchanged_todos
    
def test_todos_endpoint_DELETE_return_code(save_system_state, setup_todos):
     #An unsupported endpoint
     response = requests.delete(url)
     assert response.status_code == 405

def test_todos_endpoint_PUT_return_code(save_system_state, setup_todos):
     #An unsupported endpoint
     response = requests.put(url, json=todo_1())
     assert response.status_code == 405

def test_todos_id_endpoint_DELETE_invalid(save_system_state, setup_todos):
    post_response = requests.post(url, json=todo_1())
    assert post_response.status_code == 201

    post_response_json = post_response.json()
    post_id = post_response_json.get("id")

    first_response = requests.delete(f"{url}/{post_id}")
    assert first_response.status_code == 200

    #Assert invalid status code when trying to delete something that doesn't exist
    response = requests.delete(f"{url}/{post_id}")
    assert response.status_code == 404
    
def test_todos_endpoint_POST_malformed_json(save_system_state, setup_todos):
    #Deliberate malformed json
    malformed_json = '{"title": "Test Task", "doneStatus": false, "description": "Malformed JSON"'

    response = requests.post(url, data=malformed_json)
    
    #Assert that the malformed json error is caught
    assert response.status_code == 400

