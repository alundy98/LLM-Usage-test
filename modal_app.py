import shlex
import subprocess
from pathlib import Path
import os
import modal

# Paths
streamlit_script_local_path = Path(__file__).parent / "streamlit_run.py"
streamlit_script_remote_path = "/root/streamlit_run.py"

# Check if the Streamlit script exists
if not streamlit_script_local_path.exists():
    raise RuntimeError("streamlit_run.py not found in project folder")

# Define Modal image with dependencies and mount the local Streamlit script
image = (
    modal.Image.debian_slim(python_version="3.9")
    .uv_pip_install("streamlit", "supabase", "pandas", "plotly", "python-dotenv")
    .add_local_file(streamlit_script_local_path, streamlit_script_remote_path)
)

# Load Modal secrets
secret = modal.Secret.from_name("supabase-secrets")

# Define the Modal app
app = modal.App(name="usage-dashboard", image=image, secrets=[secret])

# Define the web server function
@app.function(allow_concurrent_inputs=100)
@modal.web_server(port=8000)
def run():
    # Quote the script path safely
    target = shlex.quote(streamlit_script_remote_path)

    # Build the Streamlit command
    cmd = f"streamlit run {target} --server.port 8000 --server.address 0.0.0.0 " \
        f"--server.headless true --server.enableCORS=false --server.enableXsrfProtection=false"

    # Environment variables
    env_vars = dict(os.environ)  # inherit all current environment variables

    # Include Supabase keys if set in environment
    if os.getenv("SUPABASE_URL"):
        env_vars["SUPABASE_URL"] = os.getenv("SUPABASE_URL")
    if os.getenv("SUPABASE_KEY"):
        env_vars["SUPABASE_KEY"] = os.getenv("SUPABASE_KEY")

    # Run Streamlit inside the container
    subprocess.Popen(cmd, shell=True, env=env_vars)
