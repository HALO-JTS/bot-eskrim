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

NAMA_PELAPOR = "AIPDA EKO HERIYANTO ANC"
FOLDER_URL_RESKRIM = "https://drive.google.com/drive/folders/1q2wd72u-Hx3cEcMe2aBCykG8HjtuyBO2"
DEFAULT_LINK = "https://drive.google.com/file/d/17KmVFmPU-OZk0dBdbVgF7AZ6ayhGWPyl/view?usp=drivesdk"
TANGGAL_PATOKAN = date(2026, 10, 28)

# ==========================================================
# 1. VARIASI RUTE PATROLI RESERSE (QW1.9) & LOKASI JATISRONO
# ==========================================================
DAFTAR_RUTE_RESKRIM = [
    "MAKO POLSEK - PASAR JATISRONO - BRI - BPD - SPBU JATISRONO - MAKO",
    "MAKO POLSEK - SIMPANG EMPAT TERMINAL - BNI - MANDIRI - PASAR - MAKO",
    "MAKO POLSEK - TUGU BINTANG - PASAR JATISRONO - PERBANKAN - SPBU - MAKO",
    "MAKO POLSEK - SPBU JATISRONO - BRI - MANDIRI - PASAR JATISRONO - MAKO",
    "MAKO POLSEK - JALAN RAYA JATISRONO - OBJEK VITAL PERBANKAN - PASAR - MAKO",
]

DAFTAR_LOKASI_UMUM = [
    {"lokasi": "PASAR JATISRONO, KEC. JATISRONO", "koordinat": "(-7.8273937, 111.1285440)"},
    {"lokasi": "JALAN SEKITAR PASAR JATISRONO", "koordinat": "(-7.8274594, 111.1289731)"},
    {"lokasi": "TUGU BINTANG JATISRONO", "koordinat": "(-7.8272791, 111.1287683)"},
    {"lokasi": "JALAN SEKITAR SPBU JATISRONO", "koordinat": "(-7.8296862, 111.1607271)"},
]

LOKASI_MAKO = {
    "lokasi": "MAKO POLSEK JATISRONO, KEC. JATISRONO",
    "koordinat": "(-7.8273937, 111.1285440)"
}

LOKASI_SPBU = {
    "lokasi": "SPBU JATISRONO, KEC. JATISRONO",
    "koordinat": "(-7.8296862, 111.1607271)"
}

# ==========================================================
# 2. DAFTAR 8 KEGIATAN HARIAN RESKRIM
# ==========================================================
DAFTAR_KEGIATAN_RESKRIM = [
    {
        "kode": "QW1.9",
        "tab": "Ruang Publik Aman",
        "nama": "Patroli siaga reserse (Pagar)"
    },
    {
        "kode": "QW3.1",
        "tab": "Bersih Judi Daring dan Penipuan Digital",
        "nama": "Penegakan hukum judi dan penipuan di ruang digital"
    },
    {
        "kode": "QW5.1",
        "tab": "Perkara Terlacak, SP2HP Pasti",
        "nama": "SP2HP berkala kepada pelapor"
    },
    {
        "kode": "QW5.2",
        "tab": "Perkara Terlacak, SP2HP Pasti",
        "nama": "Layanan informasi perkara"
    },
    {
        "kode": "QW5.3",
        "tab": "Perkara Terlacak, SP2HP Pasti",
        "nama": "Gelar perkara atas pengaduan masyarakat"
    },
    {
        "kode": "QW5.4",
        "tab": "Perkara Terlacak, SP2HP Pasti",
        "nama": "Keadilan restoratif untuk perkara ringan"
    },
    {
        "kode": "QW8.1",
        "tab": "KUHP/KUHAP Siap, Penyidikan Berbasis Ilmiah",
        "nama": "Penanganan BBM ilegal dan kejahatan ekonomi"
    },
    {
        "kode": "QW8.2",
        "tab": "KUHP/KUHAP Siap, Penyidikan Berbasis Ilmiah",
        "nama": "Penanganan TPPO, korupsi, penyelundupan, pencucian uang, dan kejahatan lainnya"
    },
]

def kirim_notif_telegram(pesan, foto_path=None):
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    daftar_chat_id = [cid.strip() for cid in TG_CHAT_ID.split(",") if cid.strip()]
    for cid in daftar_chat_id:
        try:
            if foto_path and os.path.exists(foto_path):
                url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
                with open(foto_path, "rb") as f:
                    requests.post(url, data={"chat_id": cid, "caption": pesan[:1000]}, files={"photo": f}, timeout=20)
            else:
                url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
                requests.post(url, data={"chat_id": cid, "text": pesan[:4000]}, timeout=20)
        except Exception as e:
            print(f"Gagal kirim ke Telegram ({cid}):", e)

def ambil_8_foto_harian(page, folder_url):
    jumlah_giat = len(DAFTAR_KEGIATAN_RESKRIM)
    wib_sekarang = datetime.now(timezone(timedelta(hours=7))).date()
    selisih_hari = max(0, (wib_sekarang - TANGGAL_PATOKAN).days)

    kode_utama = folder_url.rstrip("/").split("/")[-1].split("?")[0]
    embed_url = f"https://drive.google.com/embeddedfolderview?id={kode_utama}#list"

    file_links = []
    seen = set()
    try:
        res = requests.get(embed_url, timeout=20)
        ids = re.findall(r"/file/d/([a-zA-Z0-9_-]{25,})/", res.text)
        if not ids:
            ids = re.findall(r'id="entry-([a-zA-Z0-9_-]{25,})"', res.text)

        for item_id in ids:
            if item_id != kode_utama and item_id not in seen:
                seen.add(item_id)
                file_links.append(f"https://drive.google.com/file/d/{item_id}/view?usp=drivesdk")

        if not file_links:
            page.goto(embed_url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            html = page.content()
            ids2 = re.findall(r"/file/d/([a-zA-Z0-9_-]{25,})/", html)
            if not ids2:
                ids2 = re.findall(r'id="entry-([a-zA-Z0-9_-]{25,})"', html)
            for item_id in ids2:
                if item_id != kode_utama and item_id not in seen:
                    seen.add(item_id)
                    file_links.append(f"https://drive.google.com/file/d/{item_id}/view?usp=drivesdk")
    except Exception as e:
        print("Gagal memindai folder Google Drive:", e)

    if file_links:
        total_foto = len(file_links)
        base_idx = selisih_hari * jumlah_giat
        hasil_foto = []
        for i in range(jumlah_giat):
            idx_terpilih = (base_idx + i) % total_foto
            hasil_foto.append((file_links[idx_terpilih], idx_terpilih + 1, total_foto))
        return hasil_foto

    return [(DEFAULT_LINK, i + 1, 1) for i in range(jumlah_giat)]

def tutup_saran_jika_ada(page):
    """Menutup kotak Saran atau keluhan 1 (tombol ×) tanpa menutup sub-kegiatan utama."""
    try:
        tombol_x = page.locator("xpath=//*[contains(text(), 'Saran atau keluhan')]/following::button[normalize-space()='×'][1]")
        if tombol_x.count() > 0 and tombol_x.first.is_visible():
            tombol_x.first.scroll_into_view_if_needed()
            tombol_x.first.click()
            page.wait_for_timeout(500)
    except Exception:
        pass

def klik_jam_sekarang(page):
    try:
        btn_jam = page.get_by_role("button", name="Isi jam sekarang")
        for i in range(btn_jam.count()):
            if btn_jam.nth(i).is_visible():
                btn_jam.nth(i).scroll_into_view_if_needed()
                btn_jam.nth(i).click()
                page.wait_for_timeout(500)
    except Exception:
        pass

def isi_lokasi_dan_koordinat(page, nama_lokasi, titik_koordinat):
    try:
        inp_tempat = page.locator("input[placeholder*='Nama tempat']")
        for i in range(inp_tempat.count()):
            if inp_tempat.nth(i).is_visible():
                inp_tempat.nth(i).scroll_into_view_if_needed()
                inp_tempat.nth(i).fill(nama_lokasi)

        inp_koord = page.locator("input[placeholder*='Tempel koordinat']")
        for i in range(inp_koord.count()):
            if inp_koord.nth(i).is_visible():
                inp_koord.nth(i).scroll_into_view_if_needed()
                inp_koord.nth(i).fill(titik_koordinat)
    except Exception:
        pass

def pilih_alasan_dropdown(page, preferensi_teks=""):
    try:
        selects = page.locator("select")
        if selects.count() > 1:
            dropdown = selects.nth(1)
            dropdown.scroll_into_view_if_needed()
            if preferensi_teks and dropdown.locator("option", has_text=preferensi_teks).count() > 0:
                teks_opsi = dropdown.locator("option", has_text=preferensi_teks).first.text_content().strip()
                dropdown.select_option(label=teks_opsi)
            else:
                dropdown.select_option(index=1)
            page.wait_for_timeout(600)
    except Exception:
        pass

def isi_angka_kosong_dengan_nol(page):
    """Mengisi semua kotak input angka yang masih kosong dengan '0' tanpa mengubah angka '1' pada jenis kegiatan."""
    try:
        num_inputs = page.locator("input[type='number']")
        for i in range(num_inputs.count()):
            el = num_inputs.nth(i)
            if el.is_visible():
                val = (el.input_value() or "").strip()
                if val == "":
                    el.scroll_into_view_if_needed()
                    el.fill("0")
    except Exception:
        pass

def isi_link_foto_drive(page, link_foto):
    try:
        inputs_drive = page.locator("input[placeholder*='Google Drive'], input[placeholder*='drive.google.com']")
        for i in range(inputs_drive.count()):
            if inputs_drive.nth(i).is_visible():
                inputs_drive.nth(i).scroll_into_view_if_needed()
                inputs_drive.nth(i).fill(link_foto)
    except Exception:
        pass

def klik_tetap_kirim_jika_ada(page):
    try:
        btn_tetap = page.get_by_role("button", name="Tetap kirim")
        if btn_tetap.count() > 0 and btn_tetap.first.is_visible():
            btn_tetap.first.scroll_into_view_if_needed()
            btn_tetap.first.click()
            page.wait_for_timeout(3000)
    except Exception:
        pass

def aktifkan_sub_kegiatan_plus(page, teks_jenis, teks_header_muncul):
    """Menekan tombol '+' pada jenis kegiatan jika sub-kotak isiannya belum muncul di layar."""
    try:
        if page.get_by_text(teks_header_muncul).count() == 0:
            btn_plus = page.locator(f"xpath=//*[contains(text(), '{teks_jenis}')]/following::button[normalize-space()='+'][1]")
            if btn_plus.count() > 0:
                btn_plus.first.scroll_into_view_if_needed()
                btn_plus.first.click()
                page.wait_for_timeout(1500)
    except Exception as e:
        print(f"Info klik plus {teks_jenis}:", e)

def jalankan_robot_reskrim():
    kirim_notif_telegram(
        f"🤖 Robot Reskrim Polsek Jatisrono mulai berjalan otomatis...\n"
        f"👮 Pelapor: {NAMA_PELAPOR}\n"
        f"📋 Target: 8 Kegiatan Dirreskrimum / Kasat Reskrim"
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
            delapan_foto = ambil_8_foto_harian(page, FOLDER_URL_RESKRIM)

            page.goto("https://poskopbm.polri.go.id/input", timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            # 1. Login jika diminta
            if page.locator("input[type='password']").count() > 0:
                page.locator("input[type='email'], input[type='text']").first.fill(EMAIL)
                page.locator("input[type='password']").first.fill(PASSWORD)
                page.get_by_role("button", name="Masuk").click()
                page.wait_for_timeout(5000)

            # 2. Isi Identitas & Pilih Jabatan Dirreskrimum / Kasat Reskrim (8 kegiatan)
            page.get_by_label("Nama dan pangkat pelapor").fill(NAMA_PELAPOR)
            select_jabatan = page.locator("select").first
            opsi_reskrim = select_jabatan.locator("option", has_text="Reskrim").first
            teks_jabatan = (opsi_reskrim.text_content() or "").strip()
            select_jabatan.select_option(label=teks_jabatan)
            page.wait_for_timeout(2500)

            # 3. Loop Eksekusi 8 Kegiatan
            for idx, item in enumerate(DAFTAR_KEGIATAN_RESKRIM):
                kode = item["kode"]
                nama_tab = item["tab"]
                nama_giat = item["nama"]
                link_foto, no_foto, tot_foto = delapan_foto[idx]

                # Klik Tab Quick Wins jika sub-kegiatan belum terlihat di layar
                if not page.get_by_text(kode).first.is_visible():
                    tab_el = page.locator("button", has_text=nama_tab).last
                    tab_el.scroll_into_view_if_needed()
                    tab_el.click()
                    page.wait_for_timeout(1500)

                # Klik sub-kegiatan berdasarkan kodenya (QW1.9, QW3.1, dst.)
                giat_el = page.get_by_text(kode).last
                giat_el.scroll_into_view_if_needed()
                giat_el.click()
                page.wait_for_timeout(2500)

                # ======================================================
                # A. LOGIKA KHUSUS QW1.9 (PATROLI SIAGA RESERSE)
                # ======================================================
                if kode == "QW1.9":
                    rute_pilihan = random.choice(DAFTAR_RUTE_RESKRIM)
                    inp_rute = page.locator("input[placeholder*='Jalan, kecamatan']")
                    if inp_rute.count() > 0:
                        inp_rute.first.scroll_into_view_if_needed()
                        inp_rute.first.fill(rute_pilihan)

                    pilih_alasan_dropdown(page, "Rawan kejahatan")
                    klik_jam_sekarang(page)

                    btn_tidak_ada = page.get_by_role("button", name="Tidak ada", exact=True)
                    if btn_tidak_ada.count() > 0:
                        btn_tidak_ada.first.scroll_into_view_if_needed()
                        btn_tidak_ada.first.click()
                        page.wait_for_timeout(500)

                    tutup_saran_jika_ada(page)
                    isi_link_foto_drive(page, link_foto)

                # ======================================================
                # B. LOGIKA KHUSUS QW3.1 (JUDI DARING & PENIPUAN DIGITAL)
                # ======================================================
                elif kode == "QW3.1":
                    paket_lok = random.choice(DAFTAR_LOKASI_UMUM)
                    tutup_saran_jika_ada(page)
                    aktifkan_sub_kegiatan_plus(page, "Kegiatan penipuan digital", "KEGIATAN PENIPUAN DIGITAL 1")

                    isi_lokasi_dan_koordinat(page, paket_lok["lokasi"], paket_lok["koordinat"])
                    klik_jam_sekarang(page)
                    pilih_alasan_dropdown(page, "Jadwal rutin satuan")
                    isi_angka_kosong_dengan_nol(page)
                    isi_link_foto_drive(page, link_foto)

                # ======================================================
                # C. LOGIKA KHUSUS QW5.1, QW5.2, QW5.3, QW5.4
                # ======================================================
                elif kode in ["QW5.1", "QW5.2", "QW5.3", "QW5.4"]:
                    tutup_saran_jika_ada(page)
                    isi_lokasi_dan_koordinat(page, LOKASI_MAKO["lokasi"], LOKASI_MAKO["koordinat"])
                    klik_jam_sekarang(page)
                    isi_angka_kosong_dengan_nol(page)
                    isi_link_foto_drive(page, link_foto)

                    # Tutup entri Perkara 1 / Layanan 1 / Pengaduan 1 jika ada tombol Tutup
                    try:
                        btn_tutup_entri = page.locator("xpath=//*[contains(text(), 'Perkara 1') or contains(text(), 'Layanan 1') or contains(text(), 'Pengaduan 1')]/following::button[normalize-space()='×'][1]")
                        if btn_tutup_entri.count() > 0 and btn_tutup_entri.first.is_visible():
                            btn_tutup_entri.first.scroll_into_view_if_needed()
                            btn_tutup_entri.first.click()
                            page.wait_for_timeout(500)
                    except Exception:
                        pass

                    # Klik tombol "Tidak" pada "Apakah satuan Anda menangani penyidikan perkara?"
                    btn_tidak = page.get_by_role("button", name="Tidak", exact=True)
                    if btn_tidak.count() > 0:
                        btn_tidak.first.scroll_into_view_if_needed()
                        btn_tidak.first.click()
                        page.wait_for_timeout(500)

                # ======================================================
                # D. LOGIKA KHUSUS QW8.1 (BBM/LPG ILEGAL & EKONOMI)
                # ======================================================
                elif kode == "QW8.1":
                    tutup_saran_jika_ada(page)
                    aktifkan_sub_kegiatan_plus(page, "Kegiatan BBM/LPG ilegal", "KEGIATAN BBM/LPG ILEGAL 1")

                    isi_lokasi_dan_koordinat(page, LOKASI_SPBU["lokasi"], LOKASI_SPBU["koordinat"])
                    klik_jam_sekarang(page)

                    # Pilih kondisi pasokan "Normal"
                    btn_normal = page.get_by_role("button", name="Normal", exact=True)
                    if btn_normal.count() > 0:
                        btn_normal.first.scroll_into_view_if_needed()
                        btn_normal.first.click()
                        page.wait_for_timeout(400)

                    isi_angka_kosong_dengan_nol(page)
                    isi_link_foto_drive(page, link_foto)

                # ======================================================
                # E. LOGIKA KHUSUS QW8.2 (TPPO, KORUPSI, PREMANISME)
                # ======================================================
                elif kode == "QW8.2":
                    paket_lok = random.choice(DAFTAR_LOKASI_UMUM)
                    tutup_saran_jika_ada(page)
                    aktifkan_sub_kegiatan_plus(page, "Kegiatan kejahatan terkait premanisme", "KEGIATAN KEJAHATAN TERKAIT PREMANISME 1")

                    isi_lokasi_dan_koordinat(page, paket_lok["lokasi"], paket_lok["koordinat"])
                    klik_jam_sekarang(page)
                    isi_angka_kosong_dengan_nol(page)
                    isi_link_foto_drive(page, link_foto)

                # Klik Kirim laporan
                page.wait_for_timeout(1000)
                btn_kirim = page.get_by_role("button", name="Kirim laporan")
                btn_kirim.scroll_into_view_if_needed()
                btn_kirim.click()
                page.wait_for_timeout(2000)

                klik_tetap_kirim_jika_ada(page)
                page.wait_for_timeout(4000)

                btn_kirim.scroll_into_view_if_needed()
                ss_path = f"bukti_{kode.replace('.', '_')}.png"
                page.screenshot(path=ss_path)
                kirim_notif_telegram(
                    f"✅ Laporan Reskrim {kode} berhasil dikirim!\n\n"
                    f"📌 Kegiatan: {nama_giat}\n"
                    f"👮 Pelapor: {NAMA_PELAPOR}\n"
                    f"📸 Foto ke-{no_foto} dari {tot_foto}\n"
                    f"🔗 Link: {link_foto}",
                    ss_path
                )

        except Exception as e:
            err_ss = "error_reskrim.png"
            try:
                page.screenshot(path=err_ss)
                kirim_notif_telegram(f"⚠️ Gagal mengirim laporan Reskrim:\n{str(e)}", err_ss)
            except Exception:
                kirim_notif_telegram(f"⚠️ Gagal membuka web Reskrim:\n{str(e)}")
        finally:
            browser.close()

if __name__ == "__main__":
    jalankan_robot_reskrim()
