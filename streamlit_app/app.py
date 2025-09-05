import os, json, asyncio, sys
import streamlit as st
from openai import OpenAI

# ---------- OpenAI ----------
#client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))
openai_api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=openai_api_key)

st.set_page_config(page_title="Ensemble Director Agent", page_icon="⚙️")
st.title("Ensemble Director Agent (MCP)")

# ---------- State ----------
for k, v in {
    "connected": False,
    "ed_url": "",
    "ed_username": "",
    "ed_password": "",
    "history": []
}.items():
    st.session_state.setdefault(k, v)

# ---------- Sidebar: Connect ----------
with st.sidebar:
    st.subheader("Connect to Ensemble Director")
    st.session_state.ed_url = st.text_input("ED Base URL", placeholder="https://director.example.com")
    st.session_state.ed_username = st.text_input("Username")
    st.session_state.ed_password = st.text_input("Password", type="password")

    def mcp_env():
        env = os.environ.copy()
        env["ED_BASE_URL"]  = st.session_state.ed_url.strip()
        env["ED_USERNAME"]  = st.session_state.ed_username.strip()
        env["ED_PASSWORD"]  = st.session_state.ed_password
        env["ED_AUTH_MODE"] = "BASIC"  # Director uses user/pass
        env["PYTHONPATH"]   = "."
        return env

    def mcp_call(tool_name: str, arguments: dict):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server.server"],
            env=mcp_env(),
        )
        async def _once():
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    res = await session.call_tool(tool_name, arguments=arguments)
                    return res.structuredContent or res.content
        return asyncio.run(_once())

    def connect():
        try:
            _ = mcp_call("list_sites", {})   # health probe
            st.session_state.connected = True
            st.success("Connected to Director!")
        except Exception as e:
            st.session_state.connected = False
            st.error(f"Connection failed: {e}")

    st.button("Connect", on_click=connect)

st.markdown("**Status:** " + ("🟢 Connected" if st.session_state.connected else "🔴 Not connected"))

# ---------- Chat ----------
for role, content in st.session_state.history:
    with st.chat_message(role):
        st.write(content)

prompt = st.chat_input("Ask about sites/devices/alarms…")
if prompt:
    if not st.session_state.connected:
        st.error("Please connect to Director first.")
        st.stop()

    st.session_state.history.append(("user", prompt))

    # Tool schema for the model (bridging to MCP)
    tools = [
        {"type": "function","function":{
            "name":"list_devices","description":"List devices",
            "parameters":{"type":"object","properties":{"site_id":{"type":["string","null"]},"status":{"type":["string","null"]}}, "required":[]}}},
        {"type": "function","function":{
            "name":"get_device","description":"Get device details",
            "parameters":{"type":"object","properties":{"device_id":{"type":"string"}},"required":["device_id"]}}},
        {"type": "function","function":{
            "name":"get_alarms","description": "Get active alarms for a specific Connector Access device (by UID).",
            "parameters":{"type":"object","properties":{"connector_uid": {"type": "string", "description": "ACC1UID (Connector UID)"},},"required": ["connector_uid"]},},},
        {"type": "function","function":{
            "name":"deploy_vnf","description":"Deploy a VNF (ask for confirmation first)",
            "parameters":{"type":"object","properties":{"device_id":{"type":"string"},"vnf_package_id":{"type":"string"},"config":{"type":"object","default":{}}},"required":["device_id","vnf_package_id"]}}}
    ]

    messages = [
        {"role": "system", "content":
         "You are an operations copilot for Ensemble Director. "
         "Use tools for any ED query/action; ask for confirmation before any change."},
        *[{"role": r, "content": c} for (r, c) in st.session_state.history],
        {"role":"user","content": prompt}
    ]

    with st.chat_message("assistant"):
        while True:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
            msg = resp.choices[0].message

            if msg.tool_calls:
                for call in msg.tool_calls:
                    name = call.function.name
                    args = json.loads(call.function.arguments or "{}")
                    try:
                        result = mcp_call(name, args)
                    except Exception as e:
                        result = {"error": str(e)}
                    messages.append({"role":"assistant","tool_calls":[call]})
                    messages.append({"role":"tool","tool_call_id": call.id, "content": json.dumps(result)})
                continue

            final = msg.content or ""
            st.session_state.history.append(("assistant", final))
            st.write(final)
            break

    st.rerun()

