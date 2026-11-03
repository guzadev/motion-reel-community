---
name: motion-reel-community
description: Editar reels simples a partir de grabaciones, extraer clips de videos largos y crear variantes con distintos hooks sobre un mismo cuerpo. Usar cuando la persona quiere aplicar alguna de esas tres formas de edición con sus propios videos.
---

# Motion Reel Community

Esta skill crea videos verticales sencillos con archivos locales y FFmpeg. Elegí uno de los tres modos según el pedido:

1. **Grabaciones → reel:** ordenar tomas, elegir los fragmentos útiles, quitar silencios si conviene y aplicar una corrección de color suave solo si se solicita o hace falta.
2. **Video largo → clips:** elegir momentos que se entiendan por sí solos, con una apertura clara y un cierre natural; exportar cada rango como video independiente.
3. **Hooks → versiones:** combinar varias aperturas con el mismo cuerpo para probar distintas entradas al mismo contenido.

## Flujo breve

- Pedí los archivos de origen solo si faltan. Leé el pedido y verificá duración, orientación y audio con `ffprobe`. Si hay transcripción disponible, usala para decidir cortes; si no, mirá o escuchá el material. No inventes frases ni elijas clips por duración solamente.
- Prepará un archivo JSON basado en [examples](examples/) con las rutas, los rangos y la salida. Los tiempos están en segundos y `end` es el final exclusivo. Rutas relativas se resuelven desde el JSON.
- Ejecutá `python scripts/video_basics.py plan.json`. El script requiere Python 3.9+ y `ffmpeg`/`ffprobe` en PATH. Produce MP4 H.264/AAC, 1080×1920, 30 fps. El encuadre predeterminado agrega márgenes cuando hace falta; `fit: "crop"` llena el cuadro recortando bordes.
- Revisá cada exportación reproduciéndola: inicio, cortes, audio, encuadre y final. Corregí rangos o parámetros y volvé a exportar si hay errores. Entregá los archivos y explicá brevemente qué se editó.

## Decisiones importantes

- En grabaciones, `remove_silence` es opcional. El detector de silencio solo encuentra pausas de audio; no reconoce errores al hablar ni decide qué idea conservar. Revisá los cortes antes de entregar.
- `keep` permite excluir errores, ordenar tomas y conservar pausas deliberadas. Sin `keep`, se usa cada fuente completa en el orden dado.
- En clips, elegí rangos por sentido, no solo por picos de audio. Si se necesita transcripción automática, usá una herramienta disponible en el entorno; esta skill no exige una cuenta ni un servicio externo.
- En hooks, cada apertura debe decir algo distinto y enlazar naturalmente con el mismo cuerpo. El script no genera ganchos escritos ni publica reels de prueba.
- El material y las salidas pertenecen a la persona usuaria. No incluyas recursos privados, marcas ajenas, credenciales ni rutas personales en paquetes para terceros.

Para empezar o compartirla, [README.md](README.md) explica instalación y uso. Los tres JSON de [examples](examples/) son plantillas editables.
