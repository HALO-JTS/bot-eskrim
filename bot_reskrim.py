import os
import re
import random
from datetime import datetime, date, timedelta, timezone
import requests
from playwright.sync_api import sync_playwright

EMAIL = os.environ.get("POSKO_EMAIL", "").strip()
PASSWORD = os.environ.get("POSKO_PASSWORD", "").strip()
TG_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

# ==========================================================
# IDENTITAS & 1 LINK FOLDER GOOGLE DRIVE UNTUK 8 KEGIATAN
# ==========================================================
NAMA_KANIT_RESKRIM = "AIPDA EKO HERI ANC"
FOLDER_UTAMA_URL = "https://drive.google.com/drive/folders/1q2wd72u-Hx3cEcMe2aBCykG8HjtuyBO2"
DEFAULT_LINK = "https://drive.google.com/file/d/17KmVFmPU-OZk0dBdbVgF7AZ6ayhGWPyl/view?usp=drivesdk"
TANGGAL_PATOKAN = date(2026, 10, 31)

# ==========================================================
# VARIASI OTOMATIS QW1.9 (RUTE PATROLI SIAGA RESERSE)
# ==========================================================
DAFTAR_RUTE_RESERSE = [
    "MAKO POLSEK JATISRONO - PASAR JATISRONO - SPBU - BANK BRI - BANK BNI - MAKO",
    "MAKO POLSEK JATISRONO - SIMPANG 4 TERMINAL - BANK BPD - BANK MANDIRI - ALAS MBOGO - MAKO",
    "MAKO POLSEK JATISRONO - JALAN RAYA JATISRONO - KAWASAN PERTOKOAN - OBVIT PERBANKAN - SPBU - MAKO",
    "MAKO POLSEK JATISRONO - TUGU BINTANG - PASAR JATISRONO - PEMUKIMAN PENDUDUK - SPBU - MAKO",
]

ALASAN_RUTE_RESERSE = [
    "Antisipasi tindak pidana C3 (Curat, Curas, Curanmor), premanisme, dan kejahatan jalanan pada jam rawan",
    "Pemantauan titik rawan kejahatan jalanan, objek vital perbankan, serta pusat aktivitas masyarakat di wilayah Jatisrono",
    "Mencegah potensi gangguan kamtibmas, pemerasan, dan tindak kriminalitas malam hari di wilayah hukum Polsek Jatisrono",
    "Patroli mobile dan dialogis fungsi reserse guna memastikan situasi keamanan wilayah Jatisrono tetap kondusif",
]

# ==========================================================
# VARIASI OTOMATIS QW3.1 (LOKASI PENEGAKAN JUDI & PENIPUAN DIGITAL)
# ==========================================================
PAKET_LOKASI_QW3_1 = [
    {
        "lokasi": "KAWASAN PASAR JATISRONO",
        "koordinat": "(-7.8273937, 111.1285440)",
        "pertimbangan": "Pusat keramaian warga untuk pemantauan dan pencegahan praktik perjudian daring maupun penipuan digital",
    },
    {
        "lokasi": "SEKITAR TUGU BINTANG JATISRONO",
        "koordinat": "(-7.8272791, 111.1287683)",
        "pertimbangan": "Lokasi berkumpulnya masyarakat dan pemuda guna deteksi dini serta pencegahan akses judi daring",
    },
    {
        "lokasi": "WILAYAH DESA JATISRONO",
        "koordinat": "(-7.8265000, 111.1254000)",
        "pertimbangan": "Pemantauan aktivitas masyarakat dan sosialisasi pencegahan kejahatan penipuan di ruang digital",
    },
    {
        "lokasi": "SEKITAR TERMINAL JATISRONO",
        "koordinat": "(-7.8278500, 111.1291000)",
        "pertimbangan": "Area publik yang ramai aktivitas warga sehingga memerlukan pengawasan terhadap potensi perjudian",
    },
]

def kirim_notif_telegram(pesan, foto_path=None):
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    try:
        if foto_path and os.path.exists(foto_path):
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
            with open(foto_path, "rb") as f:
                requests.post(url, data={"chat_id": TG_CHAT_ID, "caption": pesan[:1000]}, files={"photo": f}, timeout=20)
        else:
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": TG_CHAT_ID, "text": pesan[:4000]}, timeout=20)
    except Exception as e:
        print("Gagal kirim ke Telegram:", e)

def scan_semua_foto_drive(page):
    folder_id = FOLDER_UTAMA_URL.rstrip("/").split("/")[-1].split("?")[0]
    embed_url = f"https://drive.google.com/embeddedfolderview?id={folder_id}#list"

    file_links = []
    try:
        res = requests.get(embed_url, timeout=20)
        ids = re.findall(r"/file/d/([a-zA-Z0-9_-]{25,})/", res.text)
        if not ids:
            ids = re.findall(r'id="entry-([a-zA-Z0-9_-]{25,})"', res.text)
        seen = set()
        for fid in ids:
            if fid != folder_id and fid not in seen:
                seen.add(fid)
                file_links.append(f"https://drive.google.com/file/d/{fid}/view?usp=drivesdk")

        if not file_links:
            page.goto(FOLDER_UTAMA_URL, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            html = page.content()
            ids2 = re.findall(r'data-id="([a-zA-Z0-9_-]{25,})"', html)
            for fid in ids2:
                if fid != folder_id and fid not in seen:
                    seen.
