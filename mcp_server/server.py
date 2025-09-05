import os
from mcp.server.fastmcp import FastMCP
from .ensemble_client import EnsembleDirector

mcp = FastMCP("ensemble-director-mcp")

async def ED():
    return EnsembleDirector(
        base_url=os.environ["ED_BASE_URL"],
        username=os.environ["ED_USERNAME"],
        password=os.environ["ED_PASSWORD"],
    )

@mcp.tool()
async def list_sites() -> dict:
    return await (await ED()).list_sites()

@mcp.tool()
async def list_devices(site_id: str | None = None, status: str | None = None) -> dict:
    return await (await ED()).list_devices(site_id=site_id, status=status)

@mcp.tool()
async def get_device(device_id: str) -> dict:
    return await (await ED()).get_device(device_id)

@mcp.tool()
async def get_alarms(site_id: str | None = None, device_id: str | None = None) -> dict:
    return await (await ED()).get_alarms(site_id=site_id, device_id=device_id)

@mcp.tool()
async def deploy_vnf(device_id: str, vnf_package_id: str, config: dict = {}) -> dict:
    # Consider adding confirmation/dry-run here in production.
    return await (await ED()).deploy_vnf(device_id, vnf_package_id, config)

if __name__ == "__main__":
    mcp.run(transport="stdio")

