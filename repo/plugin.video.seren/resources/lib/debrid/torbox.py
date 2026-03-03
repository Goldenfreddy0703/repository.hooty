"""
TorBox debrid service integration for Seren.
API Documentation: https://api.torbox.app/docs
"""

import time
from functools import cached_property

import xbmc
import xbmcgui

from resources.lib.common import source_utils
from resources.lib.common import tools
from resources.lib.modules.globals import g

TB_TOKEN_KEY = "tb.token"
TB_USERNAME_KEY = "tb.username"
TB_STATUS_KEY = "tb.premiumstatus"


class TorBox:
    """TorBox API wrapper for Seren."""

    def __init__(self):
        self.base_url = "https://api.torbox.app/v1/api/"
        self.ip_url = "https://api.ipify.org"
        self._load_settings()

    @cached_property
    def session(self):
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3 import Retry

        session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries, pool_maxsize=100))
        return session

    def _load_settings(self):
        self.token = g.get_setting(TB_TOKEN_KEY)

    def _get_headers(self, include_content_type=True):
        headers = {
            "User-Agent": f"Seren/{g.VERSION}",
        }
        if include_content_type:
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _get(self, url, params=None, fail_check=False):
        """Perform GET request to TorBox API."""
        full_url = self.base_url + url if not url.startswith("http") else url
        if not self.token:
            g.log("No TorBox Token Found", "warning")
            return None

        try:
            response = self.session.get(
                full_url, params=params, headers=self._get_headers(), timeout=20
            )
        except self.session.custom_errors if hasattr(self.session, 'custom_errors') else Exception as e:
            g.log(f"TorBox request error: {e}", "error")
            return None

        if not response.ok:
            g.log(f"TorBox API returned {response.status_code}: {response.text}", "error")
            return None

        try:
            result = response.json()
            # TorBox wraps data in success/data structure
            if isinstance(result, dict) and "data" in result and "success" in result:
                if "control" not in url:
                    return result["data"]
            return result
        except (ValueError, AttributeError):
            return response

    def _post(self, url, params=None, json_data=None, data=None, fail_check=False):
        """Perform POST request to TorBox API."""
        full_url = self.base_url + url if not url.startswith("http") else url
        if not self.token:
            g.log("No TorBox Token Found", "warning")
            return None

        # Don't include Content-Type for form data - let requests set it automatically
        include_content_type = json_data is not None and data is None
        
        try:
            response = self.session.post(
                full_url,
                params=params,
                json=json_data,
                data=data,
                headers=self._get_headers(include_content_type=include_content_type),
                timeout=20,
            )
        except Exception as e:
            g.log(f"TorBox request error: {e}", "error")
            return None

        if not response.ok:
            g.log(f"TorBox API returned {response.status_code}: {response.text}", "error")
            return None

        try:
            result = response.json()
            if isinstance(result, dict) and "data" in result and "success" in result:
                if "control" not in url:
                    return result["data"]
            return result
        except (ValueError, AttributeError):
            return response

    # =========================================================================
    # Authentication
    # =========================================================================

    def auth(self):
        """
        Authenticate with TorBox using API token.
        TorBox uses API keys from the web dashboard, not OAuth.
        """
        try:
            token = xbmcgui.Dialog().input(
                f"{g.ADDON_NAME}: TorBox API Key",
                type=xbmcgui.INPUT_ALPHANUM,
            )
            if not token:
                return

            # Test the token
            self.token = token
            account_info = self.account_info()

            if not account_info:
                xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30065))
                self.token = None
                return

            # Save settings
            g.set_setting(TB_TOKEN_KEY, token)
            self._save_user_status()
            xbmcgui.Dialog().ok(g.ADDON_NAME, f"TorBox {g.get_language_string(30020)}")
            g.log("Authorised TorBox successfully", "info")

        except Exception as e:
            g.log(f"TorBox auth error: {e}", "error")
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30065))

    def _save_user_status(self):
        """Save user account status to settings."""
        account_info = self.account_info()
        if account_info:
            username = account_info.get("email", "Unknown")
            is_premium = account_info.get("plan", 0) > 0
            status = "Premium" if is_premium else "Free"
            g.set_setting(TB_USERNAME_KEY, username)
            g.set_setting(TB_STATUS_KEY, status)

    # =========================================================================
    # Account Info
    # =========================================================================

    def account_info(self):
        """Get TorBox account information."""
        return self._get("user/me")

    def get_account_status(self):
        """Get account status (premium/free)."""
        account_info = self.account_info()
        if account_info:
            return "premium" if account_info.get("plan", 0) > 0 else "free"
        return "unknown"

    def days_remaining(self):
        """Get days remaining on premium subscription."""
        import datetime

        try:
            account_info = self.account_info()
            if not account_info:
                return None
            expires_at = account_info.get("premium_expires_at")
            if not expires_at:
                return None
            # Parse ISO format datetime
            expires = datetime.datetime.strptime(expires_at, "%Y-%m-%dT%H:%M:%SZ")
            days = (expires - datetime.datetime.utcnow()).days
            return max(days, 0)
        except Exception as e:
            g.log(f"Error getting TorBox days remaining: {e}", "error")
            return None

    # =========================================================================
    # Torrent Operations
    # =========================================================================

    def check_hash(self, hash_list):
        """
        Check if hashes are cached on TorBox.
        :param hash_list: List of info hashes to check
        :return: Dict of cached hashes with file info
        """
        if not hash_list:
            return {}

        json_data = {"hashes": hash_list}
        result = self._post("torrents/checkcached", params={"format": "list"}, json_data=json_data)

        if not result:
            return {}

        # Return list of cached hashes
        return [item["hash"] for item in result] if isinstance(result, list) else []

    def add_magnet(self, magnet):
        """Add a magnet link to TorBox."""
        data = {"magnet": magnet, "seed": 3, "allow_zip": "false"}
        result = self._post("torrents/createtorrent", data=data)
        return result

    def torrent_info(self, torrent_id):
        """Get info about a specific torrent."""
        return self._get(f"torrents/mylist", params={"id": torrent_id})

    def get_torrent_files(self, hash_value=None, magnet=None):
        """
        Create torrent from magnet and get file info similar to RD's check_hash for resolving.
        :param hash_value: Info hash of the torrent (optional, used if magnet not provided)
        :param magnet: Full magnet link (preferred)
        :return: Dict with torrent_id and files
        """
        import time
        
        if not magnet and hash_value:
            magnet = f"magnet:?xt=urn:btih:{hash_value}"
        
        if not magnet:
            g.log("TorBox: No magnet or hash provided", "error")
            return {}
            
        g.log(f"TorBox: Adding magnet: {magnet[:80]}...", "debug")
        
        response = self.add_magnet(magnet)
        g.log(f"TorBox add_magnet response: {response}", "debug")

        if not response:
            g.log("TorBox: add_magnet returned None", "error")
            return {}
            
        # TorBox might return torrent_id or id depending on if torrent already exists
        torrent_id = response.get("torrent_id") or response.get("id")
        
        if not torrent_id:
            g.log(f"TorBox: No torrent_id in response: {response}", "error")
            return {}

        g.log(f"TorBox: Got torrent_id {torrent_id}", "debug")
        
        # Wait for TorBox to process and get file list
        max_attempts = 15
        torrent_info = None
        
        for attempt in range(max_attempts):
            torrent_info = self.torrent_info(torrent_id)
            g.log(f"TorBox torrent_info attempt {attempt + 1}: {type(torrent_info)}", "debug")
            
            if torrent_info:
                files = torrent_info.get("files", [])
                download_finished = torrent_info.get("download_finished", False)
                
                g.log(f"TorBox: files={len(files)}, download_finished={download_finished}", "debug")
                
                if files and download_finished:
                    break
                    
            time.sleep(0.5)
        
        if not torrent_info:
            g.log("TorBox: Failed to get torrent info after all attempts", "error")
            return {}

        files = torrent_info.get("files", [])
        
        if not files:
            g.log("TorBox: No files in torrent_info", "warning")
            return {}
        
        # Filter out sample files and non-video files
        filtered_files = [
            f for f in files
            if "sample" not in f.get("name", "").lower()
            and "sample" not in f.get("short_name", "").lower()
            and source_utils.is_file_ext_valid(f.get("name", "") or f.get("short_name", ""))
        ]
        
        g.log(f"TorBox: Filtered to {len(filtered_files)} valid video files", "debug")

        return {
            "torrent_id": torrent_id,
            "torrent_info": torrent_info,
            "files": filtered_files,
        }

    def list_torrents(self):
        """List all torrents in user's account."""
        result = self._get("torrents/mylist")
        if result:
            g.log(f"TorBox list_torrents raw: {len(result)} items", "debug")
            if result and len(result) > 0:
                g.log(f"TorBox torrent sample keys: {list(result[0].keys()) if result else []}", "debug")
            # TorBox uses download_state for status - check for "completed" or "cached" 
            filtered = [
                i for i in result 
                if i.get("download_state") in ("completed", "cached", "seeding") or i.get("download_finished")
            ]
            # Also ensure they have files
            filtered = [i for i in filtered if i.get("files")]
            g.log(f"TorBox list_torrents filtered: {len(filtered)} items with files", "debug")
            return filtered
        return []

    def delete_torrent(self, torrent_id):
        """Delete a torrent from account."""
        data = {"torrent_id": torrent_id, "operation": "delete"}
        result = self._post("torrents/controltorrent", json_data=data)
        return result is not None and result.get("success", False)

    def torrent_select_all(self, torrent_id):
        """Select all files in a torrent (TorBox auto-selects, so this is a no-op)."""
        # TorBox automatically includes all files
        return True

    # =========================================================================
    # File Resolution
    # =========================================================================

    def resolve_torrent_file(self, torrent_id, file_id):
        """
        Resolve a torrent file to a direct download link.
        :param torrent_id: TorBox torrent ID
        :param file_id: TorBox file ID within the torrent
        :return: Direct download URL
        """
        try:
            g.log(f"TorBox resolve_torrent_file: torrent_id={torrent_id}, file_id={file_id}", "debug")
            
            # Get user's IP for CDN optimization
            try:
                user_ip = self.session.get(self.ip_url, timeout=2).text
            except Exception:
                user_ip = ""

            params = {
                "token": self.token,
                "torrent_id": torrent_id,
                "file_id": file_id,
            }
            if user_ip:
                params["user_ip"] = user_ip

            result = self._get("torrents/requestdl", params=params)
            g.log(f"TorBox resolve_torrent_file result: {type(result)} - {result[:100] if isinstance(result, str) and len(result) > 100 else result}", "debug")
            return result
        except Exception as e:
            g.log(f"TorBox resolve error: {e}", "error")
            return None

    def resolve_hoster(self, link):
        """
        Resolve a hoster URL to a direct download link using web downloads.
        :param link: URL of the hoster file
        :return: Direct download URL
        """
        try:
            # First, check if link is cached
            cached = self.check_webdl_cache([link])
            
            if cached:
                # Link is cached, create web download and get direct link
                webdl = self.create_webdl(link)
                if webdl and "webdownload_id" in webdl:
                    return self.resolve_webdl(webdl["webdownload_id"], webdl.get("file_id", 0))
            else:
                # Not cached, but still try to add and resolve
                webdl = self.create_webdl(link)
                if webdl and "webdownload_id" in webdl:
                    # Wait for processing
                    import time
                    for _ in range(20):
                        info = self.webdl_info(webdl["webdownload_id"])
                        if info and info.get("download_finished"):
                            return self.resolve_webdl(webdl["webdownload_id"], info.get("files", [{}])[0].get("id", 0))
                        time.sleep(0.5)
            return None
        except Exception as e:
            g.log(f"TorBox resolve hoster error: {e}", "error")
            return None

    # =========================================================================
    # Web Downloads (Hosters/Debrid)
    # =========================================================================

    def check_webdl_cache(self, links):
        """Check if hoster links are cached."""
        if not links:
            return []
        result = self._get("webdl/checkcached", params={"hash": ",".join(links), "format": "list"})
        return result if result else []

    def create_webdl(self, link):
        """Create a web download from a hoster link."""
        data = {"link": link}
        return self._post("webdl/createwebdownload", data=data)

    def webdl_info(self, webdl_id):
        """Get info about a web download."""
        return self._get("webdl/mylist", params={"id": webdl_id})

    def resolve_webdl(self, webdl_id, file_id):
        """Resolve web download file to direct link."""
        try:
            try:
                user_ip = self.session.get(self.ip_url, timeout=2).text
            except Exception:
                user_ip = ""

            params = {
                "token": self.token,
                "web_id": webdl_id,
                "file_id": file_id,
            }
            if user_ip:
                params["user_ip"] = user_ip

            return self._get("webdl/requestdl", params=params)
        except Exception as e:
            g.log(f"TorBox webdl resolve error: {e}", "error")
            return None

    def get_relevant_hosters(self):
        """Get list of supported hosters from TorBox."""
        # TorBox supports many hosters through their web download system
        # Common hosters that work with debrid services
        return [
            "1fichier.com", "4shared.com", "uploaded.net", "mega.nz",
            "rapidgator.net", "filefactory.com", "nitroflare.com",
            "turbobit.net", "mediafire.com", "uploading.com",
            "uploadgig.com", "katfile.com", "drop.download",
        ]

    # =========================================================================
    # Usenet Operations (for future support)
    # =========================================================================

    def list_usenet(self):
        """List usenet downloads."""
        result = self._get("usenet/mylist")
        if result:
            g.log(f"TorBox list_usenet raw: {len(result)} items", "debug")
            # TorBox uses download_state - check for completed states
            filtered = [
                i for i in result 
                if i.get("download_state") in ("completed", "cached") or i.get("download_finished")
            ]
            filtered = [i for i in filtered if i.get("files")]
            g.log(f"TorBox list_usenet filtered: {len(filtered)} items with files", "debug")
            return filtered
        return []

    def usenet_info(self, usenet_id):
        """Get info about a specific usenet download."""
        return self._get("usenet/mylist", params={"id": usenet_id})

    def delete_usenet(self, usenet_id):
        """Delete a usenet download."""
        data = {"usenet_id": usenet_id, "operation": "delete"}
        result = self._post("usenet/controlusenetdownload", json_data=data)
        return result is not None and result.get("success", False)

    def resolve_usenet(self, file_id):
        """Resolve usenet file to download link."""
        try:
            try:
                user_ip = self.session.get(self.ip_url, timeout=2).text
            except Exception:
                user_ip = ""

            usenet_id, file_id_num = file_id.split(",")
            params = {
                "token": self.token,
                "usenet_id": usenet_id,
                "file_id": file_id_num,
            }
            if user_ip:
                params["user_ip"] = user_ip

            return self._get("usenet/requestdl", params=params)
        except Exception as e:
            g.log(f"TorBox usenet resolve error: {e}", "error")
            return None

    # =========================================================================
    # Web Downloads (for future support)
    # =========================================================================

    def list_webdl(self):
        """List web downloads."""
        result = self._get("webdl/mylist")
        if result:
            g.log(f"TorBox list_webdl raw: {len(result)} items", "debug")
            # TorBox uses download_state - check for completed states
            filtered = [
                i for i in result 
                if i.get("download_state") in ("completed", "cached") or i.get("download_finished")
            ]
            filtered = [i for i in filtered if i.get("files")]
            g.log(f"TorBox list_webdl filtered: {len(filtered)} items with files", "debug")
            return filtered
        return []

    def delete_webdl(self, webdl_id):
        """Delete a web download."""
        data = {"webdl_id": webdl_id, "operation": "delete"}
        result = self._post("webdl/controlwebdownload", json_data=data)
        return result is not None and result.get("success", False)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    @staticmethod
    def is_service_enabled():
        """Check if TorBox is enabled and configured."""
        return (
            g.get_bool_setting("torbox.enabled")
            and g.get_setting(TB_TOKEN_KEY) is not None
            and g.get_setting(TB_TOKEN_KEY) != ""
        )

    def get_hosters(self, hosters):
        """
        Get supported hosters for TorBox web downloads.
        """
        host_list = self.get_relevant_hosters()
        hosters["premium"]["torbox"] = [(i, i.split(".")[0]) for i in host_list]

    @staticmethod
    def is_streamable_storage_type(storage_variant):
        """Check if storage variant contains streamable files."""
        return (
            len(
                [
                    i
                    for i in storage_variant.values()
                    if not source_utils.is_file_ext_valid(i["filename"])
                ]
            )
            <= 0
        )
