import sqlite3

conn = sqlite3.connect('aronsan.db')
c = conn.cursor()

# 1. Eski ve eksik tabloyu tamamen sil (Test hesapları gidecek)
c.execute("DROP TABLE IF EXISTS kullanicilar")

# 2. Yeni, eksiksiz ve güncel tabloyu oluştur
c.execute('''
    CREATE TABLE kullanicilar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad_soyad TEXT NOT NULL,
        eposta TEXT UNIQUE NOT NULL,
        sifre TEXT NOT NULL,
        yetki TEXT NOT NULL
    )
''')

# Eğer test için hemen bir admin personeli istersen otomatik ekleyelim:
c.execute('''
    INSERT INTO kullanicilar (ad_soyad, eposta, sifre, yetki) 
    VALUES ('Admin Aronsan', 'admin@aronsan.com', '123456', 'personel')
''')

conn.commit()
conn.close()
print("Mükemmel! Kullanıcılar tablosu en güncel haliyle yeniden oluşturuldu.")