import sqlite3

# Veritabanına bağlan
conn = sqlite3.connect('aronsan.db')

# Yeni tabloyu oluştur
conn.execute('''
    CREATE TABLE IF NOT EXISTS ekip_uyeleri (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad_soyad TEXT NOT NULL,
        departman TEXT NOT NULL,
        rutbe TEXT NOT NULL,
        gorsel_url TEXT,
        biyografi TEXT NOT NULL
    )
''')

conn.commit()
conn.close()
print("Harika! Ekip üyeleri tablosu aronsan.db'ye başarıyla eklendi!")