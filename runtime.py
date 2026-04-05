import os
import json
import shutil
import tempfile
from manifest import load_manifest
from storage import get_image_paths, get_images_path, get_base_images_path, get_layers_path
from layer_store import extract_layer_tar


def load_base_image(image_name, temp_fs):
    base_path = get_base_images_path()
    source_path = os.path.join(base_path, image_name)

    if not os.path.exists(source_path):
        print("Base image not found:", image_name)
        return False

    for item in os.listdir(source_path):
        s = os.path.join(source_path, item)
        d = os.path.join(temp_fs, item)

        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)

    return True


def run_image(image, runtime_env, override_cmd=None):
    manifest = load_manifest(image)
    if manifest is None:
        print("Image not found")
        return

    temp_fs = tempfile.mkdtemp()

    try:
        config = manifest.get("config", {})
        base_image = config.get("BaseImage", "")

        if not base_image:
            print("Base image missing in manifest")
            return

        if not load_base_image(base_image, temp_fs):
            return

        for layer in manifest.get("layers", []):
            extract_layer_tar(layer["digest"], temp_fs)

        print("Running image:", image)

        workdir = config.get("WorkingDir", "/")
        if workdir == "":
            workdir = "/"

        cmd = override_cmd if override_cmd else config.get("Cmd")
        if not cmd:
            print("No CMD specified and no runtime command provided")
            return

        env_map = {}

        for env_var in config.get("Env", []):
            if "=" in env_var:
                k, v = env_var.split("=", 1)
                env_map[k] = v

        for env_var in runtime_env:
            if "=" in env_var:
                k, v = env_var.split("=", 1)
                env_map[k] = v

        export_cmd = ""
        for k in env_map:
            export_cmd += f'export {k}="{env_map[k]}"; '

        inner_cmd = f'cd "{workdir}" && {export_cmd}{cmd}'
        run_cmd = f"sudo unshare --pid --fork --mount chroot {temp_fs} /bin/sh -c '{inner_cmd}'"

        if os.system(run_cmd) != 0:
            print("Container execution failed")

    finally:
        shutil.rmtree(temp_fs)


def list_images():
    base_path = get_images_path()

    if not os.path.exists(base_path):
        print("No images found")
        return

    manifest_files = [f for f in os.listdir(base_path) if f.endswith(".json")]

    if not manifest_files:
        print("No images found")
        return

    print(f"{'NAME':<15} {'TAG':<10} {'IMAGE ID':<14} {'CREATED'}")

    for file_name in sorted(manifest_files):
        file_path = os.path.join(base_path, file_name)

        with open(file_path, "r") as f:
            manifest = json.load(f)

        name = manifest.get("name", "")
        tag = manifest.get("tag", "")
        digest = manifest.get("digest", "")
        created = manifest.get("created", "")
        short_id = digest.replace("sha256:", "")[:12]

        print(f"{name:<15} {tag:<10} {short_id:<14} {created}")


def remove_image(image):
    manifest = load_manifest(image)
    manifest_path, fs_path = get_image_paths(image)
    removed = False

    if manifest is None:
        print("Image not found")
        return

    layers_dir = get_layers_path()
    for layer in manifest.get("layers", []):
        digest_value = layer["digest"].replace("sha256:", "")
        tar_path = os.path.join(layers_dir, f"sha256_{digest_value}.tar")
        if os.path.exists(tar_path):
            os.remove(tar_path)

    if os.path.exists(manifest_path):
        os.remove(manifest_path)
        removed = True

    if os.path.exists(fs_path):
        shutil.rmtree(fs_path)
        removed = True

    if removed:
        print("Removed:", image)
    else:
        print("Image not found")
