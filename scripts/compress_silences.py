"""Re-cut a video, removing long silences but keeping a small buffer."""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Fritz\Documents\PROJECTS\CYBER AGENT")
INPUT = ROOT / "Protego_Demo_merged.mp4"
OUTPUT = ROOT / "Protego_Demo_final.mp4"

NOISE_DB = "-30dB"
MIN_SILENCE = 4.0    # seconds — only cut silences longer than this (preserves ~3.2s clip-boundary breathing room)
BUFFER = 0.30        # seconds — keep on each side of every cut

def get_duration(path: Path) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ], text=True).strip()
    return float(out)

def detect_silences(path: Path):
    proc = subprocess.run([
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
        "-af", f"silencedetect=noise={NOISE_DB}:d={MIN_SILENCE}",
        "-f", "null", "-"
    ], capture_output=True, text=True)
    starts, ends = [], []
    for line in proc.stderr.splitlines():
        m = re.search(r"silence_start: ([\d.]+)", line)
        if m:
            starts.append(float(m.group(1)))
            continue
        m = re.search(r"silence_end: ([\d.]+)", line)
        if m:
            ends.append(float(m.group(1)))
    return list(zip(starts, ends))

def build_keep_segments(silences, duration):
    keep = []
    cursor = 0.0
    for s, e in silences:
        keep_end = max(cursor, s + BUFFER)
        if keep_end > cursor:
            keep.append((cursor, keep_end))
        cursor = max(e - BUFFER, cursor)
    if cursor < duration:
        keep.append((cursor, duration))
    # Drop any segments that ended up too short
    return [(a, b) for a, b in keep if b - a > 0.05]

def main():
    duration = get_duration(INPUT)
    silences = detect_silences(INPUT)
    print(f"Duration: {duration:.2f}s, long silences detected: {len(silences)}")
    for s, e in silences:
        print(f"  silence {s:7.2f} -> {e:7.2f}  ({e-s:5.2f}s)")
    keep = build_keep_segments(silences, duration)
    total_keep = sum(b - a for a, b in keep)
    print(f"Keep segments: {len(keep)}, total kept: {total_keep:.2f}s")

    # Build filter_complex
    parts = []
    for i, (a, b) in enumerate(keep):
        parts.append(f"[0:v]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS[v{i}]")
        parts.append(f"[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS[a{i}]")
    inputs = "".join(f"[v{i}][a{i}]" for i in range(len(keep)))
    parts.append(f"{inputs}concat=n={len(keep)}:v=1:a=1[outv][outa]")
    filter_complex = ";".join(parts)

    cmd = [
        "ffmpeg", "-y", "-i", str(INPUT),
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(OUTPUT),
    ]
    print(f"Running ffmpeg with {len(keep)} keep-segments...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("FFmpeg failed:", result.stderr[-2000:], file=sys.stderr)
        sys.exit(1)
    out_dur = get_duration(OUTPUT)
    print(f"Done. Output: {OUTPUT}  duration={out_dur:.2f}s")

if __name__ == "__main__":
    main()
