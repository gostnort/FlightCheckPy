import os
import socket
import subprocess
import sys
import time
from contextlib import closing

import pytest
import requests

# Add project root to path to allow imports from scripts and remote_db
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from remote_db.db_port_client import DbPortClient
from remote_db.remote_sqlite_adapter import RemoteSqliteConnection
from scripts.hbpr_info_processor import HbprDatabase
from scripts.command_processor import CommandProcessor


def find_free_port():
    """Finds a free port on localhost."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def db_server():
    """Fixture to start and stop the in-memory DB server."""
    host = "127.0.0.1"
    port = find_free_port()
    
    server_path = os.path.join(project_root, 'remote_db', 'memdb_port_server.py')
    
    # Start the server as a background process
    command = [sys.executable, server_path, "--host", host, "--port", str(port)]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for the server to be healthy
    health_url = f"http://{host}:{port}/health"
    retries = 10
    healthy = False
    while retries > 0:
        try:
            response = requests.get(health_url, timeout=1)
            if response.status_code == 200:
                healthy = True
                break
        except requests.ConnectionError:
            time.sleep(0.5)
            retries -= 1
    
    if not healthy:
        stdout, stderr = process.communicate()
        pytest.fail(
            f"Server failed to start on port {port}.\\n"
            f"STDOUT: {stdout.decode()}\\n"
            f"STDERR: {stderr.decode()}"
        )

    # Yield the host and port for the tests
    yield host, port
    
    # Teardown: stop the server
    process.terminate()
    process.wait(timeout=5)


def test_integration_with_real_database(db_server):
    """
    An integration test that loads a real database and runs checks
    using the refactored script processors.
    """
    host, port = db_server
    db_file = os.path.join('databases', 'CA984_25JUL25.db')

    assert os.path.exists(db_file), f"Database file not found at {db_file}"

    # 1. Connect client and load the database
    client = DbPortClient(host, port)
    load_success = client.load_database(os.path.abspath(db_file))
    assert load_success, "Failed to load database into server"

    # 2. Create the remote connection adapter and the main HbprDatabase processor
    remote_conn = RemoteSqliteConnection(client)
    db_processor = HbprDatabase(remote_conn)

    # 3. Test HbprDatabase processor's functions
    print("\\n--- Testing HbprDatabase Processor ---")
    
    # Check flight info
    flight_info = db_processor.get_flight_info()
    print(f"Flight Info: {flight_info}")
    assert flight_info is not None
    assert flight_info['flight_number'] == 'CA984'
    assert flight_info['flight_date'] == '25JUL25'

    # Check record summary
    summary = db_processor.get_record_summary()
    print(f"Record Summary: {summary}")
    assert summary['full_records'] > 100  # Expecting a reasonable number of records
    assert summary['total_records'] == summary['full_records'] + summary['simple_records']

    # Fetch a specific record that is likely to exist
    test_hbnb_number = 100
    record_content = db_processor.get_hbpr_record(test_hbnb_number)
    print(f"Content of HBNB {test_hbnb_number}: {record_content[:100]}...") # Print first 100 chars
    assert record_content is not None
    assert f'HBPR: CA984/25JUL25*LAX,{test_hbnb_number}' in record_content

    # 4. Test CommandProcessor
    print("\\n--- Testing CommandProcessor ---")
    cmd_processor = CommandProcessor(remote_conn)
    
    # Check that flight info is loaded correctly by the command processor as well
    assert cmd_processor.flight_info is not None
    assert cmd_processor.flight_info['flight_number'] == 'CA984'

    # Get all commands
    commands = cmd_processor.get_all_commands_data()
    print(f"Found {len(commands)} commands.")
    assert isinstance(commands, list)

    # If there are commands, check for a specific command type
    if commands:
        command_types = {cmd['command_type'] for cmd in commands}
        print(f"Command Types: {command_types}")
        assert 'SY' in command_types
        assert 'LNIATA' in command_types

    print("\\n--- Integration Test Passed! ---")
