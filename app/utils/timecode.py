def ms_to_mmss(ms: int) -> str:
    s = ms // 1000
    return f"{s//60}:{s%60:02d}"