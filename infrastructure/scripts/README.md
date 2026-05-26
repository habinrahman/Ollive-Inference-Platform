Local operational scripts can live here as the platform grows.

This prototype keeps schema creation in the API startup path for a single-command
demo. A production deployment would replace that with explicit migrations.

Useful commands:

```powershell
.\infrastructure\scripts\run_api.ps1 -Port 5500
.\infrastructure\scripts\run_frontend.ps1 -Port 3000
.\infrastructure\scripts\run_dashboard.ps1 -Port 3001
python infrastructure/scripts/check_db.py
python infrastructure/scripts/e2e_smoke.py --api-base-url http://127.0.0.1:5500 --stream
python infrastructure/scripts/e2e_smoke.py --api-base-url http://127.0.0.1:5500 --stream --provider openai
```

The `run_*.ps1` scripts start child processes inside a Windows job object. Closing the terminal or stopping the wrapper also stops the managed `python` or `node` process tree, which prevents stale servers from holding ports.
