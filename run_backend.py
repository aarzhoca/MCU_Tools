import subprocess, sys, os
os.chdir(r"C:\LocalHome\Local_Rep\Cross_Ref_Dashboard\backend")
sys.path.insert(0, r"C:\LocalHome\Local_Rep\Cross_Ref_Dashboard\backend")
import uvicorn
uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
