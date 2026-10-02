import sqlite3

conn = sqlite3.connect('aronsan.db')
c = conn.cursor()

c.execute('''
    CREATE TABLE IF NOT EXISTS mesajlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        gonderen_id INTEGER NOT NULL,
        alici_id INTEGER NOT NULL,
        icerik TEXT NOT NULL,
        okundu INTEGER DEFAULT 0,
        tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

conn.commit()
conn.close()
print("Mesajlar tablosu oluşturuldu!")