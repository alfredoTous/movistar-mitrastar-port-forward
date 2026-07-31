import requests
import argparse
import re
import hashlib

import os
from dotenv import load_dotenv

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


load_dotenv()

main_url = "https://192.168.1.1:8000"

password = os.getenv('PASSWORD') # Password de interfaz web del router



def login():
    session = requests.Session() # Crear sesion persistente
    session.verify = False # Ignorar certificado autofirmado

    response = session.get(main_url)

    # Parsear SID del get para implementar hash md5 de 'password:sid' el cual es lo que el server espera
    match = re.search(r"var sid\s*=\s*'([a-f0-9]+)'", response.text)
    if match == None:
        print("[-] Error parseando sid")
        return 
    sid = match.group(1)
    # ==================================================================================

    # Crear hash
    input = f"{password}:{sid}"
    pwd_hash = hashlib.md5(input.encode()).hexdigest()

    data = {
        "sessionKey": "",
        "submitValue": "1",
        "fake_syspasswd": "",
        "syspasswd_1": "",
        "syspasswd": pwd_hash,
        "leaveBlur": "0",
        "Submit": "Entrar",
    }

    # Loguearnos
    response = session.post(f"{main_url}/cgi-bin/logIn_mhs.cgi", data=data)

    return session


def get_rules(session: requests.Session):
    response = session.get(f"{main_url}/cgi-bin/port_forwarding_list.cgi",
                            headers={"X-Requested-With": "XMLHttpRequest"})
    html = response.text

    rule_ids = re.findall(r'PortForwarding_Name_(\d+)', html)

    rules = []
    for rid in rule_ids:
        name_match = re.search(rf'id="PortForwarding_Name_{rid}">([^<]*)<', html)
        ext_start = re.search(rf'id="PortForwarding_ExtStartPort_{rid}">([^<]*)<', html)
        ext_end = re.search(rf'id="PortForwarding_ExtEndPort_{rid}">([^<]*)<', html)
        int_start = re.search(rf'id="PortForwarding_LocalSPort_{rid}">([^<]*)<', html)
        int_end = re.search(rf'id="PortForwarding_LocalEPort_{rid}">([^<]*)<', html)
        ip = re.search(rf'id="PortForwarding_HOSTNAME_{rid}">([^<]*)<', html)

        img_tag = re.search(rf'<img[^>]*id="PortForwarding_Active_{rid}"[^>]*>', html)
        is_active = img_tag is not None and "i_active_on" in img_tag.group(0)

        rules.append({
            "id": int(rid),
            "active": is_active,
            "name": name_match.group(1) if name_match else None,
            "ext_start_port": ext_start.group(1) if ext_start else None,
            "ext_end_port": ext_end.group(1) if ext_end else None,
            "int_start_port": int_start.group(1) if int_start else None,
            "int_end_port": int_end.group(1) if int_end else None,
            "lan_ip": ip.group(1) if ip else None,
        })

    return rules


def add_rule(session: requests.Session, external_port: int, internal_port: int, lan_ip: str,
             rule_index: int, active: bool = True):
    data = {
        "reloadFlag": "1",
        "editFlag": "1",
        "ruleindex": str(rule_index),  # 0-indexed
        "PortRule_Active": "Yes" if active else "No",
        "start_port": str(external_port),
        "end_port": str(external_port),
        "appName": "User Define",
        "Addr": lan_ip,
        "PortRule_Protocol": "ALL",
        "oStart": str(internal_port),
        "oEnd": str(internal_port),
        "NAT_VCIndex": "",
    }
    headers = {"X-Requested-With": "XMLHttpRequest"}
    response = session.post(f"{main_url}/cgi-bin/portForwarding.cgi", data=data, headers=headers)
    return response


def set_rule(session: requests.Session, rule_id: int, active: str | None = None,
             external_port: int | None = None, internal_port: int | None = None,
             lan_ip: str | None = None):
    # Traer el estado actual de la regla para rellenar lo que no se paso por args
    rules = get_rules(session)
    current = None
    for i in rules:
        if i["id"] == rule_id:
            current = i
            break
    if current is None:
        print(f"[-] No existe la regla con id {rule_id}")
        return None

    final_active = current["active"] if active is None else (active == "on")
    final_ext = external_port if external_port is not None else int(current["ext_start_port"])
    final_int = internal_port if internal_port is not None else int(current["int_start_port"])
    final_ip = lan_ip if lan_ip is not None else current["lan_ip"]

    data = {
        "reloadFlag": "1",
        "editFlag": "1",
        "ruleindex": str(rule_id - 1),  # 0-indexed
        "PortRule_Active": "Yes" if final_active else "No",
        "start_port": str(final_ext),
        "end_port": str(final_ext),
        "appName": "User Define",
        "Addr": final_ip,
        "PortRule_Protocol": "ALL",
        "oStart": str(final_int),
        "oEnd": str(final_int),
        "NAT_VCIndex": "",
    }
    headers = {"X-Requested-With": "XMLHttpRequest"}
    response = session.post(f"{main_url}/cgi-bin/portForwarding.cgi", data=data, headers=headers)
    return response


def delete_rule(session, rule_id: int):
    data = {
        "reloadFlag": "1",
        "delFlag": "1",
        "delnum": str(rule_id-1),
    }
    headers = {"X-Requested-With": "XMLHttpRequest"}
    response = session.post(f"{main_url}/cgi-bin/portForwarding.cgi", data=data, headers=headers)
    return response



# =============== Helpers ========================================

def next_free_index(session):
    rules = get_rules(session)
    used = {r["id"] - 1 for r in rules}  # convertir a 0-indexed
    idx = 0
    while idx in used:
        idx += 1
    return idx

def print_rules(rules):
    print(f"{'ID':<4}{'Activo':<8}{'Ext':<12}{'Int':<12}{'IP LAN':<16}")
    for r in rules:
        ext = f"{r['ext_start_port']}-{r['ext_end_port']}"
        intr = f"{r['int_start_port']}-{r['int_end_port']}"
        print(f"{r['id']:<4}{'Sí' if r['active'] else 'No':<8}{ext:<12}{intr:<12}{r['lan_ip']:<16}")



def parse_args():
    parser = argparse.ArgumentParser(description="Movistar MitraStar router port forwarding tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # get
    subparsers.add_parser("get", help="Muestra las reglas de port forwarding actuales")

    # set
    set_parser = subparsers.add_parser("set", help="Modifica una regla existente por id")
    set_parser.add_argument("--id", type=int, required=True, help="Índice de la regla a modificar")
    set_parser.add_argument("--active", choices=["on", "off"], default=None, help="Activar o desactivar la regla")
    set_parser.add_argument("--external-port", type=int, default=None, help="Puerto externo (opcional)")
    set_parser.add_argument("--internal-port", type=int, default=None, help="Puerto interno (opcional)")
    set_parser.add_argument("--lan-ip", type=str, default=None, help="IP LAN de destino (opcional)")

    # add
    add_parser = subparsers.add_parser("add", help="Agrega una nueva regla de port forwarding")
    add_parser.add_argument("--external-port", type=int, required=True, help="Puerto externo")
    add_parser.add_argument("--internal-port", type=int, required=True, help="Puerto interno")
    add_parser.add_argument("--lan-ip", type=str, required=True, help="IP LAN de destino")
    add_parser.add_argument("--active", choices=["on", "off"], default="on", help="Estado inicial de la regla (default: on)")

    # delete
    delete_parser = subparsers.add_parser("delete", help="Elimina una regla de port forwarding")
    delete_parser.add_argument("--id", type=int, required=True, help="Indice de la regla a eliminar")


    return parser.parse_args()


def main():

    args = parse_args();

    session = login()
    if session == None:
        print("[-] Error la autenticacion fallo")
        return

    if args.command == "get":
        rules = get_rules(session)
        print_rules(rules)
        return

    if args.command == "add":
        idx = next_free_index(session)
        response = add_rule(session, args.external_port, args.internal_port, args.lan_ip, idx, args.active)
        if (response.status_code == 200):
            print("[+] Regla agregada correctamente")
        else:
            print(f"[-] Error agregando regla -- status {response.status_code}")
        return

    if args.command == "set":
        response = set_rule(session, rule_id=args.id, active=args.active,
                       external_port=args.external_port,
                       internal_port=args.internal_port,
                       lan_ip=args.lan_ip)
        if response == None:
            return
        if response.status_code == 200:
            print(f"Regla {args.id} actualizada correctamente")
        else:
            print(f"[-] Error editando regla -- status {response.status_code}")


    if args.command == "delete":
        response = delete_rule(session, rule_id=args.id)
        if response.status_code == 200:
            print(f"[+] Regla {args.id} eliminada correctamente")
        else:
            print(f"[-] Error eliminando regla -- status {response.status_code}")
        return


if __name__ == "__main__":
    main()


