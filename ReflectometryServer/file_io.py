import os

from ReflectometryServer.ChannelAccess.constants import REFL_CONFIG_PATH


AUTOSAVE_FILE_PATH = os.path.join(REFL_CONFIG_PATH, "refl", "params.txt")


def _format_param(key, value):
    return "{} {}\n".format(key, value)


def read_autosave_param(param_name):
    try:
        with open(AUTOSAVE_FILE_PATH) as f:
            lines = f.readlines()
            for line in lines:
                key, val = line.split()
                if key == param_name:
                    return val
    except Exception as e:
        print e
        return None


def write_autosave_param(param_name, value):
    try:
        if not os.path.exists(AUTOSAVE_FILE_PATH):
            with open(AUTOSAVE_FILE_PATH, "w") as f:
                f.writelines(_format_param(param_name, value))
                return
        else:
            with open(AUTOSAVE_FILE_PATH, "r") as f:
                lines = f.readlines()
                print(lines)
            with open(AUTOSAVE_FILE_PATH, "w+") as f:
                for i in range(len(lines)):
                    key = lines[i].split()[0]
                    if key == param_name:
                        lines[i] = _format_param(param_name, value)
                        f.writelines(lines)
                        print("Parameter {} autosave value changed: {}".format(param_name, value))
                        return
                lines.append(_format_param(param_name, value))
                f.writelines(lines)
                print("Parameter {} autosave value added: {}".format(param_name, value))
    except Exception as e:
        print(e)
