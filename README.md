
# Omada Client Monitor

The Omada interface doesn't allow for quick access to connected clients. This is annoying when trying to determine the IP of a newly connected IoT device. 

This desktop application refreses clients connected to an Omada Controller. It provides a graphical interface to view client details such as IP address, status, network name, and traffic statistics. Simply login with your controller creds, and all connected clients will be shown.

This UI shamelessly piggybacks off Gregory Haberek's fantastic https://github.com/ghaberek/omada-api


![Omada Controller](controller.png)


## Setup

### Prerequisites

Ensure you have the following installed:
- Python 3.6 or higher
- pip (Python package installer)

### Install Dependencies

1. Install the required Python packages:
    ```sh
    pip install -r requirements.txt
    ```

### Configuration

1. `cp config.json.example config.json`
2. Fill out the following in `config.json`:
    ```json
    {
        "base_url": "http://<domain_or_ip>",
        "site": "Default",
        "omada_controller_id": "<controller_id>"
    }
    ```

Note that the controller ID can be found at http://<omada_url>/api/info as `omadacId`

### Running the Application

1. Run the application using the following command:
    ```sh
    python omada_monitor.py
    ```

2. The application will attempt to auto-login using saved credentials. If no credentials are saved or auto-login fails, a login dialog will appear.

### Saving Credentials

Creds are saved locally using Fernet encryption under ~/.omada-monitor Preferably, we'd store this in the Mac's keyring. Until then, you might want to use a read-only Omada controller user. To save your creds:

1. Enter your Omada Controller username and password in the login dialog.
2. Click the "Save Credentials" button to securely save your credentials for future use in ~/.omada-monitor/credentials.enc

## Building (macos only)

I've opted to build this and pin it to my dock, so that I can locate newly connected clients with one click.

Create a Development macos App bundle which displays the process terminal along with the UI.

```
python setup.py py2app
```

Create a Production macos App bundle (you may need to remove dist, build, and .eggs first).

```
python setup.py py2app -A
```