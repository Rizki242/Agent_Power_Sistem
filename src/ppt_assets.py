"""Lookup dan penyiapan gambar spektrum untuk laporan PowerPoint.

Gambar diekstrak dari laporan Word oleh `src/docx_parser.py` dengan pola nama
`{CODE}_{YYYY-MM-DD}_img{N}.png` ke folder `data/images`. Modul ini membangun
index sekali per pemanggilan (satu `os.listdir` untuk ribuan file) lalu melayani
lookup per-equipment dengan pencocokan ter-normalisasi.
"""

import io
import os
import re
from collections import defaultdict

from src.data_loader import get_data_path

_NAME_RE = re.compile(r'^(?P<code>.+?)_(?P<date>\d{4}-\d{2}-\d{2})_img(?P<idx>\d+)\.(png|jpg|jpeg)$', re.I)


def norm_equipment(value) -> str:
    """Normalisasi kode equipment: buang non-alfanumerik, uppercase.

    Sama dengan `_norm_equipment` di app.py. Diperlukan karena nama file gambar
    memakai kode tanpa spasi/titik (`BC101_...png`) sementara kolom Equipment
    memakai `BC 10.1`.
    """
    return re.sub(r'[^A-Za-z0-9]', '', str(value or '')).upper()


class SpectrumImageIndex:
    """Index gambar spektrum, dibangun sekali lalu dipakai berulang."""

    def __init__(self, img_dir=None, max_px=1000):
        self.img_dir = img_dir or get_data_path('images')
        self.max_px = max_px
        self._by_code = defaultdict(list)   # norm_code -> list[(date, idx, filename)]
        self._cache = {}                    # filename -> bytes siap embed
        self._build()

    def _build(self):
        if not os.path.isdir(self.img_dir):
            return
        try:
            names = os.listdir(self.img_dir)
        except OSError:
            return
        for name in names:
            m = _NAME_RE.match(name)
            if not m:
                continue
            code = norm_equipment(m.group('code'))
            if not code:
                continue
            try:
                idx = int(m.group('idx'))
            except ValueError:
                idx = 0
            self._by_code[code].append((m.group('date'), idx, name))
        for code in self._by_code:
            # tanggal terbaru dulu, lalu urut nomor gambar menaik
            self._by_code[code].sort(key=lambda t: (t[0], -t[1]), reverse=True)

    def has(self, equipment) -> bool:
        return bool(self._by_code.get(norm_equipment(equipment)))

    def find(self, equipment, limit=4, date=None):
        """Kembalikan list (filename, date) untuk satu sesi pengukuran.

        Ambil tanggal `date` bila tersedia; kalau tidak, tanggal terbaru.
        """
        entries = self._by_code.get(norm_equipment(equipment))
        if not entries:
            return []

        target = None
        if date:
            target = str(date)[:10]
            if not any(e[0] == target for e in entries):
                target = None
        if target is None:
            target = entries[0][0]

        picked = [e for e in entries if e[0] == target]
        picked.sort(key=lambda t: t[1])
        return [(name, d) for d, _idx, name in picked[:limit]]

    def load(self, filename):
        """Baca + downscale gambar, kembalikan BytesIO siap `add_picture`.

        Downscale wajib: 4 gambar mentah per equipment bisa membengkakkan file
        pptx beberapa kali lipat.
        """
        if filename in self._cache:
            return io.BytesIO(self._cache[filename])

        path = os.path.join(self.img_dir, filename)
        try:
            with open(path, 'rb') as fh:
                raw = fh.read()
        except OSError:
            return None

        data = raw
        try:
            from PIL import Image
            with Image.open(io.BytesIO(raw)) as im:
                if max(im.size) > self.max_px:
                    im.thumbnail((self.max_px, self.max_px), Image.LANCZOS)
                if im.mode not in ('RGB', 'L'):
                    im = im.convert('RGB')
                buf = io.BytesIO()
                im.save(buf, format='PNG', optimize=True)
                candidate = buf.getvalue()
                if candidate:
                    data = candidate
        except Exception:
            # Pillow tidak tersedia atau gambar korup: pakai byte asli.
            data = raw

        self._cache[filename] = data
        return io.BytesIO(data)

    def aspect_ratio(self, filename, default=1.6):
        """Rasio lebar/tinggi, untuk fitting gambar tanpa distorsi."""
        path = os.path.join(self.img_dir, filename)
        try:
            from PIL import Image
            with Image.open(path) as im:
                w, h = im.size
                if h:
                    return float(w) / float(h)
        except Exception:
            pass
        return default
