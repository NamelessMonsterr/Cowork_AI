# Safety Configuration API Models
class TrustedAppsUpdate(BaseModel):
    trusted_apps: list[str]
    app_aliases: dict[str, str] = {}


class TrustedDomainsUpdate(BaseModel):
    trusted_domains: list[str]


# TASK 1: Safety Configuration API Endpoints


@app.get("/safety/trusted_apps")
async def get_trusted_apps():
    """Get current trusted apps configuration."""
    try:
        config_path = Path(__file__).parent / "config" / "trusted_apps.json"
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[Safety] Failed to load trusted apps: {e}")
        raise HTTPException(500, f"Failed to load configuration: {e}")


@app.post("/safety/trusted_apps")
async def update_trusted_apps(apps: TrustedAppsUpdate):
    """Update trusted apps configuration (requires active session)."""
    if not state.session_auth.check():
        raise HTTPException(403, "Forbidden: Active session required")

    try:
        config_path = Path(__file__).parent / "config" / "trusted_apps.json"
        data = {"trusted_apps": apps.trusted_apps, "app_aliases": apps.app_aliases}

        with open(config_path, "w") as f:
            json.dump(data, f, indent=2)

        # Reload PlanGuard config
        from assistant.safety.plan_guard import load_trusted_apps

        state.plan_guard.trusted_apps, state.plan_guard.app_aliases = (
            load_trusted_apps()
        )

        logger.info(f"[Safety] Trusted apps updated: {len(apps.trusted_apps)} apps")
        return {"status": "updated", "count": len(apps.trusted_apps)}

    except Exception as e:
        logger.error(f"[Safety] Failed to update trusted apps: {e}")
        raise HTTPException(500, f"Failed to update configuration: {e}")


@app.get("/safety/trusted_domains")
async def get_trusted_domains():
    """Get current trusted domains configuration."""
    try:
        config_path = Path(__file__).parent / "config" / "trusted_domains.json"
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[Safety] Failed to load trusted domains: {e}")
        raise HTTPException(500, f"Failed to load configuration: {e}")


@app.post("/safety/trusted_domains")
async def update_trusted_domains(domains: TrustedDomainsUpdate):
    """Update trusted domains configuration (requires active session)."""
    if not state.session_auth.check():
        raise HTTPException(403, "Forbidden: Active session required")

    try:
        config_path = Path(__file__).parent / "config" / "trusted_domains.json"
        data = {"trusted_domains": domains.trusted_domains}

        with open(config_path, "w") as f:
            json.dump(data, f, indent=2)

        # Reload PlanGuard config
        from assistant.safety.plan_guard import load_trusted_domains

        state.plan_guard.trusted_domains = load_trusted_domains()

        logger.info(
            f"[Safety] Trusted domains updated: {len(domains.trusted_domains)} domains"
        )
        return {"status": "updated", "count": len(domains.trusted_domains)}

    except Exception as e:
        logger.error(f"[Safety] Failed to update trusted domains: {e}")
        raise HTTPException(500, f"Failed to update configuration: {e}")


@app.get("/logs/recent")
async def get_recent_logs(limit: int = 50):
    """Get recent logs including safety violations."""
    try:
        logs = []

        # Get safety audit logs
        audit_path = Path("logs/safety_audit.jsonl")
        if audit_path.exists():
            with open(audit_path, "r") as f:
                for line in f.readlines()[-limit:]:
                    try:
                        entry = json.loads(line)
                        entry["type"] = "safety_violation"
                        logs.append(entry)
                    except:
                        pass

        # Get execution logs from state
        if hasattr(state, "execution_logs"):
            logs.extend(
                [{**log, "type": "execution"} for log in state.execution_logs[-limit:]]
            )

        # Sort by timestamp
        logs.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

        return {"logs": logs[:limit]}

    except Exception as e:
        logger.error(f"[Logs] Failed to load recent logs: {e}")
        return {"logs": [], "error": str(e)}
