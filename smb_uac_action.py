from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from windows_share_manager import WindowsShareManager


def _norm_path(value: str) -> str:
    return os.path.normcase(os.path.normpath(os.path.abspath(value)))


def _find_share_by_folder(manager: WindowsShareManager, folder_path: str):
    target = _norm_path(folder_path)
    for share in manager.obtener_carpetas_compartidas():
        ruta = share.get("ruta")
        if not ruta:
            continue
        try:
            if _norm_path(str(ruta)) == target:
                return share
        except Exception:
            continue
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", required=True, choices=["connect", "disconnect"])
    parser.add_argument("--folder", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out_path = Path(args.out)

    try:
        manager = WindowsShareManager()
        folder = args.folder

        if not os.path.isdir(folder):
            raise RuntimeError("La carpeta no existe o no es accesible.")

        if args.action == "connect":
            share = _find_share_by_folder(manager, folder)
            if share:
                payload = {
                    "ok": True,
                    "level": "ok",
                    "messages": [f"Recurso compartido creado: {share_name}"],
                    "share_name": share_name,
                    "share": share,
                }
            else:
                base_name = Path(folder).name.strip() or "SharedFolder"
                share_name = WindowsShareManager.normalizar_share_name(base_name)
                manager.compartir_carpeta(folder, share_name)
                share = _find_share_by_folder(manager, folder)
                payload = {
                    "ok": True,
                    "level": "ok",
                    "messages": ["Recurso compartido creado correctamente."],
                    "share": share,
                }

        elif args.action == "disconnect":
            share = _find_share_by_folder(manager, folder)
            if not share:
                raise RuntimeError("La carpeta no está compartida.")
            share_name = share.get("nombre")
            if not share_name:
                raise RuntimeError("No se pudo determinar el nombre del recurso compartido.")
            manager.descompartir_carpeta(str(share_name))
            payload = {
                "ok": True,
                "level": "ok",
                "messages": [f"Recurso compartido eliminado: {share_name}"],
                "share_name": share_name,
            }

        out_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return 0

    except Exception as exc:
        payload = {
            "ok": False,
            "level": "error",
            "messages": [str(exc)],
        }
        out_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())