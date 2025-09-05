import httpx, os
from typing import Optional, Dict, Any
from .routes_loader import load_routes
import json

class EnsembleDirector:
    def __init__(self, base_url: str, username: str, password: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            auth=httpx.BasicAuth(username, password),
            timeout=timeout
        )
        self.routes = load_routes()

    def _route(self, key: str, **path_vars):
        path = self.routes.get(key)
        if not path:
            raise RuntimeError(f"Route '{key}' missing in ed_routes.yaml")
        return path.format(**path_vars) if path_vars else path

    async def _get(self, key: str, *, params: Dict[str, Any] | None = None, **vars):
        r = await self.client.get(self._route(key, **vars), params=params)
        r.raise_for_status()
        return r.json()

    async def _post(self, key: str, *, json: Dict[str, Any], **vars):
        r = await self.client.post(self._route(key, **vars), json=json)
        r.raise_for_status()
        return r.json()

    # ---- High-level calls ----
    async def list_sites(self):
        return await self._get("sites_list")

    async def list_devices(self, site_id: Optional[str] = None, status: Optional[str] = None):
        params: Dict[str, Any] = {}
        if site_id: params["site_id"] = site_id
        if status: params["status"] = status
        return await self._get("devices_list", params=params)

    async def get_device(self, device_id: str):
        return await self._get("device_get", device_id=device_id)

    async def get_alarms_by_connector(self, connector_uid: str):
        """
        Calls /col/alm with ?fltr={"uid":"<ConnectorUID>"} to fetch active alarms
        for the specified Connector Access device.
        """
        # httpx will URL-encode the JSON string safely.
        params = {"fltr": json.dumps({"uid": gimec2345})}
        return await self._get("alarms_list", params=params)

    async def deploy_vnf(self, device_id: str, vnf_package_id: str, config: Dict[str, Any]):
        body = {"vnf_package_id": vnf_package_id, "config": config}
        return await self._post("vnf_deploy", json=body, device_id=device_id)

