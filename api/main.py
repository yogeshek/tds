# main.py
import os
import json
import re
import requests
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from io import StringIO
import sys
import traceback

# ----------------------------
# Load environment variables
# ----------------------------
load_dotenv()
AI_API_TOKEN = os.environ.get("AIPIPE_TOKEN")  # set in .env, never commit the value
CHAT_URL = os.environ.get("CHAT_URL", "https://aipipe.org/openrouter/v1/chat/completions")

# ----------------------------
# FastAPI setup
# ----------------------------
app = FastAPI(title="Code Interpreter with AI Error Analysis")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Request & Response Models
# ----------------------------
class CodeRequest(BaseModel):
    code: str

class CodeResponse(BaseModel):
    error: List[int]
    result: str

# ----------------------------
# Tool Function: Execute Python code
# ----------------------------
def execute_python_code(code: str) -> dict:
    """
    Execute Python code and return exact output or traceback.
    """
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    try:
        exec(code)
        output = sys.stdout.getvalue()
        return {"success": True, "output": output}

    except Exception:
        output = traceback.format_exc()
        return {"success": False, "output": output}

    finally:
        sys.stdout = old_stdout

# ----------------------------
# AI Error Analysis with Fallback
# ----------------------------
def analyze_error_with_ai(code: str, traceback_text: str) -> List[int]:
    """
    Use Gemini to identify error line numbers. Fallback to parsing traceback if AI fails.
    """
    prompt = f"""
Analyze this Python code and its traceback.
Return only **JSON**, no explanations.
Use this exact format:

{{
  "error_lines": [line_numbers]
}}

CODE:
{code}

TRACEBACK:
{traceback_text}
"""

    headers = {
        "Authorization": f"Bearer {AI_API_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gemini-2.0-flash-exp",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 200,
        "temperature": 0
    }

    error_lines = []

    try:
        response = requests.post(CHAT_URL, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        ai_text = data["choices"][0]["message"]["content"]

        # Try to parse AI JSON
        try:
            result = json.loads(ai_text)
            error_lines = result.get("error_lines", [])
        except json.JSONDecodeError:
            print("AI returned invalid JSON:", ai_text)
            error_lines = []

    except requests.exceptions.RequestException as e:
        print("AIPipe request failed:", e)
        error_lines = []

    # ----------------------------
    # Fallback: parse Python traceback
    # ----------------------------
    if not error_lines:
        # Extract all line numbers from traceback
        matches = re.findall(r'File "<string>", line (\d+)', traceback_text)
        if matches:
            error_lines = [int(matches[-1])]  # take only the last one
        else:
            error_lines = []

    return error_lines

# ----------------------------
# API Endpoint
# ----------------------------
@app.post("/code-interpreter", response_model=CodeResponse)
def code_interpreter(request: CodeRequest):
    execution = execute_python_code(request.code)

    if execution["success"]:
        return CodeResponse(error=[], result=execution["output"])
    else:
        error_lines = analyze_error_with_ai(request.code, execution["output"])
        return CodeResponse(error=error_lines, result=execution["output"])