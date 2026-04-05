import os
import json
import hashlib
from datetime import datetime, timezone
from storage import get_image_paths


def compute_manifest_digest(manifest_obj):
    temp = dict(manifest_obj)
    temp["digest"] = ""
    canonical = json.dumps(temp, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(canonical).hexdigest()
    return "sha256:" + digest


def write_manifest(name_tag, config, layers, created=None):
    if ":" in name_tag:
        name, tag = name_tag.split(":", 1)
    else:
        name = name_tag
        tag = "latest"

    manifest = {
        "name": name,
        "tag": tag,
        "digest": "",
        "created": created or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "config": {
            "Env": config.get("Env", []),
            "Cmd": config.get("Cmd"),
            "WorkingDir": config.get("WorkingDir", ""),
            "BaseImage": config.get("BaseImage", "")
        },
        "layers": layers
    }

    manifest["digest"] = compute_manifest_digest(manifest)

    manifest_path, _ = get_image_paths(name_tag)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    return manifest


def load_manifest(name_tag):
    manifest_path, _ = get_image_paths(name_tag)

    if not os.path.exists(manifest_path):
        return None

    with open(manifest_path, "r") as f:
        return json.load(f)

import os
import json
import hashlib
from datetime import datetime, timezone
from storage import get_image_paths


def compute_manifest_digest(manifest_obj):
    temp = dict(manifest_obj)
    temp["digest"] = ""
    canonical = json.dumps(temp, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(canonical).hexdigest()
    return "sha256:" + digest


def write_manifest(name_tag, config, layers, created=None):
    if ":" in name_tag:
        name, tag = name_tag.split(":", 1)
    else:
        name = name_tag
        tag = "latest"

    manifest = {
        "name": name,
        "tag": tag,
        "digest": "",
        "created": created or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "config": {
            "Env": config.get("Env", []),
            "Cmd": config.get("Cmd"),
            "WorkingDir": config.get("WorkingDir", ""),
            "BaseImage": config.get("BaseImage", "")
        },
        "layers": layers
    }

    manifest["digest"] = compute_manifest_digest(manifest)
    manifest_path, _ = get_image_paths(name_tag)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    return manifest


def load_manifest(name_tag):
    manifest_path, _ = get_image_paths(name_tag)

    if not os.path.exists(manifest_path):
        return None

    with open(manifest_path, "r") as f:
        return json.load(f)


def format_inspect_output(name_tag):
    manifest = load_manifest(name_tag)
    if manifest is None:
        return None

    config = manifest.get("config", {})
    layers = manifest.get("layers", [])

    lines = []
    lines.append(f"Name       : {manifest.get('name', '')}")
    lines.append(f"Tag        : {manifest.get('tag', '')}")
    lines.append(f"Digest     : {manifest.get('digest', '')}")
    lines.append(f"Created    : {manifest.get('created', '')}")
    lines.append(f"Base Image : {config.get('BaseImage', '')}")
    lines.append(f"Workdir    : {config.get('WorkingDir', '')}")
    lines.append(f"Cmd        : {config.get('Cmd', '')}")

    env_list = config.get("Env", [])
    if env_list:
        lines.append(f"Env        : {', '.join(env_list)}")
    else:
        lines.append("Env        : ")

    lines.append(f"Layers     : {len(layers)}")

    return "\n".join(lines)


def format_history_output(name_tag):
    manifest = load_manifest(name_tag)
    if manifest is None:
        return None

    lines = []
    lines.append(f"IMAGE: {manifest.get('name', '')}:{manifest.get('tag', '')}")
    lines.append(f"DIGEST: {manifest.get('digest', '')}")
    lines.append(f"CREATED: {manifest.get('created', '')}")
    lines.append("")

    layers = manifest.get("layers", [])
    if not layers:
        lines.append("No layers found")
        return "\n".join(lines)

    for i, layer in enumerate(layers, start=1):
        lines.append(f"{i}. {layer.get('createdBy', 'UNKNOWN')}")
        lines.append(f"   Layer: {layer.get('digest', '')}")
        lines.append(f"   Size : {layer.get('size', 0)} bytes")
        lines.append("")

    return "\n".join(lines)
