# Motion Reel Community

Skill básica para editar videos con tres flujos: **grabaciones a reel**, **video largo a clips** y **varios hooks sobre el mismo cuerpo**. Es independiente de `motion-reel`.

## Instalación

1. Instalá Python 3.9 o superior y FFmpeg. Comprobá que `ffmpeg` y `ffprobe` funcionen desde una terminal.
2. Copiá esta carpeta completa a `~/.claude/skills/motion-reel-community/` para usarla con Claude Code, o a `~/.codex/skills/motion-reel-community/` para usarla con Codex.
3. Pedile al agente: «Usá `motion-reel-community` para editar este video». También podés ejecutar el script directamente.

No requiere paquetes de Python, API keys, modelos pagos ni archivos de la skill original.

## Uso rápido

Copiá uno de los JSON de `examples/`, poné las rutas de tus videos y ajustá los tiempos. Después ejecutá:

```sh
python scripts/video_basics.py mi-plan.json
```

Los archivos MP4 aparecerán en la ruta `output` o dentro de `output_dir`. Todas las rutas relativas del plan se interpretan desde la ubicación del JSON. El script verifica que los rangos existan y que las fuentes tengan audio.

| Modo | Plantilla | Resultado |
| --- | --- | --- |
| `recordings` | `examples/recordings.json` | Un reel desde una o varias tomas, con cortes, eliminación opcional de silencios y color opcional. |
| `clips` | `examples/clips.json` | Varios clips independientes desde un video largo. |
| `hooks` | `examples/hooks.json` | Una versión por hook, todas con el mismo cuerpo. |

## Opciones comunes

- `fit`: `pad` conserva todo el cuadro y añade márgenes; `crop` llena 9:16 recortando bordes.
- `color`: `brightness` entre -1 y 1, `contrast` y `saturation` positivos. Omitilo para mantener el color original.
- `remove_silence` en `recordings`: `noise_db` (por defecto -35), `min_duration` (0.5 s) y `padding` (0.12 s). Si quita una pausa útil, desactivalo y definí los cortes con `keep`.

Elige los rangos mirando o escuchando el video. El script hace la edición mecánica; no identifica automáticamente los momentos más interesantes ni escribe hooks.
