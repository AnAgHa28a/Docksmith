import os
import tarfile
import hashlib
from storage import get_layers_path


def hash_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def snapshot_files(root):
    state = {}

    for current_root, dirs, files in os.walk(root):
        dirs.sort()
        files.sort()

        for name in files:
            full_path = os.path.join(current_root, name)
            rel_path = os.path.relpath(full_path, root)
            state[rel_path] = hash_file(full_path)

    return state


def find_changed_files(before, after):
    changed = []

    for path, digest in after.items():
        if path not in before or before[path] != digest:
            changed.append(path)

    changed.sort()
    return changed


def _deterministic_tarinfo(tarinfo):
    tarinfo.mtime = 0
    tarinfo.uid = 0
    tarinfo.gid = 0
    tarinfo.uname = ""
    tarinfo.gname = ""
    return tarinfo


def create_layer_tar(root, changed_files):
    layers_dir = get_layers_path()
    temp_tar_path = os.path.join(layers_dir, "temp_layer.tar")

    with tarfile.open(temp_tar_path, "w") as tar:
        for rel_path in sorted(changed_files):
            full_path = os.path.join(root, rel_path)
            if os.path.exists(full_path):
                tar.add(full_path, arcname=rel_path, filter=_deterministic_tarinfo)

    digest = hash_file(temp_tar_path)
    final_name = f"sha256_{digest}.tar"
    final_path = os.path.join(layers_dir, final_name)

    if not os.path.exists(final_path):
        os.rename(temp_tar_path, final_path)
    else:
        os.remove(temp_tar_path)

    size = os.path.getsize(final_path)

    return {
        "digest": "sha256:" + digest,
        "size": size
    }


def extract_layer_tar(layer_digest, dest_root):
    digest_value = layer_digest.replace("sha256:", "")
    tar_path = os.path.join(get_layers_path(), f"sha256_{digest_value}.tar")

    if not os.path.exists(tar_path):
        raise FileNotFoundError(f"Layer file missing: {tar_path}")

    with tarfile.open(tar_path, "r") as tar:
        tar.extractall(dest_root)
