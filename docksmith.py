import sys
from build_engine import build_image
from runtime import run_image, list_images, remove_image
from manifest import format_inspect_output, format_history_output


def main():
    if len(sys.argv) < 2:
        print("Usage: docksmith <command>")
        return

    command = sys.argv[1]

    if command == "build":
        tag = None
        context = None
        no_cache = False

        args = sys.argv[2:]
        i = 0

        while i < len(args):
            if args[i] == "-t":
                if i + 1 < len(args):
                    tag = args[i + 1]
                    i += 2
                else:
                    print("Missing tag after -t")
                    return
            elif args[i] == "--no-cache":
                no_cache = True
                i += 1
            else:
                context = args[i]
                i += 1

        if context is None:
            print("Build context not provided")
            return

        build_image(tag, context, no_cache=no_cache)

    elif command == "run":
        if len(sys.argv) < 3:
            print("Usage: docksmith run <image> [cmd] [-e KEY=VALUE]")
            return

        image = sys.argv[2]
        runtime_env = []
        cmd_parts = []

        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "-e":
                if i + 1 < len(sys.argv):
                    runtime_env.append(sys.argv[i + 1])
                    i += 2
                else:
                    print("Missing value after -e")
                    return
            else:
                cmd_parts.append(sys.argv[i])
                i += 1

        override_cmd = " ".join(cmd_parts) if cmd_parts else None
        run_image(image, runtime_env, override_cmd=override_cmd)

    elif command == "images":
        list_images()

    elif command == "rmi":
        if len(sys.argv) < 3:
            print("Usage: docksmith rmi <image>")
            return

        image = sys.argv[2]
        remove_image(image)

    elif command == "inspect":
        if len(sys.argv) < 3:
            print("Usage: docksmith inspect <image>")
            return

        image = sys.argv[2]
        output = format_inspect_output(image)

        if output is None:
            print("Image not found")
        else:
            print(output)

    elif command == "history":
        if len(sys.argv) < 3:
            print("Usage: docksmith history <image>")
            return

        image = sys.argv[2]
        output = format_history_output(image)

        if output is None:
            print("Image not found")
        else:
            print(output)

    else:
        print("Unknown command")


if __name__ == "__main__":
    main()

