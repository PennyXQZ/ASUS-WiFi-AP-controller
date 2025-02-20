import subprocess
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# =======================
# Commands Mapping
# =======================

CONDA_ENV = "/home/ubuntu/miniconda3/envs/asusenv/bin/python"
CONTROLLER_SCRIPT = "/home/ubuntu/asuscontroller/controller.py"

COMMAND_MAP = {
    "restart": [CONDA_ENV, CONTROLLER_SCRIPT, "--command", "reboot"],
    "power10": [CONDA_ENV, CONTROLLER_SCRIPT, "--command", "nvram_set", "--nvram_param", "wl1_txpower", "--nvram_value", "10"],
    "power50": [CONDA_ENV, CONTROLLER_SCRIPT, "--command", "nvram_set", "--nvram_param", "wl1_txpower", "--nvram_value", "50"],
    "power100": [CONDA_ENV, CONTROLLER_SCRIPT, "--command", "nvram_set", "--nvram_param", "wl1_txpower", "--nvram_value", "100"],
    "ledon": [CONDA_ENV, CONTROLLER_SCRIPT, "--command", "turn_led", "--state", "on"],
    "ledoff": [CONDA_ENV, CONTROLLER_SCRIPT, "--command", "turn_led", "--state", "off"],
    "query_data": [CONDA_ENV, CONTROLLER_SCRIPT, "--command", "query_data", "--data_type", "NETWORK"], # only for text purpose
}

# =======================
# Request Model
# =======================

class CommandRequest(BaseModel):
    command: str  # Must be one of: restart, power10, power50, power100, ledon, ledoff

# =======================
# API Endpoint
# =======================

@app.post("/api/control/set-command/WiFi")
def run_command(request: CommandRequest):
    """Execute predefined commands inside Conda environment."""
    command_key = request.command.lower()

    if command_key not in COMMAND_MAP:
        raise HTTPException(status_code=400, detail="Invalid command")

    try:
        # Get the command to execute
        command = COMMAND_MAP[command_key]

        # Execute the command in the Conda environment
        result = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
        )

        if result.returncode == 0:
            return {"status": "success", "command": command_key, "output": result.stdout.strip()}
        else:
            return {"status": "error", "command": command_key, "message": result.stderr.strip()}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =======================
# Running the FastAPI Server
# =======================

# Fix for Python 3.6 (No asyncio.run)
if __name__ == "__main__":
    import uvicorn
    import asyncio

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(uvicorn.run(app, host="10.150.8.14", port=8000))
    except KeyboardInterrupt:
        print("Shutting down gracefully...")
    finally:
        loop.close()


# =======================
# Example for how to Use the API
# =======================
# 1.Restart Router
# curl -X POST "http://10.150.8.14:8000/api/control/set-command" -H "Content-Type: application/json" -d '{"command": "restart"}'
# 2.Set Power to 10%
# curl -X POST "http://10.150.8.14:8000/api/control/set-command" -H "Content-Type: application/json" -d '{"command": "power10"}'
