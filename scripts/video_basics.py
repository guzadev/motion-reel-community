#!/usr/bin/env python3
"""Three small FFmpeg workflows for the motion-reel-community skill."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def fail(message: str) -> None:
    raise ValueError(message)


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[-1400:]
        fail(f"Falló {' '.join(command[:2])}: {detail}")
    if not capture and result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
    return result


def source_path(base: Path, value: str) -> Path:
    path = Path(value)
    path = (path if path.is_absolute() else base / path).resolve()
    if not path.is_file():
        fail(f"No existe el video: {path}")
    return path


def output_path(base: Path, value: str) -> Path:
    path = Path(value)
    path = (path if path.is_absolute() else base / path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def probe(path: Path) -> float:
    result = run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
         "-of", "json", str(path)], capture=True
    )
    info = json.loads(result.stdout)
    kinds = {stream.get("codec_type") for stream in info.get("streams", [])}
    if not {"video", "audio"}.issubset(kinds):
        fail(f"El archivo necesita video y audio: {path}")
    duration = float(info.get("format", {}).get("duration", 0))
    if duration <= 0:
        fail(f"No se pudo leer la duración: {path}")
    return duration


def interval(item: dict, duration: float, label: str) -> tuple[float, float]:
    try:
        start = float(item.get("start", 0))
        end = float(item.get("end", duration))
    except (TypeError, ValueError):
        fail(f"Tiempos inválidos en {label}")
    if start < 0 or end <= start or end > duration + 0.05:
        fail(f"Rango fuera del video en {label}: {start}–{end} s (duración {duration:.2f} s)")
    return start, min(end, duration)


def safe_name(name: str) -> str:
    if not isinstance(name, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", name):
        fail(f"Nombre inválido: {name!r}. Usá letras, números, guion o guion bajo.")
    return name


def filters(plan: dict) -> str:
    fit = plan.get("fit", "pad")
    if fit == "pad":
        vf = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
    elif fit == "crop":
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    else:
        fail("fit debe ser 'pad' o 'crop'")
    vf += ",setsar=1"
    if "color" in plan:
        color = plan["color"]
        if not isinstance(color, dict):
            fail("color debe ser un objeto JSON")
        brightness = float(color.get("brightness", 0))
        contrast = float(color.get("contrast", 1))
        saturation = float(color.get("saturation", 1))
        if not -1 <= brightness <= 1 or contrast <= 0 or saturation <= 0:
            fail("Valores de color inválidos")
        vf += f",eq=brightness={brightness}:contrast={contrast}:saturation={saturation}"
    return vf


def render(source: Path, start: float, end: float, dest: Path, vf: str) -> None:
    print(f"Renderizando {dest.name}: {source.name} {start:.2f}–{end:.2f} s")
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{start:.3f}",
        "-i", str(source), "-t", f"{end-start:.3f}", "-map", "0:v:0", "-map", "0:a:0",
        "-vf", vf, "-af", "aresample=async=1:first_pts=0", "-r", "30",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", str(dest),
    ])


def combine(parts: list[Path], dest: Path) -> None:
    if len(parts) == 1:
        shutil.copy2(parts[0], dest)
    else:
        manifest = parts[0].parent / "concat.txt"
        manifest.write_text("".join(f"file '{part.name}'\n" for part in parts), encoding="utf-8")
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
             "-i", str(manifest), "-c", "copy", "-movflags", "+faststart", str(dest)])
    probe(dest)
    print(f"Listo: {dest}")


def silence_ranges(source: Path, duration: float, settings: dict) -> list[tuple[float, float]]:
    noise = float(settings.get("noise_db", -35))
    minimum = float(settings.get("min_duration", 0.5))
    padding = float(settings.get("padding", 0.12))
    if minimum <= 0 or padding < 0:
        fail("min_duration debe ser positivo y padding no puede ser negativo")
    command = ["ffmpeg", "-hide_banner", "-i", str(source), "-af",
               f"silencedetect=noise={noise}dB:d={minimum}", "-f", "null", "-"]
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        fail(f"No se pudo detectar silencios: {result.stderr[-1000:]}")
    starts = re.findall(r"silence_start:\s*([\d.]+)", result.stderr)
    ends = re.findall(r"silence_end:\s*([\d.]+)", result.stderr)
    ranges = []
    for index, start_text in enumerate(starts):
        start = float(start_text) + padding
        end = (float(ends[index]) if index < len(ends) else duration) - padding
        if end > start:
            ranges.append((start, end))
    return ranges


def remove_silence(keep: tuple[float, float], silence: list[tuple[float, float]]) -> list[tuple[float, float]]:
    fragments = [keep]
    for silence_start, silence_end in silence:
        remaining = []
        for start, end in fragments:
            if silence_end <= start or silence_start >= end:
                remaining.append((start, end))
            else:
                if silence_start - start >= 0.15:
                    remaining.append((start, silence_start))
                if end - silence_end >= 0.15:
                    remaining.append((silence_end, end))
        fragments = remaining
    return fragments


def recordings(plan: dict, base: Path, vf: str) -> None:
    sources = [source_path(base, value) for value in plan["sources"]]
    if not sources:
        fail("sources no puede estar vacío")
    durations = [probe(path) for path in sources]
    keep = plan.get("keep")
    if keep is None:
        keep = [{"source": i, "start": 0, "end": duration} for i, duration in enumerate(durations)]
    if not keep:
        fail("keep no puede estar vacío")
    settings = plan.get("remove_silence", {})
    if not isinstance(settings, dict):
        fail("remove_silence debe ser un objeto JSON")
    detected: dict[int, list[tuple[float, float]]] = {}
    pieces = []
    for item in keep:
        index = int(item["source"])
        if not 0 <= index < len(sources):
            fail(f"Índice de fuente inválido: {index}")
        cut = interval(item, durations[index], f"keep[{index}]")
        if settings.get("enabled", False):
            if index not in detected:
                detected[index] = silence_ranges(sources[index], durations[index], settings)
            pieces.extend((sources[index], start, end) for start, end in remove_silence(cut, detected[index]))
        else:
            pieces.append((sources[index], *cut))
    if not pieces:
        fail("No quedaron fragmentos después de quitar silencios")
    dest = output_path(base, plan["output"])
    if dest in sources:
        fail("La salida no puede sobrescribir una fuente")
    with tempfile.TemporaryDirectory(prefix="motion-reel-", dir=dest.parent) as temp:
        parts = []
        for index, (source, start, end) in enumerate(pieces):
            part = Path(temp) / f"part_{index:03d}.mp4"
            render(source, start, end, part, vf)
            parts.append(part)
        combine(parts, dest)


def clips(plan: dict, base: Path, vf: str) -> None:
    source = source_path(base, plan["source"])
    duration = probe(source)
    folder = output_path(base, str(Path(plan["output_dir"]) / "placeholder.mp4")).parent
    items = plan["clips"]
    if not items:
        fail("clips no puede estar vacío")
    names = [safe_name(item["name"]) for item in items]
    if len(set(names)) != len(names):
        fail("Los nombres de clips deben ser únicos")
    for item, name in zip(items, names):
        start, end = interval(item, duration, name)
        dest = folder / f"{name}.mp4"
        if dest == source:
            fail("La salida no puede sobrescribir una fuente")
        render(source, start, end, dest, vf)
        probe(dest)
        print(f"Listo: {dest}")


def hooks(plan: dict, base: Path, vf: str) -> None:
    body = plan["body"]
    body_source = source_path(base, body["source"])
    body_range = interval(body, probe(body_source), "body")
    folder = output_path(base, str(Path(plan["output_dir"]) / "placeholder.mp4")).parent
    items = plan["hooks"]
    if not items:
        fail("hooks no puede estar vacío")
    names = [safe_name(item["name"]) for item in items]
    if len(set(names)) != len(names):
        fail("Los nombres de hooks deben ser únicos")
    with tempfile.TemporaryDirectory(prefix="motion-reel-", dir=folder) as temp:
        body_part = Path(temp) / "body.mp4"
        render(body_source, *body_range, body_part, vf)
        for index, (item, name) in enumerate(zip(items, names)):
            source = source_path(base, item["source"])
            start, end = interval(item, probe(source), name)
            dest = folder / f"{name}.mp4"
            if dest in {source, body_source}:
                fail("La salida no puede sobrescribir una fuente")
            hook_part = Path(temp) / f"hook_{index:03d}.mp4"
            render(source, start, end, hook_part, vf)
            combine([hook_part, body_part], dest)


def main() -> None:
    if len(sys.argv) != 2:
        fail("Uso: python scripts/video_basics.py plan.json")
    for executable in ("ffmpeg", "ffprobe"):
        if shutil.which(executable) is None:
            fail(f"Falta {executable} en PATH")
    plan_file = Path(sys.argv[1]).resolve()
    plan = json.loads(plan_file.read_text(encoding="utf-8"))
    base = plan_file.parent
    vf = filters(plan)
    modes = {"recordings": recordings, "clips": clips, "hooks": hooks}
    mode = plan.get("mode")
    if mode not in modes:
        fail("mode debe ser recordings, clips o hooks")
    modes[mode](plan, base, vf)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, FileNotFoundError, json.JSONDecodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
