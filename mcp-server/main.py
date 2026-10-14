import hashlib

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

EMAIL = "24ds3000035@ds.study.iitm.ac.in".strip().lower()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)

TOOL = {
    "name": "solve_challenge",
    "description": "Returns first 16 hex chars of SHA-256(challenge:email), challenge read from X-Exam-Challenge header.",
    "inputSchema": {"type": "object", "properties": {}, "required": []},
}


def solve(challenge: str) -> str:
    return hashlib.sha256(f"{challenge}:{EMAIL}".encode()).hexdigest()[:16]


def ok(msg_id, result):
    return JSONResponse({"jsonrpc": "2.0", "id": msg_id, "result": result})


def err(msg_id, code, message):
    return JSONResponse({"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}})


@app.post("/mcp")
@app.post("/")
async def mcp(request: Request):
    body = await request.json()
    method = body.get("method")
    msg_id = body.get("id")

    # Notifications (no id) get 202 with an empty body
    if msg_id is None:
        return Response(status_code=202)

    if method == "initialize":
        client_version = body.get("params", {}).get("protocolVersion", "2025-06-18")
        return ok(msg_id, {
            "protocolVersion": client_version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "exam-mcp-server", "version": "1.0.0"},
        })

    if method == "ping":
        return ok(msg_id, {})

    if method == "tools/list":
        return ok(msg_id, {"tools": [TOOL]})

    if method == "tools/call":
        name = body.get("params", {}).get("name")
        if name != "solve_challenge":
            return err(msg_id, -32602, f"Unknown tool: {name}")
        challenge = request.headers.get("x-exam-challenge", "").strip()
        if not challenge:
            return ok(msg_id, {
                "content": [{"type": "text", "text": "Missing X-Exam-Challenge header"}],
                "isError": True,
            })
        return ok(msg_id, {"content": [{"type": "text", "text": solve(challenge)}]})

    return err(msg_id, -32601, f"Method not found: {method}")


# MCP clients may try to open an SSE stream with GET; 405 tells them we don't offer one
@app.get("/mcp")
async def mcp_get():
    return Response(status_code=405)


@app.get("/health")
async def health():
    return {"status": "ok"}