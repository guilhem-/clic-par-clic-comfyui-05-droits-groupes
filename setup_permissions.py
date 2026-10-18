"""Reserve image generation in Open WebUI for one group of users, through its API.

Does what module 5 of the "Image generation in Open WebUI with ComfyUI" series does on screen:
  1. turns "Image Generation" off in the default permissions (a backup is kept first);
  2. creates (or updates) the group, grants it "Image Generation", adds its members;
  3. makes the "Image workshop" model private and shares it with the group (read);
  4. does the same for the tool, unless RESTRICT_TOOL=false (the video leaves it open on purpose,
     to show that the check inside the tool still refuses the image).
The third lock, the permission check inside the tool, is in open-webui/image_workshop.py.

Usage:
  python setup_permissions.py                     # apply the settings above
  python setup_permissions.py --install-workshop  # install the English tool and model (public), valve at 3
  python setup_permissions.py --check             # show default permission, group, model and tool access
  python setup_permissions.py --undo              # restore the default permissions, delete the group,
                                                  # open the model and the tool to everyone again

Settings: .env file (see .env.example); environment variables take precedence.
No dependency: Python 3.10 or newer, standard library only.
"""
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
BACKUP = HERE / "default-permissions.backup.json"
TOOL_CODE = HERE / "open-webui" / "image_workshop.py"
INSTRUCTIONS = HERE / "open-webui" / "workshop-instructions.txt"
VARIABLES = (
    "OWUI_URL", "OWUI_TOKEN", "GROUP_NAME", "GROUP_MEMBERS", "MODEL_ID", "TOOL_ID",
    "RESTRICT_TOOL", "BASE_MODEL",
)
PUBLIC = [{"principal_type": "user", "principal_id": "*", "permission": "read"}]


def settings() -> dict:
    """Defaults, then .env (key=value), then the environment, which wins."""
    s = {
        "OWUI_URL": "http://127.0.0.1:8080", "GROUP_NAME": "Communication",
        "MODEL_ID": "image-workshop", "TOOL_ID": "image_workshop", "RESTRICT_TOOL": "true",
    }
    env = HERE / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                s[key.strip()] = value.strip()
    for key in VARIABLES:
        if os.environ.get(key):
            s[key] = os.environ[key]
    return s


S = settings()


def api(method: str, path: str, body=None, tolerate=False):
    """Call Open WebUI's API with an administrator token."""
    if not S.get("OWUI_TOKEN"):
        sys.exit("OWUI_TOKEN missing (.env): token of an Open WebUI administrator account.")
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        S["OWUI_URL"].rstrip("/") + path, data=data, method=method,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {S['OWUI_TOKEN']}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            text = resp.read().decode()
    except urllib.error.HTTPError as e:
        if tolerate:
            return None
        sys.exit(f"{method} {path}: {e.code} {e.read().decode()[:300]}")
    return json.loads(text) if text.strip() else None


def with_image_generation(permissions: dict, value: bool) -> dict:
    return {**permissions, "features": {**permissions.get("features", {}), "image_generation": value}}


def find_group():
    return next((g for g in api("GET", "/api/v1/groups/") or [] if g["name"] == S["GROUP_NAME"]), None)


def share(kind: str, ident: str, grants: list) -> None:
    """Replace the access grants of a model or a tool (everything else unchanged)."""
    if kind == "model":
        model = api("GET", f"/api/v1/models/model?id={urllib.parse.quote(ident)}", tolerate=True)
        if not model:
            print(f"Model {ident} not found: skipped.")
            return
        api("POST", "/api/v1/models/model/update", {**model, "access_grants": grants})
    else:
        tool = api("GET", f"/api/v1/tools/id/{ident}", tolerate=True)
        if not tool:
            print(f"Tool {ident} not found: skipped.")
            return
        api("POST", f"/api/v1/tools/id/{ident}/update", {
            "id": tool["id"], "name": tool["name"], "content": tool["content"],
            "meta": tool.get("meta") or {"description": "", "manifest": {}}, "access_grants": grants,
        })
    print(f"{kind.capitalize()} {ident}: {'public' if grants == PUBLIC else 'reserved for ' + S['GROUP_NAME']}.")


def apply() -> None:
    # 1. Default permissions: keep a backup, then turn image generation off for everyone.
    defaults = api("GET", "/api/v1/users/default/permissions")
    if not BACKUP.exists():
        BACKUP.write_text(json.dumps(defaults, indent=2), encoding="utf-8")
        print(f"Default permissions saved to {BACKUP.name}.")
    api("POST", "/api/v1/users/default/permissions", with_image_generation(defaults, False))
    print("Default permissions: Image Generation off.")

    # 2. The group, with the permission. A new group starts from the default permissions.
    granted = with_image_generation(defaults, True)
    group = find_group()
    form = {"name": S["GROUP_NAME"], "description": "Organization visuals", "permissions": granted}
    if group:
        api("POST", f"/api/v1/groups/id/{group['id']}/update", form)
    else:
        group = api("POST", "/api/v1/groups/create", form)
    print(f"Group {S['GROUP_NAME']}: Image Generation on.")
    emails = [e.strip().lower() for e in S.get("GROUP_MEMBERS", "").split(",") if e.strip()]
    users = (api("GET", "/api/v1/users/all") or {}).get("users", [])
    ids = [u["id"] for u in users if u.get("email", "").lower() in emails]
    if len(ids) != len(emails):
        print(f"Warning: {len(emails) - len(ids)} member(s) not found among the users.")
    if ids:
        api("POST", f"/api/v1/groups/id/{group['id']}/users/add", {"user_ids": ids})
        print(f"Members added: {len(ids)}.")

    # 3. and 4. Access: the model, and the tool unless RESTRICT_TOOL=false.
    reserved = [{"principal_type": "group", "principal_id": group["id"], "permission": "read"}]
    share("model", S["MODEL_ID"], reserved)
    if S["RESTRICT_TOOL"].lower() not in ("0", "false", "no"):
        share("tool", S["TOOL_ID"], reserved)
    else:
        print(f"Tool {S['TOOL_ID']}: left open (RESTRICT_TOOL=false); the check inside the tool still applies.")


def install_workshop() -> None:
    if not S.get("BASE_MODEL"):
        sys.exit("BASE_MODEL missing (.env): id of a chat model able to call tools.")
    tool = {"id": S["TOOL_ID"], "name": "Image workshop", "content": TOOL_CODE.read_text(encoding="utf-8"),
            "meta": {"description": "", "manifest": {}}, "access_grants": PUBLIC}
    if api("GET", f"/api/v1/tools/id/{S['TOOL_ID']}", tolerate=True):
        api("POST", f"/api/v1/tools/id/{S['TOOL_ID']}/update", tool)
    else:
        api("POST", "/api/v1/tools/create", tool)
    api("POST", f"/api/v1/tools/id/{S['TOOL_ID']}/valves/update", {"max_variants": 3})
    model = {
        "id": S["MODEL_ID"], "name": "Image workshop", "base_model_id": S["BASE_MODEL"],
        "meta": {"profile_image_url": "/static/favicon.png", "description": "Visuals in the organization's formats",
                 "toolIds": [S["TOOL_ID"]]},
        "params": {"system": INSTRUCTIONS.read_text(encoding="utf-8").strip()},
        "access_grants": PUBLIC,
    }
    if api("GET", f"/api/v1/models/model?id={S['MODEL_ID']}", tolerate=True):
        api("POST", "/api/v1/models/model/update", model)
    else:
        api("POST", "/api/v1/models/create", model)
    print(f"Tool {S['TOOL_ID']} and model {S['MODEL_ID']} installed (public, max_variants = 3).")


def check() -> None:
    defaults = api("GET", "/api/v1/users/default/permissions")
    print("Default permissions, Image Generation:", defaults["features"].get("image_generation"))
    group = find_group()
    if group:
        full = api("GET", f"/api/v1/groups/id/{group['id']}")
        print(f"Group {group['name']}: {full.get('member_count')} member(s), Image Generation:",
              ((full.get("permissions") or {}).get("features") or {}).get("image_generation"))
    else:
        print(f"Group {S['GROUP_NAME']}: absent.")
    model = api("GET", f"/api/v1/models/model?id={urllib.parse.quote(S['MODEL_ID'])}", tolerate=True)
    tool = api("GET", f"/api/v1/tools/id/{S['TOOL_ID']}", tolerate=True)
    for name, item in (("Model", model), ("Tool", tool)):
        grants = (item or {}).get("access_grants") or []
        who = ", ".join("everyone" if g["principal_id"] == "*" else f"{g['principal_type']} {g['principal_id']}" for g in grants)
        print(f"{name} access:", who or ("absent" if item is None else "private"))


def undo() -> None:
    if BACKUP.exists():
        api("POST", "/api/v1/users/default/permissions", json.loads(BACKUP.read_text(encoding="utf-8")))
        BACKUP.unlink()
        print("Default permissions restored from the backup.")
    else:
        print("No backup: default permissions left as they are.")
    group = find_group()
    if group:
        api("DELETE", f"/api/v1/groups/id/{group['id']}/delete")
        print(f"Group {S['GROUP_NAME']} deleted.")
    share("model", S["MODEL_ID"], PUBLIC)
    share("tool", S["TOOL_ID"], PUBLIC)


if __name__ == "__main__":
    actions = {"--install-workshop": install_workshop, "--check": check, "--undo": undo}
    actions.get(sys.argv[1] if len(sys.argv) > 1 else "", apply)()
