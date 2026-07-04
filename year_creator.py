import os

def create_new_year_folder(base_root, last_year_str):
    """
    Creates a new year folder structure based on the last year's structure.
    """
    next_year = int(last_year_str) + 1
    next_year_str = str(next_year)
    new_prefix = f"{next_year - 2003:02d}. "

    last_year_path = os.path.join(base_root, last_year_str)
    next_year_path = os.path.join(base_root, next_year_str)

    if os.path.exists(next_year_path):
        return False, f"El año {next_year_str} ya existe en {base_root}"

    try:
        os.makedirs(next_year_path)
    except Exception as e:
        return False, f"No se pudo crear la carpeta del año {next_year_str}: {e}"

    # Get folders from last year
    try:
        last_year_folders = [d for d in os.listdir(last_year_path) if os.path.isdir(os.path.join(last_year_path, d))]
    except Exception as e:
        return False, f"No se pudo leer la carpeta del año pasado {last_year_str}: {e}"

    new_master_folder_path = None

    for folder_name in last_year_folders:
        # Remove old prefix (everything before the first space and the space itself)
        if ". " in folder_name:
            name_without_prefix = folder_name.split(". ", 1)[1]
        else:
            name_without_prefix = folder_name # Fallback

        if "___[" in folder_name:
            # This is the master folder
            new_folder_name = f"{new_prefix}___[...]"
            new_master_folder_path = os.path.join(next_year_path, new_folder_name)
        else:
            new_folder_name = f"{new_prefix}{name_without_prefix}"

        try:
            os.makedirs(os.path.join(next_year_path, new_folder_name))
        except Exception as e:
            return False, f"No se pudo crear la carpeta {new_folder_name}: {e}"

    # Fill the master folder
    if new_master_folder_path:
        master_subfolders = [
            "_eps",
            "lyrics",
            "mov_1",
            "mov_2",
            "sh_1",
            "sh_2",
            "sp",
            "vocals"
        ]
        for sub in master_subfolders:
            sub_name = f"{new_prefix}{sub}"
            try:
                os.makedirs(os.path.join(new_master_folder_path, sub_name))
            except Exception as e:
                return False, f"No se pudo crear la subcarpeta {sub_name} dentro de la maestra: {e}"

    return True, next_year_str
