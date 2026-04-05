import os
import shutil
import tempfile
import hashlib
import time

from storage import init_storage, get_base_images_path, get_image_paths
from manifest import write_manifest, load_manifest
from layer_store import snapshot_files, find_changed_files, create_layer_tar, hash_file
from cache_store import compute_cache_key, cache_lookup, cache_store


def read_docksmithfile(context):
    path = os.path.join(context, "Docksmithfile")

    if not os.path.exists(path):
        print("Docksmithfile not found")
        return []

    with open(path, "r") as f:
        lines = f.readlines()

    return [line.strip() for line in lines if line.strip()]


def parse_instruction(line):
    parts = line.split(" ", 1)
    cmd = parts[0]
    args = parts[1] if len(parts) > 1 else ""
    return cmd, args


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


def hash_copy_source(src_path):
    if os.path.isfile(src_path):
        return hash_file(src_path)

    entries = []
    for current_root, dirs, files in os.walk(src_path):
        dirs.sort()
        files.sort()

        for name in files:
            full_path = os.path.join(current_root, name)
            rel_path = os.path.relpath(full_path, src_path)
            entries.append(rel_path + ":" + hash_file(full_path))

    joined = "|".join(entries)
    return hashlib.sha256(joined.encode()).hexdigest()


def build_image(tag, context, no_cache=False):
    init_storage()

    instructions = read_docksmithfile(context)
    if not instructions:
        return

    config = {
        "Env": [],
        "Cmd": None,
        "WorkingDir": "",
        "BaseImage": ""
    }

    existing_manifest = load_manifest(tag) if tag else None
    original_created = existing_manifest["created"] if existing_manifest else None

    manifest_layers = []
    temp_fs = tempfile.mkdtemp()
    all_layer_steps_hit = True

    print("Temporary FS:", temp_fs)

    try:
        print("\nProcessing Instructions:\n")

        prev_layer_digest = ""

        for line in instructions:
            cmd, args = parse_instruction(line)

            if cmd == "FROM":
                print(f"FROM {args}")
                if not load_base_image(args, temp_fs):
                    return
                config["BaseImage"] = args
                prev_layer_digest = "base:" + args

            elif cmd == "WORKDIR":
                config["WorkingDir"] = args
                print("Set WORKDIR:", args)

            elif cmd == "ENV":
                config["Env"].append(args)
                print("Added ENV:", args)

            elif cmd == "CMD":
                config["Cmd"] = args
                print("Set CMD:", args)

            elif cmd == "COPY":
                parts = args.split()
                if len(parts) != 2:
                    print("Invalid COPY instruction")
                    return

                src, dest = parts
                src_path = os.path.abspath(os.path.join(context, src))

                if not os.path.exists(src_path):
                    print("COPY source not found:", src)
                    return

                extra = hash_copy_source(src_path)
                workdir = config["WorkingDir"] or ""
                env_list = config["Env"]

                cache_key = compute_cache_key(
                    prev_layer_digest,
                    line,
                    workdir,
                    env_list,
                    extra
                )

                start = time.time()
                cached = None if no_cache else cache_lookup(cache_key)

                if cached:
                    duration = time.time() - start
                    print(f"[CACHE HIT] COPY {args} {duration:.2f}s")
                    manifest_layers.append(cached)
                    prev_layer_digest = cached["digest"]
                    continue

                print(f"[CACHE MISS] COPY {args}", end=" ")

                all_layer_steps_hit = False
                before = snapshot_files(temp_fs)

                dest_path = os.path.join(temp_fs, dest.lstrip("/"))
                os.makedirs(dest_path, exist_ok=True)

                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
                else:
                    shutil.copy2(src_path, dest_path)

                after = snapshot_files(temp_fs)
                changed_files = find_changed_files(before, after)

                layer_info = create_layer_tar(temp_fs, changed_files)
                layer_info["createdBy"] = f"COPY {args}"
                manifest_layers.append(layer_info)

                if not no_cache:
                    cache_store(cache_key, layer_info)

                prev_layer_digest = layer_info["digest"]
                duration = time.time() - start
                print(f"{duration:.2f}s")

            elif cmd == "RUN":
                workdir = config["WorkingDir"] or ""
                env_list = config["Env"]

                cache_key = compute_cache_key(
                    prev_layer_digest,
                    line,
                    workdir,
                    env_list
                )

                start = time.time()
                cached = None if no_cache else cache_lookup(cache_key)

                if cached:
                    duration = time.time() - start
                    print(f"[CACHE HIT] RUN {args} {duration:.2f}s")
                    manifest_layers.append(cached)
                    prev_layer_digest = cached["digest"]
                    continue

                print(f"[CACHE MISS] RUN {args}", end=" ")

                all_layer_steps_hit = False
                before = snapshot_files(temp_fs)

                export_cmd = ""
                for env_var in config["Env"]:
                    if "=" in env_var:
                        key, value = env_var.split("=", 1)
                        export_cmd += f'export {key}="{value}"; '

                actual_workdir = config["WorkingDir"] or "/"
                full_command = f'cd "{actual_workdir}" && {export_cmd}{args}'
                chroot_cmd = f"sudo chroot {temp_fs} /bin/sh -c '{full_command}'"

                if os.system(chroot_cmd) != 0:
                    print("\nRUN command failed")
                    return

                after = snapshot_files(temp_fs)
                changed_files = find_changed_files(before, after)

                layer_info = create_layer_tar(temp_fs, changed_files)
                layer_info["createdBy"] = f"RUN {args}"
                manifest_layers.append(layer_info)

                if not no_cache:
                    cache_store(cache_key, layer_info)

                prev_layer_digest = layer_info["digest"]
                duration = time.time() - start
                print(f"{duration:.2f}s")

            else:
                print("Unknown instruction:", cmd)
                return

        print("\nFinal Config:")
        print(config)

        if tag:
            manifest_path, fs_path = get_image_paths(tag)

            if os.path.exists(manifest_path):
                os.remove(manifest_path)

            if os.path.exists(fs_path):
                shutil.rmtree(fs_path)

            shutil.copytree(temp_fs, fs_path)

            created_value = original_created if all_layer_steps_hit and original_created else None
            manifest = write_manifest(tag, config, manifest_layers, created=created_value)

            print("\nImage saved at:", manifest_path)
            print("Image digest:", manifest["digest"])

    finally:
        shutil.rmtree(temp_fs)
        print("Cleaned up temp filesystem")
