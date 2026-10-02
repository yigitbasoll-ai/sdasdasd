import sqlite3

conn = sqlite3.connect('aronsan.db')
c = conn.cursor()

# Bildirimler Tablosu
c.execute('''
    CREATE TABLE IF NOT EXISTS bildirimler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kullanici_id INTEGER NOT NULL,
        icerik TEXT NOT NULL,
        okundu INTEGER DEFAULT 0,
        tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Mesajlar tablosuna okundu sütunu güvencesi
try:
    c.execute("ALTER TABLE mesajlar ADD COLUMN okundu INTEGER DEFAULT 0")
except sqlite3.OperationalError:
    pass

conn.commit()
conn.close()
print("Bildirimler ve mesaj okundu altyapısı başarıyla kuruldu!")