import sqlite3

conn = sqlite3.connect('aronsan.db')
c = conn.cursor()

# Haberler tablosuna yeni sütunlar ekleyelim (Eğer yoksa)
try:
    c.execute("ALTER TABLE haberler ADD COLUMN goruntulenme INTEGER DEFAULT 0")
    c.execute("ALTER TABLE haberler ADD COLUMN begeni INTEGER DEFAULT 0")
except sqlite3.OperationalError:
    pass # Sütunlar zaten varsa hata verme, devam et

# Yorumlar tablosunu oluşturalım
c.execute('''
    CREATE TABLE IF NOT EXISTS haber_yorumlari (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        haber_id INTEGER NOT NULL,
        kullanici_ad TEXT NOT NULL,
        yorum TEXT NOT NULL,
        begeni INTEGER DEFAULT 0,
        tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

conn.commit()
conn.close()
print("Mükemmel! Veritabanı haber etkileşimleri için güncellendi!")