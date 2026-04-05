import os


def init_storage():
    base = os.path.expanduser("~/.docksmith")
    os.makedirs(os.path.join(base, "images"), exist_ok=True)
    os.makedirs(os.path.join(base, "layers"), exist_ok=True)
    os.makedirs(os.path.join(base, "cache"), exist_ok=True)
    os.makedirs(os.path.join(base, "base_images"), exist_ok=True)


def get_base_path():
    return os.path.expanduser("~/.docksmith")


def get_images_path():
    return os.path.join(get_base_path(), "images")


def get_layers_path():
    return os.path.join(get_base_path(), "layers")


def get_cache_path():
    return os.path.join(get_base_path(), "cache")


def get_base_images_path():
    return os.path.join(get_base_path(), "base_images")


def get_image_paths(name_tag):
    image_key = name_tag.replace(":", "_")
    images_dir = get_images_path()
    manifest_path = os.path.join(images_dir, image_key + ".json")
    fs_path = os.path.join(images_dir, image_key + "_fs")
    return manifest_path, fs_path
