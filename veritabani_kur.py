import sqlite3

def veritabani_kur():
    # Veritabanı dosyasına bağlan (yoksa otomatik oluşturur)
    baglanti = sqlite3.connect('aronsan.db')
    imlec = baglanti.cursor()

    # 1. Normal Kullanıcılar Tablosu
    imlec.execute('''
        CREATE TABLE IF NOT EXISTS kullanicilar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_soyad TEXT NOT NULL,
            eposta TEXT UNIQUE NOT NULL,
            sifre TEXT NOT NULL
        )
    ''')

    # 2. Personeller (Aronsan Ekibi) Tablosu
    imlec.execute('''
        CREATE TABLE IF NOT EXISTS personeller (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_soyad TEXT NOT NULL,
            eposta TEXT UNIQUE NOT NULL,
            sifre TEXT NOT NULL,
            rutbe TEXT DEFAULT 'Personel'
        )
    ''')

    # 3. Projelerimiz Tablosu
    imlec.execute('''
        CREATE TABLE IF NOT EXISTS projeler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            baslik TEXT NOT NULL,
            icerik TEXT NOT NULL,
            gorsel_url TEXT,
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 4. Savunma Sanayii Haberleri Tablosu
    imlec.execute('''
        CREATE TABLE IF NOT EXISTS haberler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            firma_adi TEXT NOT NULL,
            baslik TEXT NOT NULL,
            icerik TEXT NOT NULL,
            gorsel_url TEXT,
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Personel girişi için test hesabını otomatik ekleyelim
    try:
        imlec.execute("INSERT INTO personeller (ad_soyad, eposta, sifre, rutbe) VALUES (?, ?, ?, ?)", 
                      ('Admin', 'admin@aronsan.com', '123456', 'Yönetici'))
    except sqlite3.IntegrityError:
        pass # Eğer hesap zaten varsa hata vermemesi için

    baglanti.commit()
    baglanti.close()
    print("aronsan.db veritabanı ve tüm tablolar başarıyla oluşturuldu!")
    print("Test admin hesabı eklendi. (E-posta: admin@aronsan.com / Şifre: 123456)")

if __name__ == '__main__':
    veritabani_kur()