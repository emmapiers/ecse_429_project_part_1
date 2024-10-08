import os
import sys
import requests
import pytest
import xml.etree.ElementTree as ET

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.commands import *

#urls of the API
url = "http://localhost:4567/todos"
url_shutdown = "http://localhost:4567/shutdown"
url_docs = "http://localhost:4567/docs"
 
#Define todos and header that can be reused throughout the tests
def todo_1():
    return """
    <todo>
        <doneStatus>False</doneStatus>
        <description>Initial test</description>
        <title>Test 1</title>
    </todo>
    """

def todo_2():
    return """
    <todo>
        <doneStatus>True</doneStatus>
        <description>Initial test</description>
        <title>Test 2</title>
    </todo>
    """

def headers(): 
    return {
        "Accept": "application/xml", 
        "Content-Type": "application/xml"
    }

def parse_xml_response(response_content):
    #In order to be able to check application logic/return values
    return ET.fromstring(response_content)

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

    # Get the current system state before the test
    response = requests.get(url)
    initial_state = response.json().get('todos', [])

    delete_all_todos()
    
    # Yield control to the test
    yield initial_state

    # After the test, restore the initial state to clean up
    delete_all_todos()
    for todo in initial_state:
        requests.post(url, json=todo)  # Restore saved state

def test_todos_endpoint_GET_empty_xml(save_system_state, setup_todos):
    response = requests.get(url, headers=headers())
    assert response.status_code == 200
    response_xml = response.content
    
    todos = parse_xml_response(response_xml)
    todos_list = todos.findall('todo') 
    assert len(todos_list) == 0 
    
def test_todos_endpoint_GET_one_xml(save_system_state, setup_todos):
    post_response = requests.post(url, data=todo_1(), headers=headers())
    assert post_response.status_code == 201

    response = requests.get(url, headers=headers())
    assert response.status_code == 200

    todos = parse_xml_response(response.content)
    todos_list = todos.findall('todo')

    observed_todo_1 = {
        "doneStatus": todos_list[0].find("doneStatus").text,
        "description": todos_list[0].find("description").text,
        "title": todos_list[0].find("title").text
    }
    expected_todo_1 = {
        "doneStatus": "false", 
        "description": "Initial test",
        "title": "Test 1"
    }

    assert len(todos_list) == 1
    assert observed_todo_1 == expected_todo_1

def test_todos_endpoint_GET_two_xml(save_system_state, setup_todos):
    post_response_1 = requests.post(url, data=todo_1(), headers=headers())
    assert post_response_1.status_code == 201

    post_response_2 = requests.post(url, data=todo_2(), headers=headers())
    assert post_response_2.status_code == 201

    response = requests.get(url, headers=headers())
    assert response.status_code == 200

    todos = parse_xml_response(response.content)
    todos_list = todos.findall('todo')

    observed_todo_1 = {
        "doneStatus": todos_list[0].find("doneStatus").text,
        "description": todos_list[0].find("description").text,
        "title": todos_list[0].find("title").text
    }

    observed_todo_2 = {
        "doneStatus": todos_list[1].find("doneStatus").text,
        "description": todos_list[1].find("description").text,
        "title": todos_list[1].find("title").text
    }

    expected_todo_1 = {
        "doneStatus": "false", 
        "description": "Initial test",
        "title": "Test 1"
    }

    expected_todo_2 = {
        "doneStatus": "true",
        "description": "Initial test",
        "title": "Test 2"
    }

    #Assert the observed todos match the expected todos
    assert observed_todo_1 in [expected_todo_1, expected_todo_2]
    assert observed_todo_2 in [expected_todo_1, expected_todo_2]

    #Ensure the two todos are not the same
    assert observed_todo_1 != observed_todo_2

def test_todos_endpoint_POST_xml(save_system_state, setup_todos):
    response = requests.post(url, data=todo_1(), headers=headers())
    assert response.status_code == 201

    todos = parse_xml_response(response.content)
    

    observed_todo_1 = {
        "doneStatus": todos.find("doneStatus").text,
        "description": todos.find("description").text,
        "title": todos.find("title").text
    }
    expected_todo_1 = {
        "doneStatus": "false", 
        "description": "Initial test",
        "title": "Test 1"
    }

    #Assert all fields are correct and present
    assert observed_todo_1 == expected_todo_1
    assert todos.find("id") is not None

def test_todos_endpoint_HEAD_xml(save_system_state, setup_todos):
    response = requests.head(url, headers=headers())
    assert response.status_code == 200

    #Assert that expected headers are present
    assert 'Content-Type' in response.headers
    assert response.headers['Content-Type'] == 'application/xml'
    
    assert 'Server' in response.headers
    assert 'Jetty' in response.headers['Server']
    
    assert 'Date' in response.headers, "Missing 'Date' header"
    
    assert 'Transfer-Encoding' in response.headers
    assert response.headers['Transfer-Encoding'] == 'chunked'
    
def test_todos_id_endpoint_GET_xml(save_system_state, setup_todos):
    post_response = requests.post(url, data=todo_1(), headers=headers())
    assert post_response.status_code == 201

    post_response_xml = parse_xml_response(post_response.content)
    post_id = post_response_xml.find("id").text
    
    response = requests.get(f"{url}/{post_id}", headers=headers())
    assert response.status_code == 200

    todos = parse_xml_response(response.content)
    todos_list = todos.findall('todo')
    
    observed_todo_1 = {
        "doneStatus": todos_list[0].find("doneStatus").text,
        "description": todos_list[0].find("description").text,
        "title": todos_list[0].find("title").text
    }

    expected_todo_1 = {
        "doneStatus": "false", 
        "description": "Initial test",
        "title": "Test 1"
    }

    assert observed_todo_1 == expected_todo_1

def test_todos_id_endpoint_POST_xml(save_system_state, setup_todos):
    post_response = requests.post(url, data=todo_1(), headers=headers())
    assert post_response.status_code == 201

    post_response_xml = parse_xml_response(post_response.content)
    post_id = post_response_xml.find("id").text

    todo_1_amended= '''
    <todo>
        <doneStatus>True</doneStatus>
    </todo>
    '''

    # Update todo_1 with todo_1_amended
    response = requests.post(f"{url}/{post_id}", data=todo_1_amended, headers=headers())
    assert response.status_code == 200

    todos = parse_xml_response(response.content)
    observed_todo_1 = {
        "doneStatus": todos.find("doneStatus").text,
        "description": todos.find("description").text,
        "title": todos.find("title").text
    }
    observed_id = todos.find("id").text

    expected_todo_1 = {
        "doneStatus": "true", #Updated 
        "description": "Initial test",
        "title": "Test 1"
    }

    assert observed_todo_1 == expected_todo_1 
    assert observed_id == post_id

def test_todos_id_endpoint_PUT_xml(save_system_state, setup_todos):
    post_response = requests.post(url, data=todo_1(), headers=headers())
    assert post_response.status_code == 201

    post_response_xml = parse_xml_response(post_response.content)
    post_id = post_response_xml.find("id").text
    
    todo_1_amended= '''
        <todo>
            <description>New description</description>
            <title>New title</title>
        </todo>
        '''
    
    #Update todo_1 with todo_1_amended
    response = requests.put(f"{url}/{post_id}", data=todo_1_amended, headers=headers())
    assert response.status_code == 200

    todos = parse_xml_response(response.content)
    observed_todo_1 = {
        "doneStatus": todos.find("doneStatus").text,
        "description": todos.find("description").text,
        "title": todos.find("title").text
    }
    observed_id = todos.find("id").text

    expected_todo_1 = {
        "doneStatus": "false", 
        "description": "New description", #Updated 
        "title": "New title" #Updated 
    }

    assert observed_todo_1 == expected_todo_1 
    assert observed_id == post_id

def test_todos_id_endpoint_HEAD_xml(save_system_state, setup_todos):
    post_response = requests.post(url, data=todo_1(), headers=headers())
    assert post_response.status_code == 201

    post_response_xml = parse_xml_response(post_response.content)
    post_id = post_response_xml.find("id").text
    
    response = requests.head(f"{url}/{post_id}", headers=headers())

    #Assert proper headers
    assert response.status_code == 200
    assert "Content-Type" in response.headers
    assert response.headers["Content-Type"] == "application/xml"
    
    assert 'Server' in response.headers
    assert 'Jetty' in response.headers['Server']
    
    assert 'Date' in response.headers, "Missing 'Date' header"
    
    assert 'Transfer-Encoding' in response.headers
    assert response.headers['Transfer-Encoding'] == 'chunked'

def test_todos_id_endpoint_DELETE_empty_xml(save_system_state, setup_todos):
    post_response = requests.post(url, data=todo_1(), headers=headers())
    assert post_response.status_code == 201

    post_response_xml = parse_xml_response(post_response.content)
    post_id = post_response_xml.find("id").text

    delete_response = requests.delete(f"{url}/{post_id}", headers=headers())
    assert delete_response.status_code == 200
    
    get_response = requests.get(url, headers=headers())
    assert get_response.status_code == 200

    get_response_xml = parse_xml_response(get_response.content)
    todos = get_response_xml.findall("todo")

    #Assert that there are no todos left
    assert len(todos) == 0

def test_todos_id_endpoint_DELETE_not_empty_xml(save_system_state, setup_todos):
    post_response_1 = requests.post(url, data=todo_1(), headers=headers())
    assert post_response_1.status_code == 201

    post_response_2 = requests.post(url, data=todo_2(), headers=headers())
    assert post_response_2.status_code == 201

    post_response_xml = parse_xml_response(post_response_2.content)
    post_id = post_response_xml.find("id").text

    delete_response = requests.delete(f"{url}/{post_id}", headers=headers())
    assert delete_response.status_code == 200

    get_response = requests.get(url, headers=headers())
    assert get_response.status_code == 200

    get_response_xml = parse_xml_response(get_response.content)
    todos = get_response_xml.findall("todo")

    #Assert only one todo remains
    assert len(todos) == 1

def test_todos_endpoint_DELETE_return_code_xml(save_system_state, setup_todos):
     #An unsupported endpoint
     response = requests.delete(url, headers=headers())
     assert response.status_code == 405

def test_todos_endpoint_PUT_return_code_xml(save_system_state, setup_todos):
     #An unsupported endpoint
     response = requests.put(url, json=todo_1(), headers=headers())
     assert response.status_code == 405

def test_todos_endpoint_POST_malformed_xml(save_system_state, setup_todos):
    #Deliberately malformed XML
    malformed_xml = """
    <todo>
        <title>Test Task</title>
        <doneStatus>false</doneStatus>
        <description>Malformed XML
    </todo>
    """
    response = requests.post(url, data=malformed_xml, headers=headers())
    
    #Assert that the malformed xml error is caught
    assert response.status_code == 400