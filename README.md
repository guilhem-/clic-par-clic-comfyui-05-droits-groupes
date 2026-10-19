# Who can generate images? — groups and permissions for Open WebUI and ComfyUI

Demo code for module 5 of the "Click by Click" series **Image generation in Open WebUI with
ComfyUI**. One graphics card, the whole organization in Open WebUI: image generation is reserved
for one group of users with **three locks**, and the last one holds even when the configuration
is not perfect.

Video: {{video}}

## Goal

1. **The "Image Generation" permission**, turned off in the default permissions and granted to
   a `Communication` group. Permissions add up: a group can grant a right, never take it away.
2. **Access to the model and to the tool** "Image workshop", reserved for the group. Open WebUI
   0.11 removes a tool from the chats of users without access, even when a public model carries it.
3. **A check inside the tool's code.** Open WebUI's public route `POST /api/v1/images/generations`
   checks the permission (403 otherwise), but the internal function `image_generations()` that
   tools call checks nothing. The tool runs the same check, and returns a clear refusal to the
   model instead of raising an error: nothing reaches ComfyUI.

In the video, Lukas (in the group) gets his image; Oliver (outside the group) has no Image
switch and no "Image workshop" model, and when he asks a general assistant that carries the
tool (left public on purpose), the tool is called and refuses.

| File | Content |
|---|---|
| `open-webui/image_workshop.py` | The "Image workshop" tool of module 4 with its permission check (`_allowed`), **English version** of the `atelier_images.py` shown in the French video (same structure, same blocks; `create_visual`, formats `poster`, `banner`, `square`, valve `max_variants`) |
| `open-webui/workshop-instructions.txt` | System prompt of the "Image workshop" model |
| `open-webui/permissions.md` | The settings, screen by screen, and why they are in this order |
| `setup_permissions.py` | The video's settings through Open WebUI's API: default permission, group and members, model and tool access; `--check`, `--undo`, `--install-workshop` |
| `test/check-permissions.sh` | The public route called by a member (200) and by a user outside the group (403) |

## Prerequisites

- The image server of modules 1 and 2: ComfyUI v0.41 on a GPU, connected to Open WebUI 0.11 on
  the Images page — [`clic-par-clic-comfyui-01-brancher`](https://github.com/guilhem-/clic-par-clic-comfyui-01-brancher),
  [`clic-par-clic-comfyui-02-workflow-organisation`](https://github.com/guilhem-/clic-par-clic-comfyui-02-workflow-organisation).
- The "Image workshop" tool and model of module 4 —
  [`clic-par-clic-comfyui-04-outil-formats`](https://github.com/guilhem-/clic-par-clic-comfyui-04-outil-formats)
  (ids `image_workshop`, `image-workshop`, installed by its `setup_workshop.py`), or the same tool
  and model installed by `python setup_permissions.py --install-workshop`.
- An Open WebUI **administrator** account, and a few user accounts (role "user"; administrators
  bypass permissions and access control).
- Python 3.10+ (standard library only); `curl` and `bash` for the test.

## Step by step

### 1. By hand, as in the video

Follow [`open-webui/permissions.md`](open-webui/permissions.md):

1. **Admin Panel › Users › Groups › Default permissions**: Image Generation **off**, Save.
2. **New group** `Communication`, Permissions tab: Image Generation **on**, Save; open the group,
   **Users** tab: tick the members.
3. **Workspace › Models › Image workshop › Access**: Private, Add access › Communication, Save & Update.
   Do the same for the tool (the video leaves it public to test the third lock).

### 2. Through the API

```bash
cp .env.example .env            # OWUI_URL, OWUI_TOKEN (administrator), GROUP_MEMBERS, MODEL_ID, TOOL_ID
python setup_permissions.py --install-workshop   # optional: English tool and model, public
python setup_permissions.py                      # default permission off, group, members, access
python setup_permissions.py --check              # what is in place
python setup_permissions.py --undo               # back to the saved default permissions, group deleted, model and tool public
```

The default permissions are saved to `default-permissions.backup.json` before the first change;
`--undo` restores them exactly.

## Try it

1. With a member's account (reload the page): the **Image workshop** model is in the list;
   "A square thumbnail for the company running club." gives an image.
2. With an account outside the group: no **Image** in the Integrations menu, no **Image
   workshop** model.
3. To see the third lock: set `RESTRICT_TOOL=false`, run `setup_permissions.py` again, create a
   public model carrying the tool (system prompt: "For an image request, call the create_visual
   tool directly, without asking questions."), and ask it for an image with the account outside
   the group. Unfold the tool call: its output is the refusal sentence, and ComfyUI's queue stays
   empty.
4. The public route, from the command line:

```bash
set -a; . ./.env; set +a
./test/check-permissions.sh      # Outside the group: HTTP 403 ... OK / Member of the group: HTTP 200 ... OK
```

## Good to know

- **Order of the settings**: a new group starts from the default permissions. Turn the default
  off first, otherwise the group's switch already looks on and nothing is restricted.
- **Model capabilities**: the general assistant used in the demo has Open WebUI's built-in tools
  turned off (capability `builtin_tools`), otherwise the model sometimes asks the user a question
  ("Ask User") instead of calling the tool.
- **Administrators** always pass: permissions and access control do not apply to them
  (`BYPASS_ADMIN_ACCESS_CONTROL`), and the tool lets them through as well.
- **Settings are global**: default permissions concern every user of the instance. Keep the
  backup, and restore it with `--undo`.

## Series

- Previous module: **A tool that picks the format** —
  [`clic-par-clic-comfyui-04-outil-formats`](https://github.com/guilhem-/clic-par-clic-comfyui-04-outil-formats).
- Next module: **What may be generated?** (the organization's content charter: Open WebUI filter,
  check inside the tool, gateway in front of ComfyUI) —
  [`clic-par-clic-comfyui-06-charte`](https://github.com/guilhem-/clic-par-clic-comfyui-06-charte).

## License

MIT (see `LICENSE`). ComfyUI: GPL-3.0; Z-Image Turbo: Apache 2.0; Open WebUI: its own license
(the Open WebUI code quoted in the video stays theirs and is not copied here).
