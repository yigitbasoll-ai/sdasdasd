import sqlite3

conn = sqlite3.connect('aronsan.db')
c = conn.cursor()

# Haber beğenilerini takip eden tablo
c.execute('''
    CREATE TABLE IF NOT EXISTS haber_begenileri (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        haber_id INTEGER NOT NULL,
        kullanici_id INTEGER NOT NULL,
        UNIQUE(haber_id, kullanici_id)
    )
''')

# Yorum beğenilerini takip eden tablo
c.execute('''
    CREATE TABLE IF NOT EXISTS yorum_begenileri (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        yorum_id INTEGER NOT NULL,
        kullanici_id INTEGER NOT NULL,
        UNIQUE(yorum_id, kullanici_id)
    )
''')

conn.commit()
conn.close()
print("Sosyal Ağ Aşama 1: Beğeni log tabloları başarıyla oluşturuldu!")