# Who can generate images — the settings, screen by screen

Open WebUI 0.11.3, administrator account. The order matters: turn the default permission off
**before** creating the group (a new group starts from the default permissions).

## 1. Default permissions (lock 1, for everyone)

**Admin Panel › Users › Groups › Default permissions › Edit**

| Section | Setting | Value |
|---|---|---|
| Features permissions | Image Generation | **off** |

Save. Permissions **add up**: a user gets a feature if the default permissions *or any* of
their groups grant it (`has_permission`, `open_webui/utils/access_control`). A group can grant a
right, never take it away: as long as the default grants image generation, no group restricts
anything.

## 2. The group (lock 1, for the group)

**Admin Panel › Users › Groups › New group**

| Tab | Setting | Value |
|---|---|---|
| General | Name | `Communication` |
| General | Description | `Organization visuals` |
| Permissions | Features permissions › Image Generation | **on** |

Save, then open the group again: **Users** tab, tick the members. Each tick is saved at once
(`POST /api/v1/groups/id/<id>/users/add`): there is no Save button in that tab.

Effect: members see the **Image** switch in the chat (Integrations menu) and may call the
built-in `generate_image` tool; the others do not see it. The permission is read on page load:
a user who is already logged in reloads the page.

## 3. Model and tool access (lock 2)

**Workspace › Models › Image workshop › Access**: *Private*, **Add access** › group
`Communication` (Read). **Save & Update**.

**Workspace › Tools › Image workshop › Access**: same setting. Open WebUI then removes the tool
from the chats of users without access, even when it is attached to a public model
(`get_tools`, `open_webui/utils/tools.py`: "Access denied to tool … for user …" in the log).

In the video the tool is **left public on purpose**, attached to a general assistant open to
everyone (`RESTRICT_TOOL=false` in `setup_permissions.py`), to show the third lock at work.

## 4. The check inside the tool (lock 3)

Open WebUI's public route `POST /api/v1/images/generations` checks the permission and answers
403. The internal function `image_generations()`, which tools call, checks nothing: it trusts
its caller. `open-webui/image_workshop.py` therefore runs the same check as the public route
(`_allowed`): image generation enabled on the Images page, administrator, or
`has_permission(user.id, "features.image_generation", config.USER_PERMISSIONS)`. When refused,
it does not raise an error: it returns a clear sentence that the model passes on to the user,
and ComfyUI computes nothing.

The tool does not know the group's name: it only asks whether the permission is granted. Add
someone to the group, they are allowed at once; remove them, they are refused on their next
request.

## Who does what

| | Answers |
|---|---|
| Groups | who |
| Permission "Image Generation" | the right to generate |
| Model and tool access | with which model, which tool |
| The tool's code | the last lock, whatever happens |
