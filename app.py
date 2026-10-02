"""
ARONSAN - Teknoloji Takımı Platformu
Flask + SQLite tabanlı kurumsal site ve topluluk platformu.
"""
import os
import secrets
import sqlite3
import time
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get('ARONSAN_DB') or os.path.join(BASE_DIR, 'aronsan.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
IZINLI_UZANTILAR = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
RESMI_HESAP_ID = 1
VARSAYILAN_AVATAR = 'https://ui-avatars.com/api/?name=Aronsan&background=0D8ABC&color=fff'
TR_SAAT_FARKI = timedelta(hours=3)
CEVRIMICI_SURE = 120  # saniye
FIRMALAR = ['Aselsan', 'Baykar', 'Roketsan', 'TUSAŞ', 'HAVELSAN', 'MKE', 'STM', 'FNSS', 'Aronsan', 'Diğer']
PROJE_DURUMLARI = ['Planlama', 'Geliştirme', 'Test', 'Tamamlandı']
SOHBET_TEMALARI = {
    'default': 'Varsayılan (Lacivert)',
    'cyber': 'Cyberpunk (Neon Mor)',
    'sunset': 'Sunset (Gül Kurusu)',
    'emerald': 'Emerald (Zümrüt)',
    'ocean': 'Okyanus',
    'carbon': 'Karbon',
}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def _gizli_anahtar():
    if os.environ.get('ARONSAN_SECRET'):
        return os.environ['ARONSAN_SECRET']
    yol = os.path.join(BASE_DIR, '.secret_key')
    if os.path.exists(yol):
        with open(yol, encoding='utf-8') as f:
            return f.read().strip()
    anahtar = secrets.token_hex(32)
    with open(yol, 'w', encoding='utf-8') as f:
        f.write(anahtar)
    return anahtar


app = Flask(__name__)
app.secret_key = _gizli_anahtar()
app.config.update(
    UPLOAD_FOLDER=UPLOAD_FOLDER,
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
)

# Bellek içi "yazıyor..." durumu: (gonderen_id, alici_id) -> zaman
YAZIYOR = {}


# =========================================================
#  VERİTABANI
# =========================================================
def db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH, timeout=10)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def db_kapat(_exc):
    conn = g.pop('db', None)
    if conn is not None:
        conn.close()


def sorgu(sql, args=(), tek=False):
    rv = db().execute(sql, args).fetchall()
    if tek:
        return rv[0] if rv else None
    return rv


def calistir(sql, args=()):
    cur = db().execute(sql, args)
    db().commit()
    return cur


def simdi_utc():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')


def veritabani_hazirla():
    """Tabloları oluşturur, eksik kolonları ekler ve eski verileri onarır."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS kullanicilar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_soyad TEXT NOT NULL,
            eposta TEXT UNIQUE NOT NULL,
            sifre TEXT NOT NULL,
            yetki TEXT NOT NULL DEFAULT 'kullanici');
        CREATE TABLE IF NOT EXISTS projeler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            baslik TEXT NOT NULL, icerik TEXT NOT NULL, gorsel_url TEXT,
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS haberler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            firma_adi TEXT NOT NULL, baslik TEXT NOT NULL, icerik TEXT NOT NULL, gorsel_url TEXT,
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS ekip_uyeleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_soyad TEXT NOT NULL, departman TEXT NOT NULL, rutbe TEXT NOT NULL,
            gorsel_url TEXT, biyografi TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS haber_yorumlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            haber_id INTEGER NOT NULL, kullanici_ad TEXT NOT NULL, yorum TEXT NOT NULL,
            begeni INTEGER DEFAULT 0, tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS haber_begenileri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            haber_id INTEGER NOT NULL, kullanici_id INTEGER NOT NULL,
            UNIQUE(haber_id, kullanici_id));
        CREATE TABLE IF NOT EXISTS yorum_begenileri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            yorum_id INTEGER NOT NULL, kullanici_id INTEGER NOT NULL,
            UNIQUE(yorum_id, kullanici_id));
        CREATE TABLE IF NOT EXISTS haber_kayitlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            haber_id INTEGER NOT NULL, kullanici_id INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS takipciler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            takip_eden_id INTEGER NOT NULL, takip_edilen_id INTEGER NOT NULL,
            UNIQUE(takip_eden_id, takip_edilen_id));
        CREATE TABLE IF NOT EXISTS gonderiler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kullanici_id INTEGER NOT NULL, icerik TEXT NOT NULL, gorsel_url TEXT,
            begeni INTEGER DEFAULT 0, tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS gonderi_begenileri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gonderi_id INTEGER NOT NULL, kullanici_id INTEGER NOT NULL,
            UNIQUE(gonderi_id, kullanici_id));
        CREATE TABLE IF NOT EXISTS gonderi_yorumlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gonderi_id INTEGER NOT NULL, kullanici_id INTEGER NOT NULL, yorum TEXT NOT NULL,
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS mesajlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gonderen_id INTEGER NOT NULL, alici_id INTEGER NOT NULL, icerik TEXT NOT NULL,
            okundu INTEGER DEFAULT 0, tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS bildirimler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kullanici_id INTEGER NOT NULL, icerik TEXT NOT NULL, okundu INTEGER DEFAULT 0,
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS sohbet_ayarlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kullanici_id INTEGER NOT NULL, hedef_id INTEGER NOT NULL, tema TEXT, takma_ad TEXT);
        CREATE TABLE IF NOT EXISTS destek_talepleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kullanici_id INTEGER, ad_soyad TEXT, eposta TEXT, konu TEXT, mesaj TEXT NOT NULL,
            tur TEXT DEFAULT 'destek', durum TEXT DEFAULT 'acik',
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    ''')

    def kolon_ekle(tablo, kolon, tanim):
        mevcut = [r[1] for r in c.execute(f'PRAGMA table_info({tablo})')]
        if kolon not in mevcut:
            c.execute(f'ALTER TABLE {tablo} ADD COLUMN {kolon} {tanim}')

    kolon_ekle('kullanicilar', 'profil_fotografi', f"TEXT DEFAULT '{VARSAYILAN_AVATAR}'")
    kolon_ekle('kullanicilar', 'biyografi', "TEXT DEFAULT 'Savunma sanayii ve teknoloji tutkunu.'")
    kolon_ekle('kullanicilar', 'mavi_tik', 'INTEGER DEFAULT 0')
    kolon_ekle('kullanicilar', 'kapak_fotografi', 'TEXT')
    kolon_ekle('kullanicilar', 'unvan', 'TEXT')
    kolon_ekle('kullanicilar', 'konum', 'TEXT')
    kolon_ekle('kullanicilar', 'web_sitesi', 'TEXT')
    kolon_ekle('kullanicilar', 'kayit_tarihi', 'TEXT')
    kolon_ekle('kullanicilar', 'son_gorulme', 'TEXT')
    kolon_ekle('kullanicilar', 'mesaj_izni', "TEXT DEFAULT 'herkes'")
    kolon_ekle('kullanicilar', 'cevrimici_goster', 'INTEGER DEFAULT 1')
    kolon_ekle('haberler', 'goruntulenme', 'INTEGER DEFAULT 0')
    kolon_ekle('haberler', 'begeni', 'INTEGER DEFAULT 0')
    kolon_ekle('haber_yorumlari', 'kullanici_id', 'INTEGER')
    kolon_ekle('haber_yorumlari', 'ust_yorum_id', 'INTEGER')
    kolon_ekle('projeler', 'kategori', 'TEXT')
    kolon_ekle('projeler', 'durum', "TEXT DEFAULT 'Geliştirme'")
    kolon_ekle('ekip_uyeleri', 'kullanici_id', 'INTEGER')
    kolon_ekle('ekip_uyeleri', 'linkedin', 'TEXT')
    kolon_ekle('ekip_uyeleri', 'github', 'TEXT')
    kolon_ekle('mesajlar', 'okundu', 'INTEGER DEFAULT 0')
    kolon_ekle('mesajlar', 'gorsel_url', 'TEXT')
    kolon_ekle('mesajlar', 'silindi', 'INTEGER DEFAULT 0')
    kolon_ekle('mesajlar', 'tepki', 'TEXT')
    kolon_ekle('bildirimler', 'link', 'TEXT')
    kolon_ekle('bildirimler', 'gonderen_id', 'INTEGER')
    kolon_ekle('bildirimler', 'tur', "TEXT DEFAULT 'genel'")

    # --- Veri onarımları ---
    c.execute('UPDATE kullanicilar SET ad_soyad = TRIM(ad_soyad)')
    # Katılım tarihi bilinmeyen eski üyeler: ilk etkinlik tarihini kullan
    c.execute('''UPDATE kullanicilar SET kayit_tarihi = COALESCE(
                    (SELECT MIN(t) FROM (
                        SELECT MIN(tarih) AS t FROM mesajlar WHERE gonderen_id = kullanicilar.id
                        UNION ALL SELECT MIN(tarih) FROM gonderiler WHERE kullanici_id = kullanicilar.id
                        UNION ALL SELECT MIN(tarih) FROM haber_yorumlari WHERE TRIM(kullanici_ad) = TRIM(kullanicilar.ad_soyad))),
                    CURRENT_TIMESTAMP)
                 WHERE kayit_tarihi IS NULL''')
    c.execute(f"UPDATE kullanicilar SET profil_fotografi = '{VARSAYILAN_AVATAR}' "
              "WHERE profil_fotografi IS NULL OR profil_fotografi = ''")
    # Eski yorumlar isimle tutuluyordu -> kullanıcı id'sine bağla (mavi tik / profil linki için)
    c.execute('''UPDATE haber_yorumlari SET kullanici_id = (
                    SELECT k.id FROM kullanicilar k WHERE TRIM(k.ad_soyad) = TRIM(haber_yorumlari.kullanici_ad) LIMIT 1)
                 WHERE kullanici_id IS NULL''')
    # Beğeni sayaçlarını gerçek kayıtlardan yeniden hesapla (eksiye düşme hatası)
    c.execute('UPDATE haberler SET begeni = (SELECT COUNT(*) FROM haber_begenileri b WHERE b.haber_id = haberler.id)')
    c.execute('UPDATE haberler SET goruntulenme = COALESCE(goruntulenme, 0)')

    c.executescript('''
        CREATE INDEX IF NOT EXISTS ix_mesaj_cift ON mesajlar(gonderen_id, alici_id);
        CREATE INDEX IF NOT EXISTS ix_bildirim_k ON bildirimler(kullanici_id);
        CREATE INDEX IF NOT EXISTS ix_gonderi_k ON gonderiler(kullanici_id);
        CREATE INDEX IF NOT EXISTS ix_hyorum_h ON haber_yorumlari(haber_id);
        CREATE INDEX IF NOT EXISTS ix_gyorum_g ON gonderi_yorumlari(gonderi_id);
    ''')

    if c.execute('SELECT COUNT(*) FROM kullanicilar').fetchone()[0] == 0:
        c.execute("INSERT INTO kullanicilar (ad_soyad, eposta, sifre, yetki, mavi_tik) VALUES (?,?,?,?,1)",
                  ('Aronsan', 'admin@aronsan.com', generate_password_hash('123456'), 'personel'))
        print('Varsayılan yönetici oluşturuldu: admin@aronsan.com / 123456')
    conn.commit()
    conn.close()


veritabani_hazirla()


# =========================================================
#  YARDIMCILAR
# =========================================================
def sifre_dogrula(kayitli, girilen):
    if not kayitli:
        return False
    if kayitli.startswith(('scrypt:', 'pbkdf2:')):
        return check_password_hash(kayitli, girilen)
    return secrets.compare_digest(kayitli, girilen)  # eski düz metin şifreler


def _ts_parse(ts):
    if not ts:
        return None
    if isinstance(ts, datetime):
        return ts
    try:
        return datetime.strptime(str(ts)[:19], '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return None


AYLAR = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz',
         'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']


@app.template_filter('zaman_once')
def zaman_once(ts):
    dt = _ts_parse(ts)
    if not dt:
        return ''
    fark = (datetime.now(timezone.utc).replace(tzinfo=None) - dt).total_seconds()
    if fark < 60:
        return 'az önce'
    if fark < 3600:
        return f'{int(fark // 60)} dk önce'
    if fark < 86400:
        return f'{int(fark // 3600)} sa önce'
    if fark < 86400 * 7:
        return f'{int(fark // 86400)} gün önce'
    return tarih_tr(ts)


@app.template_filter('tarih_tr')
def tarih_tr(ts, saatli=False):
    dt = _ts_parse(ts)
    if not dt:
        return ''
    dt = dt + TR_SAAT_FARKI
    metin = f'{dt.day} {AYLAR[dt.month - 1]} {dt.year}'
    if saatli:
        metin += f' · {dt:%H:%M}'
    return metin


@app.template_filter('saat')
def saat(ts):
    dt = _ts_parse(ts)
    return (dt + TR_SAAT_FARKI).strftime('%H:%M') if dt else ''


@app.template_filter('sayi')
def sayi_kisalt(n):
    n = int(n or 0)
    if n >= 1_000_000:
        return f'{n / 1_000_000:.1f}M'.replace('.0', '')
    if n >= 1000:
        return f'{n / 1000:.1f}B'.replace('.0', '')
    return str(n)


def cevrimici_mi(k):
    if not k or not k['son_gorulme'] or not k['cevrimici_goster']:
        return False
    dt = _ts_parse(k['son_gorulme'])
    return bool(dt and (datetime.now(timezone.utc).replace(tzinfo=None) - dt).total_seconds() < CEVRIMICI_SURE)


def son_gorulme_metni(k):
    if not k or not k['cevrimici_goster']:
        return ''
    if cevrimici_mi(k):
        return 'Çevrimiçi'
    if k['son_gorulme']:
        return 'Son görülme ' + zaman_once(k['son_gorulme'])
    return ''


app.jinja_env.globals.update(cevrimici_mi=cevrimici_mi, son_gorulme_metni=son_gorulme_metni,
                             VARSAYILAN_AVATAR=VARSAYILAN_AVATAR, RESMI_HESAP_ID=RESMI_HESAP_ID,
                             FIRMALAR=FIRMALAR, PROJE_DURUMLARI=PROJE_DURUMLARI,
                             SOHBET_TEMALARI=SOHBET_TEMALARI)


def kullanici_json(k):
    return {
        'id': k['id'],
        'ad_soyad': k['ad_soyad'],
        'profil_fotografi': k['profil_fotografi'] or VARSAYILAN_AVATAR,
        'mavi_tik': bool(k['mavi_tik']),
        'yetki': k['yetki'] if 'yetki' in k.keys() else None,
        'cevrimici': cevrimici_mi(k) if 'son_gorulme' in k.keys() else False,
    }


def dosya_kaydet(dosya):
    """Yüklenen görseli benzersiz isimle kaydeder, URL döner. Dosya yoksa None."""
    if not dosya or not dosya.filename:
        return None
    uzanti = dosya.filename.rsplit('.', 1)[-1].lower() if '.' in dosya.filename else ''
    if uzanti not in IZINLI_UZANTILAR:
        raise ValueError('Sadece PNG, JPG, GIF veya WEBP görseller yüklenebilir.')
    ad = f'{datetime.now():%Y%m%d}_{uuid.uuid4().hex[:12]}.{uzanti}'
    dosya.save(os.path.join(app.config['UPLOAD_FOLDER'], ad))
    return '/static/uploads/' + ad


def bildirim_ekle(alici_id, icerik, link=None, gonderen_id=None, tur='genel'):
    if not alici_id or (gonderen_id and int(alici_id) == int(gonderen_id)):
        return
    db().execute('INSERT INTO bildirimler (kullanici_id, icerik, link, gonderen_id, tur) VALUES (?,?,?,?,?)',
                 (alici_id, icerik, link, gonderen_id, tur))


def json_hata(mesaj='İşlem için giriş yapmalısınız.', kod=401):
    return jsonify({'status': 'error', 'mesaj': mesaj}), kod


def giris_gerekli(f):
    @wraps(f)
    def sarici(*a, **kw):
        if not g.user:
            if request.path.startswith('/api/'):
                return json_hata()
            flash('Bu sayfayı görüntülemek için giriş yapmalısınız.', 'warning')
            return redirect(url_for('giris', next=request.path))
        return f(*a, **kw)
    return sarici


def personel_gerekli(f):
    @wraps(f)
    def sarici(*a, **kw):
        if not g.user or g.user['yetki'] != 'personel':
            if request.path.startswith('/api/'):
                return json_hata('Yetkiniz yok.', 403)
            flash('Bu alana erişim yetkiniz yok.', 'danger')
            return redirect(url_for('index'))
        return f(*a, **kw)
    return sarici


def csrf_token():
    if '_csrf' not in session:
        session['_csrf'] = secrets.token_hex(16)
    return session['_csrf']


app.jinja_env.globals['csrf_token'] = csrf_token


def guvenli_yonlendirme(hedef, varsayilan):
    if hedef and hedef.startswith('/') and not hedef.startswith('//'):
        return hedef
    return varsayilan


# =========================================================
#  İSTEK KANCALARI
# =========================================================
@app.before_request
def istek_oncesi():
    g.user = None
    if request.endpoint == 'static':
        return
    uid = session.get('kullanici_id')
    if uid:
        g.user = sorgu('SELECT * FROM kullanicilar WHERE id = ?', (uid,), tek=True)
        if not g.user:
            session.clear()
        elif time.time() - session.get('_sg', 0) > 45:
            calistir('UPDATE kullanicilar SET son_gorulme = ? WHERE id = ?', (simdi_utc(), uid))
            session['_sg'] = time.time()

    if request.method == 'POST':
        token = request.form.get('_csrf') or request.headers.get('X-CSRF-Token')
        if not token or token != session.get('_csrf'):
            if request.path.startswith('/api/'):
                return json_hata('Oturum doğrulaması başarısız. Sayfayı yenileyip tekrar deneyin.', 400)
            flash('Oturum doğrulaması başarısız oldu, lütfen tekrar deneyin.', 'danger')
            return redirect(request.referrer or url_for('index'))


@app.context_processor
def ortak_veriler():
    veri = dict(aktif_kullanici=g.get('user'), okunmamis_bildirim=0, okunmamis_mesaj=0)
    if g.get('user'):
        uid = g.user['id']
        veri['okunmamis_bildirim'] = sorgu('SELECT COUNT(*) FROM bildirimler WHERE kullanici_id = ? AND okundu = 0',
                                           (uid,), tek=True)[0]
        veri['okunmamis_mesaj'] = sorgu('SELECT COUNT(*) FROM mesajlar WHERE alici_id = ? AND okundu = 0 AND silindi = 0',
                                        (uid,), tek=True)[0]
    return veri


@app.errorhandler(404)
def hata_404(_e):
    if request.path.startswith('/api/'):
        return json_hata('Bulunamadı.', 404)
    return render_template('hata.html', kod=404, baslik='Sayfa bulunamadı',
                           aciklama='Aradığınız sayfa taşınmış, silinmiş ya da hiç var olmamış olabilir.'), 404


@app.errorhandler(413)
def hata_413(_e):
    flash('Dosya çok büyük. En fazla 16 MB yükleyebilirsiniz.', 'danger')
    return redirect(request.referrer or url_for('index'))


@app.errorhandler(500)
def hata_500(_e):
    if request.path.startswith('/api/'):
        return json_hata('Sunucu hatası.', 500)
    return render_template('hata.html', kod=500, baslik='Bir şeyler ters gitti',
                           aciklama='Sunucuda beklenmeyen bir hata oluştu. Lütfen biraz sonra tekrar deneyin.'), 500


# =========================================================
#  KURUMSAL SAYFALAR
# =========================================================
def haber_listesi_sql(where='', limit=''):
    return f'''SELECT h.*,
                (SELECT COUNT(*) FROM haber_yorumlari WHERE haber_id = h.id) AS yorum_sayisi,
                (SELECT COUNT(*) FROM haber_begenileri WHERE haber_id = h.id) AS begeni_sayisi
               FROM haberler h {where} ORDER BY h.id DESC {limit}'''


def gonderi_sql(where='', limit=''):
    return f'''SELECT g.*, k.ad_soyad AS yazar_ad, k.profil_fotografi AS yazar_foto, k.mavi_tik AS yazar_tik,
                (SELECT COUNT(*) FROM gonderi_begenileri WHERE gonderi_id = g.id) AS begeni_sayisi,
                (SELECT COUNT(*) FROM gonderi_yorumlari WHERE gonderi_id = g.id) AS yorum_sayisi,
                {('(SELECT COUNT(*) FROM gonderi_begenileri WHERE gonderi_id = g.id AND kullanici_id = %d)' % g.user['id']) if g.get('user') else '0'} AS begendim
               FROM gonderiler g JOIN kullanicilar k ON g.kullanici_id = k.id {where}
               ORDER BY g.id DESC {limit}'''


def istatistikler():
    s = {}
    for anahtar, tablo in [('proje', 'projeler'), ('haber', 'haberler'), ('uye', 'kullanicilar'),
                           ('gonderi', 'gonderiler'), ('ekip', 'ekip_uyeleri')]:
        s[anahtar] = sorgu(f'SELECT COUNT(*) FROM {tablo}', tek=True)[0]
    return s


def takip_onerileri(limit=5):
    if not g.user:
        return sorgu('SELECT * FROM kullanicilar ORDER BY mavi_tik DESC, id DESC LIMIT ?', (limit,))
    return sorgu('''SELECT k.*, (SELECT COUNT(*) FROM takipciler WHERE takip_edilen_id = k.id) AS takipci
                    FROM kullanicilar k WHERE k.id != ? AND k.id NOT IN
                    (SELECT takip_edilen_id FROM takipciler WHERE takip_eden_id = ?)
                    ORDER BY k.mavi_tik DESC, takipci DESC LIMIT ?''', (g.user['id'], g.user['id'], limit))


@app.route('/')
def index():
    return render_template('index.html',
                           haberler=sorgu(haber_listesi_sql(limit='LIMIT 6')),
                           projeler=sorgu('SELECT * FROM projeler ORDER BY id DESC LIMIT 3'),
                           gonderiler=sorgu(gonderi_sql(limit='LIMIT 4')),
                           ekip=sorgu('SELECT * FROM ekip_uyeleri ORDER BY id ASC LIMIT 4'),
                           istatistik=istatistikler())


@app.route('/haberler')
def haberler():
    firma = request.args.get('firma', '').strip()
    q = request.args.get('q', '').strip()
    kosul, args = [], []
    if firma:
        kosul.append('h.firma_adi = ?'); args.append(firma)
    if q:
        kosul.append('(h.baslik LIKE ? OR h.icerik LIKE ?)'); args += [f'%{q}%', f'%{q}%']
    where = ('WHERE ' + ' AND '.join(kosul)) if kosul else ''
    liste = sorgu(haber_listesi_sql(where), args)
    firmalar = [r[0] for r in sorgu('SELECT DISTINCT firma_adi FROM haberler ORDER BY firma_adi')]
    return render_template('haberler.html', haberler=liste, firmalar=firmalar, secili_firma=firma, q=q)


@app.route('/projeler')
def projeler():
    return render_template('projeler.html', projeler=sorgu('SELECT * FROM projeler ORDER BY id DESC'))


@app.route('/proje/<int:id>')
def proje_detay(id):
    proje = sorgu('SELECT * FROM projeler WHERE id = ?', (id,), tek=True)
    if not proje:
        abort(404)
    digerleri = sorgu('SELECT * FROM projeler WHERE id != ? ORDER BY id DESC LIMIT 3', (id,))
    return render_template('proje_detay.html', proje=proje, digerleri=digerleri)


@app.route('/ekibimiz')
def ekibimiz():
    personeller = sorgu('''SELECT e.*, k.mavi_tik, k.id AS hesap_id FROM ekip_uyeleri e
                           LEFT JOIN kullanicilar k ON e.kullanici_id = k.id ORDER BY e.id ASC''')
    departmanlar = sorted({p['departman'] for p in personeller if p['departman']})
    return render_template('ekibimiz.html', personeller=personeller, departmanlar=departmanlar)


@app.route('/ekip/<int:id>')
def uye_detay(id):
    personel = sorgu('''SELECT e.*, k.mavi_tik, k.id AS hesap_id, k.profil_fotografi AS hesap_foto
                        FROM ekip_uyeleri e LEFT JOIN kullanicilar k ON e.kullanici_id = k.id
                        WHERE e.id = ?''', (id,), tek=True)
    if not personel:
        return redirect(url_for('ekibimiz'))
    digerleri = sorgu('SELECT * FROM ekip_uyeleri WHERE id != ? ORDER BY id LIMIT 4', (id,))
    return render_template('uye_detay.html', personel=personel, digerleri=digerleri)


@app.route('/hakkimizda')
def hakkimizda():
    return render_template('hakkimizda.html', istatistik=istatistikler())


@app.route('/iletisim', methods=['GET', 'POST'])
def iletisim():
    if request.method == 'POST':
        ad = request.form.get('ad_soyad', '').strip()
        eposta = request.form.get('eposta', '').strip()
        konu = request.form.get('konu', '').strip()
        mesaj = request.form.get('mesaj', '').strip()
        if not (ad and eposta and mesaj):
            flash('Lütfen tüm zorunlu alanları doldurun.', 'danger')
        else:
            calistir('INSERT INTO destek_talepleri (kullanici_id, ad_soyad, eposta, konu, mesaj, tur) VALUES (?,?,?,?,?,?)',
                     (g.user['id'] if g.user else None, ad, eposta, konu, mesaj, 'iletisim'))
            flash('Mesajınız ekibimize ulaştı. En kısa sürede dönüş yapacağız.', 'success')
            return redirect(url_for('iletisim'))
    return render_template('iletisim.html')


@app.route('/ara')
def ara():
    q = request.args.get('q', '').strip()
    sonuc = {'kisiler': [], 'haberler': [], 'projeler': [], 'gonderiler': []}
    if q:
        like = f'%{q}%'
        sonuc['kisiler'] = sorgu('SELECT * FROM kullanicilar WHERE ad_soyad LIKE ? ORDER BY mavi_tik DESC LIMIT 20', (like,))
        sonuc['haberler'] = sorgu(haber_listesi_sql('WHERE h.baslik LIKE ? OR h.icerik LIKE ?'), (like, like))
        sonuc['projeler'] = sorgu('SELECT * FROM projeler WHERE baslik LIKE ? OR icerik LIKE ? ORDER BY id DESC', (like, like))
        sonuc['gonderiler'] = sorgu(gonderi_sql('WHERE g.icerik LIKE ?', 'LIMIT 20'), (like,))
    return render_template('ara.html', q=q, sonuc=sonuc)


# =========================================================
#  KİMLİK DOĞRULAMA
# =========================================================
def _oturum_ac(kullanici, hatirla=True):
    session.clear()
    session.permanent = hatirla
    session['kullanici_id'] = kullanici['id']
    csrf_token()


def _giris_dene(eposta, sifre, sadece_personel=False):
    k = sorgu('SELECT * FROM kullanicilar WHERE LOWER(eposta) = LOWER(?)', (eposta.strip(),), tek=True)
    if not k or not sifre_dogrula(k['sifre'], sifre):
        return None, 'E-posta adresi veya şifre hatalı.'
    if sadece_personel and k['yetki'] != 'personel':
        return None, 'Bu hesabın personel yetkisi bulunmuyor.'
    if not k['sifre'].startswith(('scrypt:', 'pbkdf2:')):
        calistir('UPDATE kullanicilar SET sifre = ? WHERE id = ?', (generate_password_hash(sifre), k['id']))
    return k, None


@app.route('/giris', methods=['GET', 'POST'])
def giris():
    if g.user:
        return redirect(url_for('index'))
    if request.method == 'POST':
        k, hata = _giris_dene(request.form.get('eposta', ''), request.form.get('sifre', ''))
        if hata:
            flash(hata, 'danger')
            return render_template('giris.html', eposta=request.form.get('eposta', ''))
        _oturum_ac(k, bool(request.form.get('hatirla')))
        flash(f'Tekrar hoş geldin, {k["ad_soyad"].split()[0]}!', 'success')
        return redirect(guvenli_yonlendirme(request.args.get('next'), url_for('akis')))
    return render_template('giris.html')


@app.route('/personel-giris', methods=['GET', 'POST'])
def personel_giris():
    if request.method == 'POST':
        k, hata = _giris_dene(request.form.get('eposta', ''), request.form.get('sifre', ''), sadece_personel=True)
        if hata:
            flash(hata, 'danger')
            return render_template('personel_giris.html', eposta=request.form.get('eposta', ''))
        _oturum_ac(k)
        flash('Yönetim paneline hoş geldiniz.', 'success')
        return redirect(url_for('admin'))
    return render_template('personel_giris.html')


@app.route('/kayit', methods=['GET', 'POST'])
def kayit():
    if g.user:
        return redirect(url_for('index'))
    if request.method == 'POST':
        ad = request.form.get('ad_soyad', '').strip()
        eposta = request.form.get('eposta', '').strip().lower()
        sifre = request.form.get('sifre', '')
        sifre2 = request.form.get('sifre_tekrar', sifre)
        hata = None
        if len(ad) < 2:
            hata = 'Lütfen geçerli bir ad soyad girin.'
        elif '@' not in eposta or '.' not in eposta.split('@')[-1]:
            hata = 'Lütfen geçerli bir e-posta adresi girin.'
        elif len(sifre) < 6:
            hata = 'Şifre en az 6 karakter olmalıdır.'
        elif sifre != sifre2:
            hata = 'Şifreler birbiriyle eşleşmiyor.'
        elif sorgu('SELECT 1 FROM kullanicilar WHERE LOWER(eposta) = ?', (eposta,), tek=True):
            hata = 'Bu e-posta adresiyle kayıtlı bir hesap zaten var.'
        if hata:
            flash(hata, 'danger')
            return render_template('kayit.html', ad_soyad=ad, eposta=eposta)
        foto = f'https://ui-avatars.com/api/?name={ad.replace(" ", "+")}&background=0D8ABC&color=fff&bold=true'
        cur = calistir('''INSERT INTO kullanicilar (ad_soyad, eposta, sifre, yetki, profil_fotografi, kayit_tarihi)
                          VALUES (?,?,?,?,?,CURRENT_TIMESTAMP)''',
                       (ad, eposta, generate_password_hash(sifre), 'kullanici', foto))
        yeni = sorgu('SELECT * FROM kullanicilar WHERE id = ?', (cur.lastrowid,), tek=True)
        # Resmi hesabı otomatik takip et + hoş geldin bildirimi
        if sorgu('SELECT 1 FROM kullanicilar WHERE id = ?', (RESMI_HESAP_ID,), tek=True):
            db().execute('INSERT OR IGNORE INTO takipciler (takip_eden_id, takip_edilen_id) VALUES (?,?)',
                         (yeni['id'], RESMI_HESAP_ID))
        bildirim_ekle(yeni['id'], "Aronsan topluluğuna hoş geldin! Profilini düzenleyerek başlayabilirsin.",
                      link='/hesap-ayarlari', gonderen_id=RESMI_HESAP_ID, tur='sistem')
        db().commit()
        _oturum_ac(yeni)
        flash('Hesabın oluşturuldu. Aramıza hoş geldin!', 'success')
        return redirect(url_for('akis'))
    return render_template('kayit.html')


@app.route('/cikis')
def cikis():
    session.clear()
    flash('Güvenli bir şekilde çıkış yaptınız.', 'info')
    return redirect(url_for('index'))


# =========================================================
#  PROFİL & HESAP
# =========================================================
@app.route('/profil')
def profil_kisayol():
    q = request.args.get('q', '').strip()
    if q:  # eski @etiket linkleri için
        k = sorgu('SELECT id FROM kullanicilar WHERE TRIM(ad_soyad) = ? LIMIT 1', (q,), tek=True)
        if k:
            return redirect(url_for('profil', id=k['id']))
        return redirect(url_for('ara', q=q))
    if g.user:
        return redirect(url_for('profil', id=g.user['id']))
    return redirect(url_for('giris'))


@app.route('/profil/<int:id>')
def profil(id):
    kisi = sorgu('SELECT * FROM kullanicilar WHERE id = ?', (id,), tek=True)
    if not kisi:
        abort(404)
    takipci_sayisi = sorgu('SELECT COUNT(*) FROM takipciler WHERE takip_edilen_id = ?', (id,), tek=True)[0]
    takip_edilen_sayisi = sorgu('SELECT COUNT(*) FROM takipciler WHERE takip_eden_id = ?', (id,), tek=True)[0]
    takip_durumu = beni_takip_ediyor = False
    if g.user:
        takip_durumu = bool(sorgu('SELECT 1 FROM takipciler WHERE takip_eden_id = ? AND takip_edilen_id = ?',
                                  (g.user['id'], id), tek=True))
        beni_takip_ediyor = bool(sorgu('SELECT 1 FROM takipciler WHERE takip_eden_id = ? AND takip_edilen_id = ?',
                                       (id, g.user['id']), tek=True))
    gonderiler = sorgu(gonderi_sql('WHERE g.kullanici_id = ?'), (id,))
    kaydedilenler = []
    if g.user and g.user['id'] == id:
        kaydedilenler = sorgu(haber_listesi_sql('WHERE h.id IN (SELECT haber_id FROM haber_kayitlari WHERE kullanici_id = ?)'), (id,))
    toplam_begeni = sum(gd['begeni_sayisi'] for gd in gonderiler)
    ortak_takip = []
    if g.user and g.user['id'] != id:
        ortak_takip = sorgu('''SELECT k.* FROM takipciler t JOIN kullanicilar k ON k.id = t.takip_eden_id
                               WHERE t.takip_edilen_id = ? AND t.takip_eden_id IN
                               (SELECT takip_edilen_id FROM takipciler WHERE takip_eden_id = ?) LIMIT 3''',
                            (id, g.user['id']))
    return render_template('profil.html', kisi=kisi, takipci_sayisi=takipci_sayisi,
                           takip_edilen_sayisi=takip_edilen_sayisi, takip_durumu=takip_durumu,
                           beni_takip_ediyor=beni_takip_ediyor, gonderiler=gonderiler,
                           kaydedilenler=kaydedilenler, toplam_begeni=toplam_begeni, ortak_takip=ortak_takip)


@app.route('/hesap-ayarlari', methods=['GET', 'POST'])
@giris_gerekli
def hesap_ayarlari():
    k = g.user
    if request.method == 'POST':
        ad = request.form.get('ad_soyad', '').strip()
        if len(ad) < 2:
            flash('Ad soyad en az 2 karakter olmalıdır.', 'danger')
            return redirect(url_for('hesap_ayarlari'))
        try:
            foto = dosya_kaydet(request.files.get('profil_gorsel')) or k['profil_fotografi']
            kapak = dosya_kaydet(request.files.get('kapak_gorsel')) or k['kapak_fotografi']
        except ValueError as e:
            flash(str(e), 'danger')
            return redirect(url_for('hesap_ayarlari'))
        if request.form.get('foto_kaldir'):
            foto = f'https://ui-avatars.com/api/?name={ad.replace(" ", "+")}&background=0D8ABC&color=fff&bold=true'
        if request.form.get('kapak_kaldir'):
            kapak = None
        web = request.form.get('web_sitesi', '').strip()
        if web and not web.startswith(('http://', 'https://')):
            web = 'https://' + web
        calistir('''UPDATE kullanicilar SET ad_soyad=?, biyografi=?, profil_fotografi=?, kapak_fotografi=?,
                    unvan=?, konum=?, web_sitesi=? WHERE id=?''',
                 (ad, request.form.get('biyografi', '').strip()[:300], foto, kapak,
                  request.form.get('unvan', '').strip()[:60], request.form.get('konum', '').strip()[:60],
                  web[:200], k['id']))
        flash('Profilin başarıyla güncellendi.', 'success')
        return redirect(url_for('hesap_ayarlari'))
    return render_template('hesap_ayarlari.html', kisi=k)


@app.route('/ayarlar', methods=['GET', 'POST'])
@giris_gerekli
def ayarlar():
    k = g.user
    if request.method == 'POST':
        islem = request.form.get('islem')
        if islem == 'sifre':
            mevcut, yeni, tekrar = (request.form.get(x, '') for x in ('mevcut_sifre', 'yeni_sifre', 'yeni_sifre_tekrar'))
            if not sifre_dogrula(k['sifre'], mevcut):
                flash('Mevcut şifreniz hatalı.', 'danger')
            elif len(yeni) < 6:
                flash('Yeni şifre en az 6 karakter olmalıdır.', 'danger')
            elif yeni != tekrar:
                flash('Yeni şifreler eşleşmiyor.', 'danger')
            else:
                calistir('UPDATE kullanicilar SET sifre = ? WHERE id = ?', (generate_password_hash(yeni), k['id']))
                flash('Şifreniz güncellendi.', 'success')
            return redirect(url_for('ayarlar', sekme='guvenlik'))
        if islem == 'eposta':
            yeni = request.form.get('eposta', '').strip().lower()
            if not sifre_dogrula(k['sifre'], request.form.get('sifre', '')):
                flash('Şifre hatalı.', 'danger')
            elif '@' not in yeni:
                flash('Geçerli bir e-posta girin.', 'danger')
            elif sorgu('SELECT 1 FROM kullanicilar WHERE LOWER(eposta) = ? AND id != ?', (yeni, k['id']), tek=True):
                flash('Bu e-posta başka bir hesapta kullanılıyor.', 'danger')
            else:
                calistir('UPDATE kullanicilar SET eposta = ? WHERE id = ?', (yeni, k['id']))
                flash('E-posta adresiniz güncellendi.', 'success')
            return redirect(url_for('ayarlar', sekme='guvenlik'))
        if islem == 'gizlilik':
            izin = request.form.get('mesaj_izni', 'herkes')
            calistir('UPDATE kullanicilar SET mesaj_izni = ?, cevrimici_goster = ? WHERE id = ?',
                     (izin if izin in ('herkes', 'takip', 'kimse') else 'herkes',
                      1 if request.form.get('cevrimici_goster') else 0, k['id']))
            flash('Gizlilik tercihleriniz kaydedildi.', 'success')
            return redirect(url_for('ayarlar', sekme='gizlilik'))
        if islem == 'destek':
            mesaj = request.form.get('mesaj', '').strip()
            if mesaj:
                calistir('INSERT INTO destek_talepleri (kullanici_id, ad_soyad, eposta, konu, mesaj, tur) VALUES (?,?,?,?,?,?)',
                         (k['id'], k['ad_soyad'], k['eposta'], request.form.get('konu', 'Genel'), mesaj, 'destek'))
                flash('Destek talebiniz ekibimize iletildi.', 'success')
            return redirect(url_for('ayarlar', sekme='destek'))
        if islem == 'hesap_sil':
            if not sifre_dogrula(k['sifre'], request.form.get('sifre', '')):
                flash('Hesabı silmek için şifrenizi doğru girmelisiniz.', 'danger')
                return redirect(url_for('ayarlar', sekme='hesap'))
            hesap_verilerini_sil(k['id'])
            session.clear()
            flash('Hesabınız ve tüm verileriniz silindi. Sizi özleyeceğiz.', 'info')
            return redirect(url_for('index'))
    talepler = sorgu("SELECT * FROM destek_talepleri WHERE kullanici_id = ? ORDER BY id DESC LIMIT 10", (k['id'],))
    return render_template('ayarlar.html', sekme=request.args.get('sekme', 'gorunum'), talepler=talepler)


def hesap_verilerini_sil(uid):
    c = db()
    c.execute('DELETE FROM gonderi_begenileri WHERE kullanici_id = ? OR gonderi_id IN (SELECT id FROM gonderiler WHERE kullanici_id = ?)', (uid, uid))
    c.execute('DELETE FROM gonderi_yorumlari WHERE kullanici_id = ? OR gonderi_id IN (SELECT id FROM gonderiler WHERE kullanici_id = ?)', (uid, uid))
    for sql in ['DELETE FROM gonderiler WHERE kullanici_id = ?',
                'DELETE FROM takipciler WHERE takip_eden_id = ? OR takip_edilen_id = ?',
                'DELETE FROM mesajlar WHERE gonderen_id = ? OR alici_id = ?',
                'DELETE FROM bildirimler WHERE kullanici_id = ? OR gonderen_id = ?',
                'DELETE FROM sohbet_ayarlari WHERE kullanici_id = ? OR hedef_id = ?',
                'DELETE FROM haber_begenileri WHERE kullanici_id = ?',
                'DELETE FROM haber_kayitlari WHERE kullanici_id = ?',
                'DELETE FROM yorum_begenileri WHERE kullanici_id = ?',
                'DELETE FROM haber_yorumlari WHERE kullanici_id = ?',
                'UPDATE ekip_uyeleri SET kullanici_id = NULL WHERE kullanici_id = ?',
                'DELETE FROM kullanicilar WHERE id = ?']:
        c.execute(sql, (uid,) * sql.count('?'))
    c.execute('UPDATE haberler SET begeni = (SELECT COUNT(*) FROM haber_begenileri b WHERE b.haber_id = haberler.id)')
    c.commit()


# =========================================================
#  AKIŞ & GÖNDERİLER
# =========================================================
@app.route('/akis')
def akis():
    filtre = request.args.get('filtre', 'herkes')
    if filtre == 'takip' and g.user:
        gonderiler = sorgu(gonderi_sql('WHERE g.kullanici_id = ? OR g.kullanici_id IN (SELECT takip_edilen_id FROM takipciler WHERE takip_eden_id = ?)', 'LIMIT 60'),
                           (g.user['id'], g.user['id']))
    else:
        filtre = 'herkes'
        gonderiler = sorgu(gonderi_sql(limit='LIMIT 60'))
    benim = None
    if g.user:
        benim = {
            'takipci': sorgu('SELECT COUNT(*) FROM takipciler WHERE takip_edilen_id = ?', (g.user['id'],), tek=True)[0],
            'takip': sorgu('SELECT COUNT(*) FROM takipciler WHERE takip_eden_id = ?', (g.user['id'],), tek=True)[0],
            'gonderi': sorgu('SELECT COUNT(*) FROM gonderiler WHERE kullanici_id = ?', (g.user['id'],), tek=True)[0],
        }
    return render_template('akis.html', gonderiler=gonderiler, filtre=filtre, oneriler=takip_onerileri(),
                           son_haberler=sorgu(haber_listesi_sql(limit='LIMIT 4')), benim=benim)


@app.route('/gonderi-paylas', methods=['POST'])
@giris_gerekli
def gonderi_paylas():
    icerik = request.form.get('icerik', '').strip()
    try:
        gorsel_url = dosya_kaydet(request.files.get('gorsel')) or ''
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(request.referrer or url_for('akis'))
    if not icerik and not gorsel_url:
        flash('Boş gönderi paylaşılamaz.', 'warning')
        return redirect(request.referrer or url_for('akis'))
    cur = calistir('INSERT INTO gonderiler (kullanici_id, icerik, gorsel_url) VALUES (?, ?, ?)',
                   (g.user['id'], icerik[:2200], gorsel_url))
    for t in sorgu('SELECT takip_eden_id FROM takipciler WHERE takip_edilen_id = ?', (g.user['id'],)):
        bildirim_ekle(t[0], 'yeni bir gönderi paylaştı.', link=f'/profil/{g.user["id"]}?gonderi={cur.lastrowid}',
                      gonderen_id=g.user['id'], tur='gonderi')
    db().commit()
    flash('Gönderin paylaşıldı.', 'success')
    return redirect(request.referrer or url_for('profil', id=g.user['id']))


def _gonderi_json(gid):
    gd = sorgu(gonderi_sql('WHERE g.id = ?'), (gid,), tek=True)
    if not gd:
        return None
    yorumlar = sorgu('''SELECT y.*, k.ad_soyad, k.profil_fotografi, k.mavi_tik FROM gonderi_yorumlari y
                        JOIN kullanicilar k ON k.id = y.kullanici_id WHERE y.gonderi_id = ? ORDER BY y.id ASC''', (gid,))
    uid = g.user['id'] if g.user else None
    return {
        'id': gd['id'], 'icerik': gd['icerik'], 'gorsel_url': gd['gorsel_url'] or '',
        'tarih': zaman_once(gd['tarih']), 'tarih_uzun': tarih_tr(gd['tarih'], True),
        'begeni': gd['begeni_sayisi'], 'begendim': bool(gd['begendim']), 'yorum_sayisi': gd['yorum_sayisi'],
        'benim': uid == gd['kullanici_id'], 'yonetici': bool(g.user and g.user['yetki'] == 'personel'),
        'yazar': {'id': gd['kullanici_id'], 'ad_soyad': gd['yazar_ad'], 'profil_fotografi': gd['yazar_foto'],
                  'mavi_tik': bool(gd['yazar_tik'])},
        'yorumlar': [{'id': y['id'], 'yorum': y['yorum'], 'tarih': zaman_once(y['tarih']),
                      'silinebilir': uid in (y['kullanici_id'], gd['kullanici_id']),
                      'yazar': {'id': y['kullanici_id'], 'ad_soyad': y['ad_soyad'],
                                'profil_fotografi': y['profil_fotografi'], 'mavi_tik': bool(y['mavi_tik'])}}
                     for y in yorumlar],
    }


@app.route('/api/gonderi/<int:id>')
def api_gonderi(id):
    veri = _gonderi_json(id)
    if not veri:
        return json_hata('Gönderi bulunamadı.', 404)
    return jsonify({'status': 'success', 'gonderi': veri})


@app.route('/api/gonderi/<int:id>/begen', methods=['POST'])
@giris_gerekli
def api_gonderi_begen(id):
    gd = sorgu('SELECT * FROM gonderiler WHERE id = ?', (id,), tek=True)
    if not gd:
        return json_hata('Gönderi bulunamadı.', 404)
    ben = g.user['id']
    if sorgu('SELECT 1 FROM gonderi_begenileri WHERE gonderi_id = ? AND kullanici_id = ?', (id, ben), tek=True):
        db().execute('DELETE FROM gonderi_begenileri WHERE gonderi_id = ? AND kullanici_id = ?', (id, ben))
        begendim = False
    else:
        db().execute('INSERT INTO gonderi_begenileri (gonderi_id, kullanici_id) VALUES (?, ?)', (id, ben))
        begendim = True
        bildirim_ekle(gd['kullanici_id'], 'gönderini beğendi.', link=f'/profil/{gd["kullanici_id"]}?gonderi={id}',
                      gonderen_id=ben, tur='begeni')
    sayi = db().execute('SELECT COUNT(*) FROM gonderi_begenileri WHERE gonderi_id = ?', (id,)).fetchone()[0]
    db().execute('UPDATE gonderiler SET begeni = ? WHERE id = ?', (sayi, id))
    db().commit()
    return jsonify({'status': 'success', 'begendim': begendim, 'begeni': sayi})


@app.route('/api/gonderi/<int:id>/yorum', methods=['POST'])
@giris_gerekli
def api_gonderi_yorum(id):
    gd = sorgu('SELECT * FROM gonderiler WHERE id = ?', (id,), tek=True)
    yorum = (request.get_json(silent=True) or {}).get('yorum', '').strip()
    if not gd or not yorum:
        return json_hata('Yorum boş olamaz.', 400)
    db().execute('INSERT INTO gonderi_yorumlari (gonderi_id, kullanici_id, yorum) VALUES (?,?,?)',
                 (id, g.user['id'], yorum[:1000]))
    bildirim_ekle(gd['kullanici_id'], f'gönderine yorum yaptı: "{yorum[:40]}"',
                  link=f'/profil/{gd["kullanici_id"]}?gonderi={id}', gonderen_id=g.user['id'], tur='yorum')
    db().commit()
    return jsonify({'status': 'success', 'gonderi': _gonderi_json(id)})


@app.route('/api/gonderi_yorum/<int:id>/sil', methods=['POST'])
@giris_gerekli
def api_gonderi_yorum_sil(id):
    y = sorgu('''SELECT y.*, g.kullanici_id AS sahip FROM gonderi_yorumlari y
                 JOIN gonderiler g ON g.id = y.gonderi_id WHERE y.id = ?''', (id,), tek=True)
    if not y or g.user['id'] not in (y['kullanici_id'], y['sahip']) and g.user['yetki'] != 'personel':
        return json_hata('Bu yorumu silemezsiniz.', 403)
    calistir('DELETE FROM gonderi_yorumlari WHERE id = ?', (id,))
    return jsonify({'status': 'success', 'gonderi': _gonderi_json(y['gonderi_id'])})


@app.route('/api/gonderi/<int:id>/duzenle', methods=['POST'])
@giris_gerekli
def api_gonderi_duzenle(id):
    icerik = (request.get_json(silent=True) or {}).get('icerik', '').strip()
    gd = sorgu('SELECT * FROM gonderiler WHERE id = ?', (id,), tek=True)
    if not gd or gd['kullanici_id'] != g.user['id']:
        return json_hata('Bu gönderiyi düzenleyemezsiniz.', 403)
    if not icerik and not gd['gorsel_url']:
        return json_hata('Gönderi boş olamaz.', 400)
    calistir('UPDATE gonderiler SET icerik = ? WHERE id = ?', (icerik[:2200], id))
    return jsonify({'status': 'success', 'icerik': icerik})


@app.route('/gonderi/<int:id>/sil', methods=['POST'])
@app.route('/api/gonderi/<int:id>/sil', methods=['POST'])
@giris_gerekli
def gonderi_sil(id):
    gd = sorgu('SELECT * FROM gonderiler WHERE id = ?', (id,), tek=True)
    if gd and (gd['kullanici_id'] == g.user['id'] or g.user['yetki'] == 'personel'):
        db().execute('DELETE FROM gonderi_begenileri WHERE gonderi_id = ?', (id,))
        db().execute('DELETE FROM gonderi_yorumlari WHERE gonderi_id = ?', (id,))
        db().execute('DELETE FROM gonderiler WHERE id = ?', (id,))
        db().commit()
        if request.path.startswith('/api/'):
            return jsonify({'status': 'success'})
        flash('Gönderi silindi.', 'success')
    elif request.path.startswith('/api/'):
        return json_hata('Bu gönderiyi silemezsiniz.', 403)
    return redirect(request.referrer or url_for('profil', id=g.user['id']))


# =========================================================
#  HABERLER
# =========================================================
@app.route('/haber/<int:id>', methods=['GET', 'POST'])
def haber_detay(id):
    haber = sorgu('SELECT * FROM haberler WHERE id = ?', (id,), tek=True)
    if not haber:
        abort(404)
    if request.method == 'POST':
        if not g.user:
            return redirect(url_for('giris', next=request.path))
        yorum = request.form.get('yorum', '').strip()
        if yorum:
            _haber_yorum_ekle(id, yorum, request.form.get('ust_yorum_id', type=int))
        return redirect(url_for('haber_detay', id=id) + '#yorumlar')

    goruldu = session.get('goruldu', [])
    if id not in goruldu:  # her yenilemede sayaç şişmesin
        calistir('UPDATE haberler SET goruntulenme = COALESCE(goruntulenme, 0) + 1 WHERE id = ?', (id,))
        session['goruldu'] = (goruldu + [id])[-200:]
        haber = sorgu('SELECT * FROM haberler WHERE id = ?', (id,), tek=True)

    yorumlar = _haber_yorumlari(id)
    begenildi_mi = kaydedildi_mi = takip_resmi = False
    if g.user:
        ben = g.user['id']
        begenildi_mi = bool(sorgu('SELECT 1 FROM haber_begenileri WHERE haber_id = ? AND kullanici_id = ?', (id, ben), tek=True))
        kaydedildi_mi = bool(sorgu('SELECT 1 FROM haber_kayitlari WHERE haber_id = ? AND kullanici_id = ?', (id, ben), tek=True))
        takip_resmi = bool(sorgu('SELECT 1 FROM takipciler WHERE takip_eden_id = ? AND takip_edilen_id = ?', (ben, RESMI_HESAP_ID), tek=True))
    begeni = sorgu('SELECT COUNT(*) FROM haber_begenileri WHERE haber_id = ?', (id,), tek=True)[0]
    resmi = sorgu('SELECT * FROM kullanicilar WHERE id = ?', (RESMI_HESAP_ID,), tek=True)
    ilgili = sorgu(haber_listesi_sql('WHERE h.id != ?', 'LIMIT 3'), (id,))
    return render_template('haber_detay.html', haber=haber, yorumlar=yorumlar, begeni=begeni,
                           begenildi_mi=begenildi_mi, kaydedildi_mi=kaydedildi_mi, takip_resmi=takip_resmi,
                           resmi=resmi, ilgili=ilgili, yorum_sayisi=sum(1 + len(y['yanitlar']) for y in yorumlar))


def _haber_yorumlari(haber_id):
    uid = g.user['id'] if g.user else 0
    satirlar = sorgu('''SELECT y.*, k.ad_soyad AS k_ad, k.profil_fotografi, k.mavi_tik,
                        (SELECT COUNT(*) FROM yorum_begenileri WHERE yorum_id = y.id) AS begeni_sayisi,
                        (SELECT COUNT(*) FROM yorum_begenileri WHERE yorum_id = y.id AND kullanici_id = ?) AS begendim
                        FROM haber_yorumlari y LEFT JOIN kullanicilar k ON k.id = y.kullanici_id
                        WHERE y.haber_id = ? ORDER BY y.id ASC''', (uid, haber_id))
    ana, yanit = [], {}
    for s in satirlar:
        d = dict(s)
        d['ad'] = s['k_ad'] or s['kullanici_ad']
        d['yanitlar'] = []
        if s['ust_yorum_id']:
            yanit.setdefault(s['ust_yorum_id'], []).append(d)
        else:
            ana.append(d)
    idler = {d['id'] for d in ana}
    for d in ana:
        d['yanitlar'] = yanit.get(d['id'], [])
    for ust, liste in yanit.items():  # üst yorumu silinmiş yanıtlar
        if ust not in idler:
            ana.extend(liste)
    ana.sort(key=lambda d: d['id'], reverse=True)
    return ana


def _haber_yorum_ekle(haber_id, yorum, ust_id=None):
    if ust_id:
        ust_kayit = sorgu('SELECT id, ust_yorum_id FROM haber_yorumlari WHERE id = ? AND haber_id = ?', (ust_id, haber_id), tek=True)
        ust_id = (ust_kayit['ust_yorum_id'] or ust_kayit['id']) if ust_kayit else None
    cur = db().execute('INSERT INTO haber_yorumlari (haber_id, kullanici_ad, kullanici_id, yorum, ust_yorum_id) VALUES (?,?,?,?,?)',
                       (haber_id, g.user['ad_soyad'], g.user['id'], yorum[:1000], ust_id))
    if ust_id:
        ust = sorgu('SELECT kullanici_id FROM haber_yorumlari WHERE id = ?', (ust_id,), tek=True)
        if ust:
            bildirim_ekle(ust['kullanici_id'], f'yorumuna yanıt verdi: "{yorum[:40]}"', link=f'/haber/{haber_id}#yorum-{cur.lastrowid}',
                          gonderen_id=g.user['id'], tur='yorum')
    db().commit()
    return cur.lastrowid


@app.route('/api/haber/<int:id>/yorum', methods=['POST'])
@giris_gerekli
def api_haber_yorum(id):
    veri = request.get_json(silent=True) or {}
    yorum = veri.get('yorum', '').strip()
    if not yorum or not sorgu('SELECT 1 FROM haberler WHERE id = ?', (id,), tek=True):
        return json_hata('Yorum boş olamaz.', 400)
    yeni_id = _haber_yorum_ekle(id, yorum, veri.get('ust_yorum_id'))
    return jsonify({'status': 'success', 'id': yeni_id})


@app.route('/api/haber_yorum/<int:id>/sil', methods=['POST'])
@giris_gerekli
def api_haber_yorum_sil(id):
    y = sorgu('SELECT * FROM haber_yorumlari WHERE id = ?', (id,), tek=True)
    if not y or (y['kullanici_id'] != g.user['id'] and g.user['yetki'] != 'personel'):
        return json_hata('Bu yorumu silemezsiniz.', 403)
    db().execute('DELETE FROM yorum_begenileri WHERE yorum_id IN (SELECT id FROM haber_yorumlari WHERE id = ? OR ust_yorum_id = ?)', (id, id))
    db().execute('DELETE FROM haber_yorumlari WHERE id = ? OR ust_yorum_id = ?', (id, id))
    db().commit()
    return jsonify({'status': 'success'})


@app.route('/api/haber_yorum/<int:id>/begen', methods=['POST'])
@giris_gerekli
def api_haber_yorum_begen(id):
    y = sorgu('SELECT * FROM haber_yorumlari WHERE id = ?', (id,), tek=True)
    if not y:
        return json_hata('Yorum bulunamadı.', 404)
    ben = g.user['id']
    if sorgu('SELECT 1 FROM yorum_begenileri WHERE yorum_id = ? AND kullanici_id = ?', (id, ben), tek=True):
        db().execute('DELETE FROM yorum_begenileri WHERE yorum_id = ? AND kullanici_id = ?', (id, ben))
        begendim = False
    else:
        db().execute('INSERT INTO yorum_begenileri (yorum_id, kullanici_id) VALUES (?, ?)', (id, ben))
        begendim = True
        bildirim_ekle(y['kullanici_id'], 'yorumunu beğendi.', link=f'/haber/{y["haber_id"]}#yorum-{id}', gonderen_id=ben, tur='begeni')
    sayi = db().execute('SELECT COUNT(*) FROM yorum_begenileri WHERE yorum_id = ?', (id,)).fetchone()[0]
    db().commit()
    return jsonify({'status': 'success', 'begendim': begendim, 'begeni': sayi})


@app.route('/api/haber/<int:id>/begen', methods=['POST'])
@giris_gerekli
def api_haber_begen(id):
    ben = g.user['id']
    if sorgu('SELECT 1 FROM haber_begenileri WHERE haber_id = ? AND kullanici_id = ?', (id, ben), tek=True):
        db().execute('DELETE FROM haber_begenileri WHERE haber_id = ? AND kullanici_id = ?', (id, ben))
        begendim = False
    else:
        db().execute('INSERT INTO haber_begenileri (haber_id, kullanici_id) VALUES (?, ?)', (id, ben))
        begendim = True
    sayi = db().execute('SELECT COUNT(*) FROM haber_begenileri WHERE haber_id = ?', (id,)).fetchone()[0]
    db().execute('UPDATE haberler SET begeni = ? WHERE id = ?', (sayi, id))
    db().commit()
    return jsonify({'status': 'success', 'begeni': sayi, 'begendim': begendim})


@app.route('/api/haber/<int:id>/kaydet', methods=['POST'])
@giris_gerekli
def api_haber_kaydet(id):
    ben = g.user['id']
    if sorgu('SELECT 1 FROM haber_kayitlari WHERE haber_id = ? AND kullanici_id = ?', (id, ben), tek=True):
        calistir('DELETE FROM haber_kayitlari WHERE haber_id = ? AND kullanici_id = ?', (id, ben))
        durum = 'cikarildi'
    else:
        calistir('INSERT INTO haber_kayitlari (haber_id, kullanici_id) VALUES (?, ?)', (id, ben))
        durum = 'kaydedildi'
    return jsonify({'status': 'success', 'durum': durum})


# =========================================================
#  SOSYAL API (arama, takip, bildirim)
# =========================================================
@app.route('/api/arama')
def api_arama():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'kisiler': [], 'haberler': [], 'projeler': []})
    like = f'%{q}%'
    kisiler = sorgu('SELECT * FROM kullanicilar WHERE ad_soyad LIKE ? ORDER BY mavi_tik DESC, id DESC LIMIT 6', (like,))
    haberler_ = sorgu('SELECT id, baslik, firma_adi, gorsel_url FROM haberler WHERE baslik LIKE ? OR icerik LIKE ? ORDER BY id DESC LIMIT 4', (like, like))
    projeler_ = sorgu('SELECT id, baslik, gorsel_url FROM projeler WHERE baslik LIKE ? OR icerik LIKE ? ORDER BY id DESC LIMIT 3', (like, like))
    return jsonify({'kisiler': [kullanici_json(k) for k in kisiler],
                    'haberler': [dict(h) for h in haberler_], 'projeler': [dict(p) for p in projeler_]})


@app.route('/api/takip/<int:id>', methods=['POST'])
@giris_gerekli
def api_takip(id):
    ben = g.user['id']
    if ben == id or not sorgu('SELECT 1 FROM kullanicilar WHERE id = ?', (id,), tek=True):
        return json_hata('Geçersiz işlem.', 400)
    if sorgu('SELECT 1 FROM takipciler WHERE takip_eden_id = ? AND takip_edilen_id = ?', (ben, id), tek=True):
        db().execute('DELETE FROM takipciler WHERE takip_eden_id = ? AND takip_edilen_id = ?', (ben, id))
        durum = 'takipten_cikildi'
    else:
        db().execute('INSERT INTO takipciler (takip_eden_id, takip_edilen_id) VALUES (?, ?)', (ben, id))
        durum = 'takip_edildi'
        bildirim_ekle(id, 'seni takip etmeye başladı.', link=f'/profil/{ben}', gonderen_id=ben, tur='takip')
    db().commit()
    sayi = sorgu('SELECT COUNT(*) FROM takipciler WHERE takip_edilen_id = ?', (id,), tek=True)[0]
    return jsonify({'status': 'success', 'durum': durum, 'takipci_sayisi': sayi})


@app.route('/api/takip_listesi/<int:id>')
def api_takip_listesi(id):
    tur = request.args.get('tur', 'takipciler')
    if tur == 'takip_edilenler':
        liste = sorgu('''SELECT k.* FROM takipciler t JOIN kullanicilar k ON k.id = t.takip_edilen_id
                         WHERE t.takip_eden_id = ? ORDER BY t.id DESC''', (id,))
    else:
        liste = sorgu('''SELECT k.* FROM takipciler t JOIN kullanicilar k ON k.id = t.takip_eden_id
                         WHERE t.takip_edilen_id = ? ORDER BY t.id DESC''', (id,))
    benim_takip = set()
    if g.user:
        benim_takip = {r[0] for r in sorgu('SELECT takip_edilen_id FROM takipciler WHERE takip_eden_id = ?', (g.user['id'],))}
    sonuc = []
    for k in liste:
        d = kullanici_json(k)
        d['biyografi'] = k['unvan'] or (k['biyografi'] or '')[:60]
        d['takip_ediyorum'] = k['id'] in benim_takip
        d['ben'] = bool(g.user and g.user['id'] == k['id'])
        sonuc.append(d)
    return jsonify({'status': 'success', 'liste': sonuc})


@app.route('/api/bildirimler')
@giris_gerekli
def api_bildirimler():
    satirlar = sorgu('''SELECT b.*, k.ad_soyad, k.profil_fotografi, k.mavi_tik FROM bildirimler b
                        LEFT JOIN kullanicilar k ON k.id = b.gonderen_id
                        WHERE b.kullanici_id = ? ORDER BY b.id DESC LIMIT 30''', (g.user['id'],))
    liste = [{
        'id': b['id'], 'icerik': b['icerik'], 'link': b['link'] or '', 'okundu': bool(b['okundu']),
        'tur': b['tur'] or 'genel', 'zaman': zaman_once(b['tarih']),
        'gonderen': ({'id': b['gonderen_id'], 'ad_soyad': b['ad_soyad'], 'profil_fotografi': b['profil_fotografi'],
                      'mavi_tik': bool(b['mavi_tik'])} if b['ad_soyad'] else None),
    } for b in satirlar]
    return jsonify({'status': 'success', 'bildirimler': liste})


@app.route('/api/sayaclar')
@giris_gerekli
def api_sayaclar():
    uid = g.user['id']
    return jsonify({
        'status': 'success',
        'bildirim': sorgu('SELECT COUNT(*) FROM bildirimler WHERE kullanici_id = ? AND okundu = 0', (uid,), tek=True)[0],
        'mesaj': sorgu('SELECT COUNT(*) FROM mesajlar WHERE alici_id = ? AND okundu = 0 AND silindi = 0', (uid,), tek=True)[0],
    })


@app.route('/api/bildirimleri_okudum', methods=['POST'])
@giris_gerekli
def bildirimleri_okudum():
    calistir('UPDATE bildirimler SET okundu = 1 WHERE kullanici_id = ?', (g.user['id'],))
    return jsonify({'status': 'success'})


@app.route('/api/bildirim/sil/<int:id>', methods=['POST'])
@giris_gerekli
def bildirim_sil(id):
    calistir('DELETE FROM bildirimler WHERE id = ? AND kullanici_id = ?', (id, g.user['id']))
    return jsonify({'status': 'success'})


@app.route('/api/bildirim/sil_tumu', methods=['POST'])
@giris_gerekli
def bildirim_sil_tumu():
    calistir('DELETE FROM bildirimler WHERE kullanici_id = ?', (g.user['id'],))
    return jsonify({'status': 'success'})


# =========================================================
#  MESAJLAŞMA
# =========================================================
def _mesaj_json(m, ben):
    return {
        'id': m['id'], 'benim': m['gonderen_id'] == ben,
        'icerik': '' if m['silindi'] else m['icerik'],
        'gorsel_url': '' if m['silindi'] else (m['gorsel_url'] or ''),
        'silindi': bool(m['silindi']), 'okundu': bool(m['okundu']), 'tepki': m['tepki'] or '',
        'saat': saat(m['tarih']), 'gun': tarih_tr(m['tarih']), 'tarih': m['tarih'],
    }


def _sohbet_listesi(ben):
    satirlar = sorgu('''
        SELECT k.*, s.takma_ad AS ozel_ad, son.icerik AS son_icerik, son.gorsel_url AS son_gorsel,
               son.silindi AS son_silindi, son.gonderen_id AS son_gonderen, son.tarih AS son_tarih, son.okundu AS son_okundu,
               (SELECT COUNT(*) FROM mesajlar WHERE gonderen_id = k.id AND alici_id = ? AND okundu = 0 AND silindi = 0) AS okunmamis
        FROM (SELECT CASE WHEN gonderen_id = ? THEN alici_id ELSE gonderen_id END AS diger, MAX(id) AS son_id
              FROM mesajlar WHERE gonderen_id = ? OR alici_id = ? GROUP BY diger) c
        JOIN kullanicilar k ON k.id = c.diger
        JOIN mesajlar son ON son.id = c.son_id
        LEFT JOIN sohbet_ayarlari s ON s.kullanici_id = ? AND s.hedef_id = k.id
        ORDER BY c.son_id DESC''', (ben, ben, ben, ben, ben))
    liste = []
    for r in satirlar:
        d = kullanici_json(r)
        if r['son_silindi']:
            onizleme = 'Mesaj silindi'
        elif r['son_gorsel'] and not r['son_icerik']:
            onizleme = '📷 Fotoğraf'
        else:
            onizleme = r['son_icerik']
        d.update({
            'gorunen_ad': r['ozel_ad'] or r['ad_soyad'], 'onizleme': ('Sen: ' if r['son_gonderen'] == ben else '') + (onizleme or ''),
            'zaman': zaman_once(r['son_tarih']), 'okunmamis': r['okunmamis'],
            'son_benim_okundu': bool(r['son_gonderen'] == ben and r['son_okundu']),
        })
        liste.append(d)
    return liste


def _mesaj_atabilir_mi(gonderen, alici):
    izin = alici['mesaj_izni'] or 'herkes'
    if izin == 'herkes' or gonderen['yetki'] == 'personel':
        return True
    if sorgu('SELECT 1 FROM mesajlar WHERE gonderen_id = ? AND alici_id = ? LIMIT 1', (alici['id'], gonderen['id']), tek=True):
        return True  # zaten konuşuyorlar
    if izin == 'takip':
        return bool(sorgu('SELECT 1 FROM takipciler WHERE takip_eden_id = ? AND takip_edilen_id = ?',
                          (alici['id'], gonderen['id']), tek=True))
    return False


@app.route('/mesajlar')
@app.route('/mesajlar/<int:alici_id>')
@giris_gerekli
def mesaj_paneli(alici_id=None):
    ben = g.user['id']
    sohbetler = _sohbet_listesi(ben)
    konusulanlar = {s['id'] for s in sohbetler}
    oneriler = [k for k in sorgu('''SELECT * FROM kullanicilar WHERE id != ?
                                     ORDER BY mavi_tik DESC, son_gorulme DESC LIMIT 12''', (ben,))
                if k['id'] not in konusulanlar][:6]
    secili_kisi, sohbet, aktif_tema, aktif_takma_ad, mesaj_izni = None, [], 'default', '', True
    if alici_id:
        if alici_id == ben:
            return redirect(url_for('mesaj_paneli'))
        secili_kisi = sorgu('SELECT * FROM kullanicilar WHERE id = ?', (alici_id,), tek=True)
        if not secili_kisi:
            abort(404)
        calistir('UPDATE mesajlar SET okundu = 1 WHERE gonderen_id = ? AND alici_id = ? AND okundu = 0', (alici_id, ben))
        sohbet = [_mesaj_json(m, ben) for m in sorgu('''SELECT * FROM mesajlar WHERE (gonderen_id = ? AND alici_id = ?)
                                                        OR (gonderen_id = ? AND alici_id = ?) ORDER BY id ASC''',
                                                     (ben, alici_id, alici_id, ben))]
        ayar = sorgu('SELECT * FROM sohbet_ayarlari WHERE kullanici_id = ? AND hedef_id = ?', (ben, alici_id), tek=True)
        if ayar:
            aktif_tema = ayar['tema'] or 'default'
            aktif_takma_ad = ayar['takma_ad'] or ''
        mesaj_izni = _mesaj_atabilir_mi(g.user, secili_kisi)
        sohbetler = _sohbet_listesi(ben)  # okundu bilgisi güncellendi
    return render_template('mesaj_paneli.html', sohbetler=sohbetler, oneriler=oneriler, secili_kisi=secili_kisi,
                           sohbet=sohbet, aktif_tema=aktif_tema, aktif_takma_ad=aktif_takma_ad, mesaj_izni=mesaj_izni)


@app.route('/api/sohbetler')
@giris_gerekli
def api_sohbetler():
    return jsonify({'status': 'success', 'sohbetler': _sohbet_listesi(g.user['id'])})


@app.route('/api/mesajlar/<int:alici_id>')
@giris_gerekli
def api_mesajlar(alici_id):
    ben = g.user['id']
    son_id = request.args.get('son', 0, type=int)
    calistir('UPDATE mesajlar SET okundu = 1 WHERE gonderen_id = ? AND alici_id = ? AND okundu = 0', (alici_id, ben))
    yeni = sorgu('''SELECT * FROM mesajlar WHERE id > ? AND ((gonderen_id = ? AND alici_id = ?) OR (gonderen_id = ? AND alici_id = ?))
                    ORDER BY id ASC''', (son_id, ben, alici_id, alici_id, ben))
    # Okundu / silindi / tepki değişikliklerini yakalamak için son 60 mesajın durumu
    durumlar = sorgu('''SELECT id, okundu, silindi, tepki FROM mesajlar WHERE ((gonderen_id = ? AND alici_id = ?) OR (gonderen_id = ? AND alici_id = ?))
                        ORDER BY id DESC LIMIT 60''', (ben, alici_id, alici_id, ben))
    karsi = sorgu('SELECT * FROM kullanicilar WHERE id = ?', (alici_id,), tek=True)
    yaziyor = time.time() - YAZIYOR.get((alici_id, ben), 0) < 4
    return jsonify({
        'status': 'success', 'mesajlar': [_mesaj_json(m, ben) for m in yeni],
        'durumlar': [{'id': d['id'], 'okundu': bool(d['okundu']), 'silindi': bool(d['silindi']), 'tepki': d['tepki'] or ''} for d in durumlar],
        'yaziyor': yaziyor, 'cevrimici': cevrimici_mi(karsi), 'durum_metni': son_gorulme_metni(karsi),
    })


@app.route('/api/mesaj_gonder', methods=['POST'])
@giris_gerekli
def api_mesaj_gonder():
    ben = g.user['id']
    veri = request.get_json(silent=True) or request.form
    alici_id = int(veri.get('alici_id') or 0)
    icerik = (veri.get('icerik') or '').strip()
    alici = sorgu('SELECT * FROM kullanicilar WHERE id = ?', (alici_id,), tek=True)
    if not alici or alici_id == ben:
        return json_hata('Alıcı bulunamadı.', 404)
    if not _mesaj_atabilir_mi(g.user, alici):
        return json_hata('Bu kullanıcı mesaj kabul etmiyor.', 403)
    try:
        gorsel = dosya_kaydet(request.files.get('gorsel')) if request.files else None
    except ValueError as e:
        return json_hata(str(e), 400)
    if not icerik and not gorsel:
        return json_hata('Boş mesaj gönderilemez.', 400)
    cur = calistir('INSERT INTO mesajlar (gonderen_id, alici_id, icerik, gorsel_url, okundu) VALUES (?, ?, ?, ?, 0)',
                   (ben, alici_id, icerik[:4000], gorsel))
    YAZIYOR.pop((ben, alici_id), None)
    m = sorgu('SELECT * FROM mesajlar WHERE id = ?', (cur.lastrowid,), tek=True)
    return jsonify({'status': 'success', 'mesaj': _mesaj_json(m, ben)})


@app.route('/api/mesaj/<int:id>/sil', methods=['POST'])
@giris_gerekli
def api_mesaj_sil(id):
    m = sorgu('SELECT * FROM mesajlar WHERE id = ?', (id,), tek=True)
    if not m or m['gonderen_id'] != g.user['id']:
        return json_hata('Bu mesajı silemezsiniz.', 403)
    calistir("UPDATE mesajlar SET silindi = 1, icerik = '', gorsel_url = NULL, tepki = NULL WHERE id = ?", (id,))
    return jsonify({'status': 'success'})


@app.route('/api/mesaj/<int:id>/tepki', methods=['POST'])
@giris_gerekli
def api_mesaj_tepki(id):
    m = sorgu('SELECT * FROM mesajlar WHERE id = ?', (id,), tek=True)
    if not m or g.user['id'] not in (m['gonderen_id'], m['alici_id']) or m['silindi']:
        return json_hata('Geçersiz mesaj.', 403)
    tepki = (request.get_json(silent=True) or {}).get('tepki', '')[:8]
    yeni = None if (not tepki or m['tepki'] == tepki) else tepki
    calistir('UPDATE mesajlar SET tepki = ? WHERE id = ?', (yeni, id))
    return jsonify({'status': 'success', 'tepki': yeni or ''})


@app.route('/api/yaziyor', methods=['POST'])
@giris_gerekli
def api_yaziyor():
    alici = (request.get_json(silent=True) or {}).get('alici_id')
    if alici:
        YAZIYOR[(g.user['id'], int(alici))] = time.time()
    return jsonify({'status': 'success'})


@app.route('/api/sohbet_ayar', methods=['POST'])
@giris_gerekli
def sohbet_ayar():
    veri = request.get_json(silent=True) or {}
    alici_id = veri.get('alici_id')
    tema = veri.get('tema') if veri.get('tema') in SOHBET_TEMALARI else 'default'
    takma_ad = (veri.get('takma_ad') or '').strip()[:40]
    ben = g.user['id']
    if sorgu('SELECT 1 FROM sohbet_ayarlari WHERE kullanici_id = ? AND hedef_id = ?', (ben, alici_id), tek=True):
        calistir('UPDATE sohbet_ayarlari SET tema = ?, takma_ad = ? WHERE kullanici_id = ? AND hedef_id = ?',
                 (tema, takma_ad, ben, alici_id))
    else:
        calistir('INSERT INTO sohbet_ayarlari (kullanici_id, hedef_id, tema, takma_ad) VALUES (?, ?, ?, ?)',
                 (ben, alici_id, tema, takma_ad))
    return jsonify({'status': 'success', 'tema': tema, 'takma_ad': takma_ad})


# =========================================================
#  YÖNETİM PANELİ
# =========================================================
@app.route('/admin', methods=['GET', 'POST'])
@personel_gerekli
def admin():
    if request.method == 'POST' and 'kullanici_id_duzenle' in request.form:  # eski form uyumluluğu
        k_id = request.form.get('kullanici_id_duzenle', type=int)
        calistir('UPDATE kullanicilar SET yetki = ?, mavi_tik = ? WHERE id = ?',
                 (request.form.get('yetki', 'kullanici'), 1 if request.form.get('mavi_tik') else 0, k_id))
        flash(f'Kullanıcı #{k_id} güncellendi.', 'success')
        return redirect(url_for('admin'))
    ist = istatistikler()
    ist['mesaj'] = sorgu('SELECT COUNT(*) FROM mesajlar', tek=True)[0]
    ist['yorum'] = sorgu('SELECT COUNT(*) FROM haber_yorumlari', tek=True)[0] + sorgu('SELECT COUNT(*) FROM gonderi_yorumlari', tek=True)[0]
    ist['acik_talep'] = sorgu("SELECT COUNT(*) FROM destek_talepleri WHERE durum = 'acik'", tek=True)[0]
    ist['onayli'] = sorgu('SELECT COUNT(*) FROM kullanicilar WHERE mavi_tik = 1', tek=True)[0]
    ist['goruntulenme'] = sorgu('SELECT COALESCE(SUM(goruntulenme),0) FROM haberler', tek=True)[0]
    son_uyeler = sorgu('SELECT * FROM kullanicilar ORDER BY id DESC LIMIT 6')
    son_talepler = sorgu('SELECT * FROM destek_talepleri ORDER BY id DESC LIMIT 5')
    populer = sorgu(haber_listesi_sql(limit='LIMIT 5').replace('ORDER BY h.id DESC', 'ORDER BY h.goruntulenme DESC'))
    return render_template('admin.html', ist=ist, son_uyeler=son_uyeler, son_talepler=son_talepler, populer=populer)


@app.route('/admin/kullanicilar')
@personel_gerekli
def admin_kullanicilar():
    q = request.args.get('q', '').strip()
    if q:
        liste = sorgu('SELECT * FROM kullanicilar WHERE ad_soyad LIKE ? OR eposta LIKE ? ORDER BY id DESC', (f'%{q}%', f'%{q}%'))
    else:
        liste = sorgu('SELECT * FROM kullanicilar ORDER BY id DESC')
    return render_template('admin_kullanicilar.html', kullanicilar=liste, q=q)


@app.route('/api/admin/kullanici/<int:id>', methods=['POST'])
@personel_gerekli
def api_admin_kullanici(id):
    veri = request.get_json(silent=True) or {}
    islem = veri.get('islem')
    k = sorgu('SELECT * FROM kullanicilar WHERE id = ?', (id,), tek=True)
    if not k:
        return json_hata('Kullanıcı bulunamadı.', 404)
    if islem == 'mavi_tik':
        yeni = 0 if k['mavi_tik'] else 1
        calistir('UPDATE kullanicilar SET mavi_tik = ? WHERE id = ?', (yeni, id))
        if yeni:
            bildirim_ekle(id, 'Hesabın onaylandı! Artık profilinde mavi tik görünüyor.', link=f'/profil/{id}',
                          gonderen_id=RESMI_HESAP_ID if id != RESMI_HESAP_ID else None, tur='sistem')
            db().commit()
        return jsonify({'status': 'success', 'mavi_tik': bool(yeni)})
    if islem == 'yetki':
        if id == g.user['id']:
            return json_hata('Kendi yetkinizi değiştiremezsiniz.', 400)
        yeni = 'kullanici' if k['yetki'] == 'personel' else 'personel'
        calistir('UPDATE kullanicilar SET yetki = ? WHERE id = ?', (yeni, id))
        return jsonify({'status': 'success', 'yetki': yeni})
    if islem == 'sil':
        if id in (g.user['id'], RESMI_HESAP_ID):
            return json_hata('Bu hesap silinemez.', 400)
        hesap_verilerini_sil(id)
        return jsonify({'status': 'success'})
    return json_hata('Geçersiz işlem.', 400)


def _gorsel_al(form_alani='gorsel_dosya', url_alani='gorsel_url', mevcut=''):
    yuklenen = dosya_kaydet(request.files.get(form_alani))
    return yuklenen or request.form.get(url_alani, '').strip() or mevcut or ''


@app.route('/admin/haberler')
@personel_gerekli
def admin_haberler():
    return render_template('admin_liste.html', tur='haber', baslik='Haberler',
                           kayitlar=sorgu(haber_listesi_sql()))


@app.route('/admin/haber-ekle', methods=['GET', 'POST'])
@app.route('/admin/haber/<int:id>/duzenle', methods=['GET', 'POST'])
@personel_gerekli
def haber_ekle(id=None):
    kayit = sorgu('SELECT * FROM haberler WHERE id = ?', (id,), tek=True) if id else None
    if id and not kayit:
        abort(404)
    if request.method == 'POST':
        try:
            gorsel = _gorsel_al(mevcut=kayit['gorsel_url'] if kayit else '')
        except ValueError as e:
            flash(str(e), 'danger')
            return redirect(request.url)
        alanlar = (request.form['firma_adi'], request.form['baslik'].strip(), request.form['icerik'].strip(), gorsel)
        if kayit:
            calistir('UPDATE haberler SET firma_adi=?, baslik=?, icerik=?, gorsel_url=? WHERE id=?', alanlar + (id,))
            flash('Haber güncellendi.', 'success')
        else:
            calistir('INSERT INTO haberler (firma_adi, baslik, icerik, gorsel_url) VALUES (?, ?, ?, ?)', alanlar)
            flash('Haber yayınlandı.', 'success')
        return redirect(url_for('admin_haberler'))
    return render_template('haber_ekle.html', kayit=kayit)


@app.route('/admin/haber/<int:id>/sil', methods=['POST'])
@personel_gerekli
def admin_haber_sil(id):
    db().execute('DELETE FROM yorum_begenileri WHERE yorum_id IN (SELECT id FROM haber_yorumlari WHERE haber_id = ?)', (id,))
    for t in ('haber_yorumlari', 'haber_begenileri', 'haber_kayitlari'):
        db().execute(f'DELETE FROM {t} WHERE haber_id = ?', (id,))
    db().execute('DELETE FROM haberler WHERE id = ?', (id,))
    db().commit()
    flash('Haber silindi.', 'success')
    return redirect(url_for('admin_haberler'))


@app.route('/admin/projeler')
@personel_gerekli
def admin_projeler():
    return render_template('admin_liste.html', tur='proje', baslik='Projeler',
                           kayitlar=sorgu('SELECT * FROM projeler ORDER BY id DESC'))


@app.route('/admin/proje-ekle', methods=['GET', 'POST'])
@app.route('/admin/proje/<int:id>/duzenle', methods=['GET', 'POST'])
@personel_gerekli
def proje_ekle(id=None):
    kayit = sorgu('SELECT * FROM projeler WHERE id = ?', (id,), tek=True) if id else None
    if id and not kayit:
        abort(404)
    if request.method == 'POST':
        try:
            gorsel = _gorsel_al(mevcut=kayit['gorsel_url'] if kayit else '')
        except ValueError as e:
            flash(str(e), 'danger')
            return redirect(request.url)
        alanlar = (request.form['baslik'].strip(), request.form['icerik'].strip(), gorsel,
                   request.form.get('kategori', '').strip(), request.form.get('durum', 'Geliştirme'))
        if kayit:
            calistir('UPDATE projeler SET baslik=?, icerik=?, gorsel_url=?, kategori=?, durum=? WHERE id=?', alanlar + (id,))
            flash('Proje güncellendi.', 'success')
        else:
            calistir('INSERT INTO projeler (baslik, icerik, gorsel_url, kategori, durum) VALUES (?,?,?,?,?)', alanlar)
            flash('Proje eklendi.', 'success')
        return redirect(url_for('admin_projeler'))
    return render_template('proje_ekle.html', kayit=kayit)


@app.route('/admin/proje/<int:id>/sil', methods=['POST'])
@personel_gerekli
def admin_proje_sil(id):
    calistir('DELETE FROM projeler WHERE id = ?', (id,))
    flash('Proje silindi.', 'success')
    return redirect(url_for('admin_projeler'))


@app.route('/admin/ekip')
@personel_gerekli
def admin_ekip():
    return render_template('admin_liste.html', tur='ekip', baslik='Ekip Üyeleri',
                           kayitlar=sorgu('SELECT * FROM ekip_uyeleri ORDER BY id ASC'))


@app.route('/admin/personel-ekle', methods=['GET', 'POST'])
@app.route('/admin/personel/<int:id>/duzenle', methods=['GET', 'POST'])
@personel_gerekli
def personel_ekle(id=None):
    kayit = sorgu('SELECT * FROM ekip_uyeleri WHERE id = ?', (id,), tek=True) if id else None
    if id and not kayit:
        abort(404)
    if request.method == 'POST':
        try:
            gorsel = _gorsel_al(mevcut=kayit['gorsel_url'] if kayit else '')
        except ValueError as e:
            flash(str(e), 'danger')
            return redirect(request.url)
        hesap = request.form.get('kullanici_id', type=int) or None
        alanlar = (request.form['ad_soyad'].strip(), request.form['departman'].strip(), request.form['rutbe'].strip(),
                   gorsel, request.form['biyografi'].strip(), hesap,
                   request.form.get('linkedin', '').strip(), request.form.get('github', '').strip())
        if kayit:
            calistir('''UPDATE ekip_uyeleri SET ad_soyad=?, departman=?, rutbe=?, gorsel_url=?, biyografi=?,
                        kullanici_id=?, linkedin=?, github=? WHERE id=?''', alanlar + (id,))
            flash('Ekip üyesi güncellendi.', 'success')
        else:
            calistir('''INSERT INTO ekip_uyeleri (ad_soyad, departman, rutbe, gorsel_url, biyografi, kullanici_id, linkedin, github)
                        VALUES (?,?,?,?,?,?,?,?)''', alanlar)
            flash('Ekip üyesi eklendi.', 'success')
        return redirect(url_for('admin_ekip'))
    hesaplar = sorgu('SELECT id, ad_soyad, eposta FROM kullanicilar ORDER BY ad_soyad')
    return render_template('personel_ekle.html', kayit=kayit, hesaplar=hesaplar)


@app.route('/admin/personel/<int:id>/sil', methods=['POST'])
@personel_gerekli
def admin_personel_sil(id):
    calistir('DELETE FROM ekip_uyeleri WHERE id = ?', (id,))
    flash('Ekip üyesi silindi.', 'success')
    return redirect(url_for('admin_ekip'))


@app.route('/admin/gonderiler')
@personel_gerekli
def admin_gonderiler():
    return render_template('admin_liste.html', tur='gonderi', baslik='Topluluk Gönderileri',
                           kayitlar=sorgu(gonderi_sql()))


@app.route('/admin/destek')
@personel_gerekli
def admin_destek():
    return render_template('admin_destek.html', talepler=sorgu('SELECT * FROM destek_talepleri ORDER BY durum ASC, id DESC'))


@app.route('/admin/destek/<int:id>/durum', methods=['POST'])
@personel_gerekli
def admin_destek_durum(id):
    t = sorgu('SELECT * FROM destek_talepleri WHERE id = ?', (id,), tek=True)
    if t:
        yeni = 'kapali' if t['durum'] == 'acik' else 'acik'
        calistir('UPDATE destek_talepleri SET durum = ? WHERE id = ?', (yeni, id))
        if yeni == 'kapali' and t['kullanici_id']:
            bildirim_ekle(t['kullanici_id'], 'Destek talebin çözüldü olarak işaretlendi.', link='/ayarlar?sekme=destek',
                          gonderen_id=RESMI_HESAP_ID, tur='sistem')
            db().commit()
    return redirect(url_for('admin_destek'))


@app.route('/admin/duyuru', methods=['POST'])
@personel_gerekli
def admin_duyuru():
    metin = request.form.get('metin', '').strip()
    link = request.form.get('link', '').strip() or None
    if metin:
        for (uid,) in sorgu('SELECT id FROM kullanicilar'):
            bildirim_ekle(uid, metin, link=link, gonderen_id=RESMI_HESAP_ID if uid != RESMI_HESAP_ID else None, tur='duyuru')
        db().commit()
        flash('Duyuru tüm kullanıcılara bildirim olarak gönderildi.', 'success')
    return redirect(url_for('admin'))


if __name__ == '__main__':
    app.run(debug=True, port=5000)
