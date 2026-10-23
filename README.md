# NUKE TOOL (Python)

Herramienta de destruccion de servidores Discord para Termux. Interfaz de terminal con
banner ASCII, colores truecolor y multiples funciones de nuke.

## Instalacion (Termux)

```bash
pkg update && pkg upgrade -y
pkg install python git clang make libffi openssl -y
git clone https://github.com/kravox-tool/nuke-tool.git
cd nuke-tool
pip install -r requirements.txt
python main.py
```

Si `aiohttp` falla al compilar, instala el toolchain completo primero:

```bash
pkg install build-essential binutils -y
pip install aiohttp --no-binary aiohttp
```

## Configuracion del bot

1. Discord Developer Portal -> New Application -> Bot.
2. Activa `SERVER MEMBERS INTENT` en Privileged Gateway Intents.
3. Dentro de la herramienta: `login TU_TOKEN`
4. Invita el bot con Administrator:
   `https://discord.com/oauth2/authorize?client_id=TU_CLIENT_ID&scope=bot&permissions=8`

## Uso

```
guilds            lista los servidores
use 2             selecciona el servidor numero 2
info              datos del servidor activo
nuke              DESTRUCCION TOTAL
```

## Comandos

| Comando | Descripcion |
|---|---|
| `nuke` | Borra roles y canales, recrea categoria + canales, crea rol admin, limpia emojis/stickers |
| `banall [razon]` | Banea a todos los miembros |
| `kickall [razon]` | Expulsa a todos los miembros |
| `nickall <nick>` | Cambia el nick de todos |
| `dmall <mensaje>` | Envia un DM a todos |
| `rename <nombre>` | Renombra el servidor |
| `renamebot <nombre>` | Renombra el bot |
| `roledestroy` | Borra todos los roles |
| `rolespam <n>` | Crea N roles con admin |
| `roleall <rol>` | Da un rol a todos |
| `chandestroy` | Borra todos los canales |
| `chanspam <n> [voice]` | Crea N canales |
| `emojidestroy` | Borra todos los emojis |
| `stickerdestroy` | Borra todos los stickers |
| `vcdisconnect` | Saca a todos de voz |
| `status <texto>` | Cambia el estado del bot |
| `auto on/off` | Nuke automatico al entrar a un servidor |
| `config` | Ver/editar parametros del nuke |
| `clear` / `exit` | Limpiar pantalla / salir |

## Configuracion del nuke

`config.json` se genera solo. Desde la herramienta:

```
config text_count 30
config ban_all true
config guild_name Mi Servidor
```

| Clave | Default | Descripcion |
|---|---|---|
| `guild_name` | `nuked by <bot>` | Nombre final del servidor |
| `role_name` | `nuked` | Rol creado al final |
| `category_name` | `NUKE` | Nombre de la categoria |
| `text_count` | `15` | Canales de texto a crear |
| `voice_count` | `3` | Canales de voz a crear |
| `delete_roles` | `true` | Borrar roles |
| `delete_channels` | `true` | Borrar canales |
| `delete_emojis` | `true` | Borrar emojis |
| `delete_stickers` | `true` | Borrar stickers |
| `ban_all` | `false` | Banear a todos en el nuke |
| `concurrency` | `3` | Operaciones en paralelo |

## Notas

- Python 3.9+ requerido (usa `asyncio.to_thread`).
- Con token de bot el bot no se banea a si mismo (configurable con `ban_self`).
- La creacion de canales tiene rate limit: 100 canales tarda un rato.
- `renamebot` esta limitado a 2 cambios por hora por Discord.
- **Selfbot:** si usas tu token de usuario, pon `chunk_guilds_at_startup=False` en `create_client()`
  y considera `pip install discord.py-self` (misma API, mejor soporte de user tokens).

## Licencia

MIT
