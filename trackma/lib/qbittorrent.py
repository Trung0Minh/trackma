import requests
import time
from trackma import utils

class QBitClient:
    """
    Handles communication with qBittorrent WebAPI.
    """
    def __init__(self, host="localhost", port=8080, username="admin", password="", messenger=None):
        self.base_url = f"http://{host}:{port}/api/v2"
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.msg = messenger

    def login(self, auto_launch=True):
        """Log in to qBittorrent."""
        url = f"{self.base_url}/auth/login"
        data = {
            'username': self.username,
            'password': self.password
        }
        
        retries = 3 if auto_launch else 1
        for attempt in range(retries):
            try:
                response = self.session.post(url, data=data, timeout=2)
                if response.status_code == 200 and response.text == "Ok.":
                    if self.msg:
                        self.msg.debug("qBittorrent: Login successful")
                    return True
                else:
                    if self.msg:
                        self.msg.warn(f"qBittorrent: Login failed - {response.text}")
                    return False
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if auto_launch and attempt == 0:
                    if self.msg:
                        self.msg.info("qBittorrent not responding. Attempting to launch...")
                    try:
                        utils.spawn_process(["qbittorrent"])
                        # Wait for it to start up
                        time.sleep(5)
                        continue
                    except Exception as launch_err:
                        if self.msg:
                            self.msg.warn(f"Failed to launch qBittorrent: {launch_err}")
                        return False
                
                if self.msg:
                    self.msg.warn(f"qBittorrent: Connection error - {e}")
                return False
            except Exception as e:
                if self.msg:
                    self.msg.warn(f"qBittorrent: Unexpected error during login - {e}")
                return False
        return False

    def add_magnet(self, magnet_link, save_path=None):
        """Add a magnet link to qBittorrent."""
        url = f"{self.base_url}/torrents/add"
        data = {
            'urls': magnet_link,
        }
        if save_path:
            data['savepath'] = save_path

        try:
            response = self.session.post(url, data=data)
            if response.status_code == 200:
                if self.msg:
                    self.msg.info("qBittorrent: Magnet link added successfully")
                return True
            else:
                if self.msg:
                    self.msg.warn(f"qBittorrent: Failed to add magnet - {response.text}")
                return False
        except Exception as e:
            if self.msg:
                self.msg.warn(f"qBittorrent: Connection error - {e}")
            return False
