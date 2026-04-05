import os
import json
import hashlib
from storage import get_base_path, get_layers_path


def get_cache_path():
    path = os.path.join(get_base_path(), "cache")
    os.makedirs(path, exist_ok=True)
    return path


def compute_hash(data):
    return hashlib.sha256(data.encode()).hexdigest()


def compute_cache_key(prev_digest, instruction, workdir, env_list, extra=""):
    env_sorted = sorted(env_list)
    env_serialized = "|".join(env_sorted)
    base = prev_digest + "|" + instruction + "|" + workdir + "|" + env_serialized + "|" + extra
    return compute_hash(base)


def layer_file_exists(layer_digest):
    digest_value = layer_digest.replace("sha256:", "")
    tar_path = os.path.join(get_layers_path(), f"sha256_{digest_value}.tar")
    return os.path.exists(tar_path)


def cache_lookup(key):
    path = os.path.join(get_cache_path(), key + ".json")
    if not os.path.exists(path):
        return None

    with open(path, "r") as f:
        layer_info = json.load(f)

    if "digest" not in layer_info:
        return None

    if not layer_file_exists(layer_info["digest"]):
        return None

    return layer_info


def cache_store(key, layer_info):
    path = os.path.join(get_cache_path(), key + ".json")
    with open(path, "w") as f:
        json.dump(layer_info, f)
