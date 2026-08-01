# movistar-mitrastar-port-forward

Script en Python para automatizar la apertura, cierre y gestión de reglas de port forwarding en el router **Movistar MitraStar GPT-2742GX4X5v6, firmware GL_g2.5_100XNT0b23_2**, directamente a través de las APIs internas del router.

Movistar no expone públicamente ninguna opción de configuración de port forwarding en la interfaz web (al menos en Colombia). La opción existe en el firmware pero está oculta del menu visible. Ademas, la interfaz web es extremadamente lenta e inestable. Este script resuelve ambos problemas: automatiza el proceso completo y es mucho más rápido y confiable que usar la interfaz web manualmente.

Como Movistar no documenta estas APIs, el comportamiento del script fue obtenido mediante **ingeniería inversa del frontend/API del router** (interceptando peticiones con Burp Suite y analizando el JS). No hay garantía de que Movistar no cambie el firmware en una actualización y rompa el script.

---
<img width="1292" height="621" alt="Image" src="https://github.com/user-attachments/assets/dce586a2-c31f-43fd-b275-2459d4672553" />

<img width="1297" height="690" alt="Image" src="https://github.com/user-attachments/assets/607bd24b-f483-432c-bd63-5902298b99a5" />

---
## ⚠️ Advertencia de seguridad

Abrir un puerto en tu router expone ese servicio directamente a internet. Ten en cuenta:

- Usa este script para exposición **temporal** de puertos, no dejes reglas abiertas indefinidamente sin necesidad.
- Evita exponer servicios sensibles (SSH, RDP, paneles de administración) sin protección adicional (VPN, autenticación fuerte, etc.).
- Prioriza usar puertos altos y no estándar en vez de los puertos por defecto (80, 443, 22, 3389) para reducir ruido de escaneos automatizados.
- Revisa periódicamente con `get` que no queden reglas abiertas que ya no necesites.

## Requisitos

```bash
pip install -r requirements.txt
```

## Configuración

Crea un archivo `.env` en la raíz del proyecto con la contraseña de acceso a la interfaz web del router:

```
PASSWORD=tu_password_del_router
```

## Uso

```bash
python3 script.py -h
```
```
usage: script.py [-h] {get,set,add,delete} ...

Movistar MitraStar router port forwarding tool

positional arguments:
  {get,set,add,delete}
    get                 Muestra las reglas de port forwarding actuales
    set                 Modifica una regla existente por id
    add                 Agrega una nueva regla de port forwarding
    delete              Elimina una regla de port forwarding

options:
  -h, --help            show this help message and exit
```

### `get` — listar reglas actuales

```bash
python3 script.py get
```
```
ID  Activo  Ext         Int         IP LAN
1   Sí      8888-8888   8888-8888   192.168.1.47
```

### `add` — agregar una nueva regla

```bash
python3 script.py add --external-port 8888 --internal-port 8888 --lan-ip 192.168.1.47
```

Opcionalmente, agrega `--active off` para crear la regla desactivada de entrada:

```bash
python3 script.py add --external-port 8888 --internal-port 8888 --lan-ip 192.168.1.47 --active off
```

### `set` — modificar una regla existente

Si un campo se omite, se conserva el valor actual de la regla.

```bash
python3 script.py set --id 1 --active off
python3 script.py set --id 1 --external-port 9999
```

### `delete` — eliminar una regla

```bash
python3 script.py delete --id 1
```

## Disclaimer

Este proyecto no está afiliado a Movistar ni a MitraStar. Fue creado para uso personal, en base a ingeniería inversa del panel de administración del propio router del autor. Úsalo bajo tu propio criterio y responsabilidad.
