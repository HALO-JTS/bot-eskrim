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
    """Memindai 1 folder Google Drive dan mengambil seluruh daftar link foto di dalamnya."""
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
                    seen.add(fid)
                    file_links.append(f"https://drive.google.com/file/d/{fid}/view?usp=drivesdk")
    except Exception as e:
        print("Gagal scan folder utama:", e)

    return file_links

def pilih_foto_kegiatan(daftar_link, urutan_giat):
    """Memilih foto secara bergilir untuk masing-masing dari 8 kegiatan."""
    if not daftar_link:
        return DEFAULT_LINK, 1, 1
    wib_today = datetime.now(timezone(timedelta(hours=7))).date()
    selisih_hari = max(0, (wib_today - TANGGAL_PATOKAN).days)
    idx = (selisih_hari * 8 + urutan_giat) % len(daftar_link)
    return daftar_link[idx], idx + 1, len(daftar_link)

def tutup_saran_jika_ada(page):
    try:
        tombol_x = page.locator("button:has-text('×')")
        for i in range(tombol_x.count()):
            if tombol_x.nth(i).is_visible():
                tombol_x.nth(i).click()
                page.wait_for_timeout(500)
    except Exception:
        pass

def isi_semua_angka_nol(page):
    inputs_num = page.locator("input[type='number']")
    for i in range(inputs_num.count()):
        if inputs_num.nth(i).is_visible():
            inputs_num.nth(i).fill("0")
    page.wait_for_timeout(500)

def buka_tab_dan_kegiatan(page, teks_tab, nama_giat):
    seksi_dua = page.get_by_text("2. PILIH QUICK WINS DAN KEGIATAN").first
    if seksi_dua.is_visible():
        seksi_dua.scroll_into_view_if_needed()

    tab = page.get_by_text(teks_tab).first
    tab.scroll_into_view_if_needed()
    tab.click()
    page.wait_for_timeout(1500)

    giat = page.get_by_text(nama_giat, exact=True).last
    giat.scroll_into_view_if_needed()
    giat.click()
    page.wait_for_timeout(2500)

    inp_pejabat = page.get_by_label("Nama dan pangkat pejabat pelaksana")
    inp_pejabat.scroll_into_view_if_needed()
    inp_pejabat.fill(NAMA_KANIT_RESKRIM)
    page.wait_for_timeout(500)

def kirim_dan_screenshot(page, kode, nama_giat, link_foto, no_foto, tot_foto, info_tambahan=""):
    tutup_saran_jika_ada(page)

    inputs_drive = page.locator("input[placeholder*='drive.google.com']")
    for i in range(inputs_drive.count()):
        if inputs_drive.nth(i).is_visible():
            inputs_drive.nth(i).fill(link_foto)
    page.wait_for_timeout(1000)

    btn_kirim = page.get_by_role("button", name="Kirim laporan")
    btn_kirim.scroll_into_view_if_needed()
    btn_kirim.click()
    page.wait_for_timeout(5000)

    ss_path = f"bukti_{kode.replace('.', '_')}.png"
    page.screenshot(path=ss_path)
    teks_tambahan = f"{info_tambahan}\n" if info_tambahan else ""
    kirim_notif_telegram(
        f"✅ Laporan Kanit Reskrim {kode} berhasil dikirim!\n\n"
        f"📌 Kegiatan: {nama_giat}\n"
        f"{teks_tambahan}"
        f"👮 Pelapor & Pelaksana: {NAMA_KANIT_RESKRIM}\n"
        f"📸 Foto ke-{no_foto} dari {tot_foto}\n"
        f"🔗 Link: {link_foto}",
        ss_path
    )

def jalankan_robot_reskrim():
    wib_sekarang = datetime.now(timezone(timedelta(hours=7)))
    nama_hari = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"][wib_sekarang.weekday()]

    kirim_notif_telegram(
        f"🤖 Robot Kanit Reskrim Jatisrono mulai berjalan...\n"
        f"📅 Hari: {nama_hari}, {wib_sekarang.strftime('%d-%m-%Y')}\n"
        f"👮 Pelapor: {NAMA_KANIT_RESKRIM}"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = browser.new_context(
            viewport={"width": 412, "height": 915},
            ignore_https_errors=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )
        page = context.new_page()

        try:
            # Pindai 1 folder utama untuk dipakai oleh 8 kegiatan
            daftar_foto = scan_semua_foto_drive(page)

            page.goto("https://poskopbm.polri.go.id/input", timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            if page.locator("input[type='password']").count() > 0:
                page.locator("input[type='email'], input[type='text']").first.fill(EMAIL)
                page.locator("input[type='password']").first.fill(PASSWORD)
                page.get_by_role("button", name="Masuk").click()
                page.wait_for_timeout(5000)

            # 1. CARA MEMILIH KEGIATAN DAN IDENTITAS LAPORAN
            page.get_by_label("Nama dan pangkat pelapor").fill(NAMA_KANIT_RESKRIM)
            page.locator("select").first.select_option(label="Kanit Reskrim (8 kegiatan)")
            page.wait_for_timeout(2000)

            # ==========================================================
            # 1. QW1.9 PATROLI SIAGA RESERSE (PAGAR)
            # ==========================================================
            rute = random.choice(DAFTAR_RUTE_RESERSE)
            alasan_rute = random.choice(ALASAN_RUTE_RESERSE)
            buka_tab_dan_kegiatan(page, "Ruang Publik Aman", "Patroli siaga reserse (Pagar)")
            page.get_by_label("Rute patroli").fill(rute)
            page.locator("textarea[placeholder*='Alasan rute dipilih']").first.fill(alasan_rute)
            link, no, tot = pilih_foto_kegiatan(daftar_foto, 0)
            kirim_dan_screenshot(page, "QW1.9", "Patroli siaga reserse (Pagar)", link, no, tot, f"🛣️ Rute: {rute}")

            # ==========================================================
            # 2. QW3.1 PENEGAKAN HUKUM JUDI DAN PENIPUAN DI RUANG DIGITAL
            # ==========================================================
            paket_judi = random.choice(PAKET_LOKASI_QW3_1)
            buka_tab_dan_kegiatan(page, "Bersih Judi Daring dan Penipuan Digital", "Penegakan hukum judi dan penipuan di ruang digital")
            tutup_saran_jika_ada(page)
            page.locator("input[placeholder*='Nama tempat']").first.fill(paket_judi["lokasi"])
            page.locator("input[placeholder*='Tempel koordinat']").first.fill(paket_judi["koordinat"])
            page.locator("textarea[placeholder*='Alasan lokasi dipilih']").first.fill(paket_judi["pertimbangan"])
            isi_semua_angka_nol(page)
            link, no, tot = pilih_foto_kegiatan(daftar_foto, 1)
            kirim_dan_screenshot(page, "QW3.1", "Penegakan hukum judi dan penipuan di ruang digital", link, no, tot, f"📍 Lokasi: {paket_judi['lokasi']}")

            # ==========================================================
            # 3. QW5.1 SP2HP BERKALA KEPADA PELAPOR
            # ==========================================================
            buka_tab_dan_kegiatan(page, "Perkara Terlacak, SP2HP Pasti", "SP2HP berkala kepada pelapor")
            tutup_saran_jika_ada(page)
            isi_semua_angka_nol(page)
            link, no, tot = pilih_foto_kegiatan(daftar_foto, 2)
            kirim_dan_screenshot(page, "QW5.1", "SP2HP berkala kepada pelapor", link, no, tot)

            # ==========================================================
            # 4. QW5.2 LAYANAN INFORMASI PERKARA
            # ==========================================================
            buka_tab_dan_kegiatan(page, "Perkara Terlacak, SP2HP Pasti", "Layanan informasi perkara")
            tutup_saran_jika_ada(page)
            isi_semua_angka_nol(page)
            link, no, tot = pilih_foto_kegiatan(daftar_foto, 3)
            kirim_dan_screenshot(page, "QW5.2", "Layanan informasi perkara", link, no, tot)

            # ==========================================================
            # 5. QW5.3 GELAR PERKARA ATAS PENGADUAN WARGA
            # ==========================================================
            buka_tab_dan_kegiatan(page, "Perkara Terlacak, SP2HP Pasti", "Gelar perkara atas pengaduan warga")
            tutup_saran_jika_ada(page)
            isi_semua_angka_nol(page)
            link, no, tot = pilih_foto_kegiatan(daftar_foto, 4)
            kirim_dan_screenshot(page, "QW5.3", "Gelar perkara atas pengaduan warga", link, no, tot)

            # ==========================================================
            # 6. QW5.4 KEADILAN RESTORATIF UNTUK PERKARA RINGAN
            # ==========================================================
            buka_tab_dan_kegiatan(page, "Perkara Terlacak, SP2HP Pasti", "Keadilan restoratif untuk perkara ringan")
            tutup_saran_jika_ada(page)
            isi_semua_angka_nol(page)
            link, no, tot = pilih_foto_kegiatan(daftar_foto, 5)
            kirim_dan_screenshot(page, "QW5.4", "Keadilan restoratif untuk perkara ringan", link, no, tot)

            # ==========================================================
            # 7. QW8.1 PENANGANAN BBM ILEGAL DAN KEJAHATAN EKONOMI
            # ==========================================================
            buka_tab_dan_kegiatan(page, "KUHP/KUHAP Siap, Penyidikan Berbasis Ilmiah", "Penanganan BBM ilegal dan kejahatan ekonomi")
            tutup_saran_jika_ada(page)
            page.get_by_role("button", name="Normal", exact=True).click()
            isi_semua_angka_nol(page)
            link, no, tot = pilih_foto_kegiatan(daftar_foto, 6)
            kirim_dan_screenshot(page, "QW8.1", "Penanganan BBM ilegal dan kejahatan ekonomi", link, no, tot)

            # ==========================================================
            # 8. QW8.2 PENANGANAN TPPO, KORUPSI, PENYELUNDUPAN, DAN TPPU
            # ==========================================================
            buka_tab_dan_kegiatan(page, "KUHP/KUHAP Siap, Penyidikan Berbasis Ilmiah", "Penanganan TPPO, korupsi, penyelundupan, dan pencucian uang")
            tutup_saran_jika_ada(page)
            isi_semua_angka_nol(page)
            link, no, tot = pilih_foto_kegiatan(daftar_foto, 7)
            kirim_dan_screenshot(page, "QW8.2", "Penanganan TPPO, korupsi, penyelundupan, dan pencucian uang", link, no, tot)

        except Exception as e:
            err_ss = "error_reskrim.png"
            try:
                page.screenshot(path=err_ss)
                kirim_notif_telegram(f"⚠️ Gagal mengirim laporan Kanit Reskrim:\n{str(e)}", err_ss)
            except Exception:
                kirim_notif_telegram(f"⚠️ Gagal mengirim laporan Kanit Reskrim:\n{str(e)}")
        finally:
            browser.close()

if __name__ == "__main__":
    jalankan_robot_reskrim()
