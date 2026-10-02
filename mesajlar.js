/* =========================================================
   ARONSAN — MESAJLAŞMA
========================================================= */
(function () {
    'use strict';
    const { api, toast, esc, avatarHTML, tikHTML, $, $$, rozetGuncelle } = window.Aronsan;
    const DM = window.DM || {};
    const ALICI = DM.aliciId;
    const GRUP_SURESI = 5 * 60 * 1000;
    const EMOJILER = ['😀', '😂', '🥰', '😍', '😎', '🤔', '😅', '😭', '😡', '😮', '🥳', '😴', '👍', '👎', '👏', '🙏', '💪', '👀', '🔥', '❤️', '💯', '🎉', '✅', '❌', '🚀', '✈️', '🛰️', '🛡️', '⚡', '🎯', '🤝', '☕'];
    const TEPKILER = ['❤️', '😂', '😮', '😢', '👍', '🔥'];

    /* ---------- SOHBET LİSTESİ ---------- */
    let sohbetler = DM.sohbetler || [];
    const listeEl = $('#sohbetListesi');
    const araInput = $('#sohbetAra');

    function listeCiz() {
        if (!listeEl) return;
        if (!sohbetler.length) {
            listeEl.innerHTML = '<div class="text-center text-muted small px-3 py-4"><i class="bi bi-chat-square-dots fs-3 d-block mb-2"></i>Henüz bir sohbetin yok.<br>Aşağıdan birini seçerek başla.</div>';
        } else {
            listeEl.innerHTML = '<div class="dm-bolum-baslik">Sohbetler</div>' + sohbetler.map((s) => `
                <a href="/mesajlar/${s.id}" class="dm-kisi ${s.id === ALICI ? 'aktif' : ''} ${s.okunmamis ? 'okunmamis' : ''}" data-ad="${esc((s.gorunen_ad + ' ' + s.ad_soyad).toLocaleLowerCase('tr'))}">
                    ${avatarHTML(s.profil_fotografi, 48, s.cevrimici)}
                    <div class="bilgi">
                        <div class="ust-satir"><span class="kisi-isim"><span>${esc(s.gorunen_ad)}</span>${tikHTML(s.mavi_tik)}</span><span class="zaman">${esc(s.zaman)}</span></div>
                        <div class="ust-satir"><span class="onizleme">${s.son_benim_okundu ? '<i class="bi bi-check2-all" style="color:var(--verified)"></i> ' : ''}${esc(s.onizleme)}</span>${s.okunmamis ? `<span class="okunmamis-sayi">${s.okunmamis}</span>` : ''}</div>
                    </div>
                </a>`).join('');
        }
        filtrele();
        const toplam = sohbetler.reduce((t, s) => t + (s.id === ALICI ? 0 : s.okunmamis), 0);
        rozetGuncelle('[data-mesaj-rozet]', toplam);
    }
    function filtrele() {
        const q = (araInput?.value || '').trim().toLocaleLowerCase('tr');
        const konusulan = new Set(sohbetler.map((s) => s.id));
        $$('#dmListe .dm-kisi').forEach((a) => {
            const id = parseInt(a.getAttribute('href').split('/').pop(), 10);
            if (a.closest('#oneriBolum') && konusulan.has(id)) { a.style.display = 'none'; return; }
            a.style.display = !q || (a.dataset.ad || '').includes(q) ? '' : 'none';
        });
        const oneri = $('#oneriBolum');
        if (oneri) oneri.style.display = $$('.dm-kisi', oneri).some((a) => a.style.display !== 'none') ? '' : 'none';
    }
    araInput?.addEventListener('input', filtrele);
    listeCiz();

    async function listeYenile() {
        const v = await api('/api/sohbetler');
        if (v.status === 'success') { sohbetler = v.sohbetler; listeCiz(); }
    }
    setInterval(() => { if (!document.hidden) listeYenile(); }, 7000);

    /* ---------- YENİ SOHBET MODALI ---------- */
    const kisiAra = $('#kisiAra'), kisiSonuc = $('#kisiSonuc');
    let araZaman;
    kisiAra?.addEventListener('input', () => {
        clearTimeout(araZaman);
        const q = kisiAra.value.trim();
        if (!q) { kisiSonuc.innerHTML = '<div class="text-center text-muted small py-4">Mesaj göndermek istediğin kişinin adını yaz.</div>'; return; }
        araZaman = setTimeout(async () => {
            const v = await api('/api/arama?q=' + encodeURIComponent(q));
            const benId = window.ARONSAN.kullanici?.id;
            const kisiler = (v.kisiler || []).filter((k) => k.id !== benId);
            kisiSonuc.innerHTML = kisiler.length ? kisiler.map((k) => `
                <a href="/mesajlar/${k.id}" class="kisi-satir text-reset">
                    ${avatarHTML(k.profil_fotografi, 46, k.cevrimici)}
                    <div class="bilgi"><span class="kisi-isim"><span>${esc(k.ad_soyad)}</span>${tikHTML(k.mavi_tik)}</span>${k.yetki === 'personel' ? '<span class="personel-rozet">EKİP</span>' : ''}<div class="alt">${k.cevrimici ? '<span style="color:var(--success)">● Çevrimiçi</span>' : 'Sohbet başlat'}</div></div>
                    <i class="bi bi-chevron-right text-muted"></i>
                </a>`).join('') : '<div class="text-center text-muted small py-4">Kimse bulunamadı.</div>';
        }, 220);
    });
    $('#yeniSohbetModal')?.addEventListener('shown.bs.modal', () => kisiAra.focus());

    if (!ALICI) return;

    /* ---------- MESAJ ALANI ---------- */
    const alan = $('#mesajAlani'), liste = $('#mesajListe'), yaziyorBalon = $('#yaziyorBalon');
    const input = $('#mesajInput'), gonderBtn = $('#gonderBtn'), yeniBtn = $('#yeniMsjBtn');
    let mesajlar = DM.mesajlar || [];
    const ts = (m) => Date.parse(String(m.tarih).replace(' ', 'T') + 'Z') || 0;
    const sonId = () => mesajlar.reduce((mx, m) => Math.max(mx, m.id), 0);
    const altta = () => alan.scrollHeight - alan.scrollTop - alan.clientHeight < 140;
    const asagiKaydir = (yumusak = true) => { alan.scrollTo({ top: alan.scrollHeight, behavior: yumusak ? 'smooth' : 'auto' }); yeniBtn.style.display = 'none'; };

    function gunEtiketi(m) {
        const d = new Date(ts(m)), bugun = new Date();
        const dun = new Date(); dun.setDate(bugun.getDate() - 1);
        if (d.toDateString() === bugun.toDateString()) return 'Bugün';
        if (d.toDateString() === dun.toDateString()) return 'Dün';
        return m.gun;
    }

    function mesajHTML(m, onceki, sonraki) {
        const ayniOnceki = onceki && onceki.benim === m.benim && ts(m) - ts(onceki) < GRUP_SURESI && gunEtiketi(onceki) === gunEtiketi(m);
        const ayniSonraki = sonraki && sonraki.benim === m.benim && ts(sonraki) - ts(m) < GRUP_SURESI && gunEtiketi(sonraki) === gunEtiketi(m);
        const sinif = ['msj', m.benim ? 'ben' : 'o', ayniOnceki ? 'devam' : 'ayri', ayniSonraki ? '' : 'son-grup', m.tepki ? 'tepkili' : ''].join(' ');
        let balon;
        if (m.silindi) {
            balon = `<div class="balon silinmis"><i class="bi bi-slash-circle me-1"></i>${m.benim ? 'Bu mesajı sildin' : 'Bu mesaj silindi'}</div>`;
        } else {
            const sadeceGorsel = m.gorsel_url && !m.icerik;
            balon = `<div class="balon ${sadeceGorsel ? 'sadece-gorsel' : ''}">${m.gorsel_url ? `<img src="${esc(m.gorsel_url)}" alt="Fotoğraf" loading="lazy">` : ''}${esc(m.icerik)}</div>`;
        }
        const okundu = m.benim ? `<i class="bi ${m.okundu ? 'bi-check2-all okundu' : 'bi-check2'} okundu-ikon" title="${m.okundu ? 'Görüldü' : 'Gönderildi'}"></i>` : '';
        const araclar = m.silindi ? '' : `<div class="msj-arac">
            <button data-tepki-ac title="Tepki ver"><i class="bi bi-emoji-smile"></i></button>
            ${m.benim ? '<button data-msj-sil title="Sil"><i class="bi bi-trash3"></i></button>' : ''}
        </div>`;
        return `<div class="${sinif}" data-id="${m.id}">${balon}${m.tepki ? `<span class="tepki-rozet" data-tepki-kaldir>${esc(m.tepki)}</span>` : ''}
            <div class="zaman-satir">${esc(m.saat)}${okundu}${m.benim && m.okundu && m === sonBenim() ? ' <span>Görüldü</span>' : ''}</div>${araclar}</div>`;
    }
    function sonBenim() { for (let i = mesajlar.length - 1; i >= 0; i--) if (mesajlar[i].benim) return mesajlar[i]; return null; }

    function ciz() {
        let h = '', gun = null;
        mesajlar.forEach((m, i) => {
            const g = gunEtiketi(m);
            if (g !== gun) { h += `<div class="d-flex justify-content-center"><span class="dm-gun">${esc(g)}</span></div>`; gun = g; }
            h += mesajHTML(m, mesajlar[i - 1], mesajlar[i + 1]);
        });
        liste.innerHTML = h;
        $('#sohbetBasi').style.display = mesajlar.length > 6 ? 'none' : '';
    }
    ciz();
    requestAnimationFrame(() => asagiKaydir(false));
    alan.addEventListener('scroll', () => { if (altta()) yeniBtn.style.display = 'none'; });
    yeniBtn.addEventListener('click', () => asagiKaydir());

    function mesajlariEkle(yeni, kendim = false) {
        const varolan = new Set(mesajlar.map((m) => m.id));
        const eklenecek = yeni.filter((m) => !varolan.has(m.id));
        if (!eklenecek.length) return;
        const asagida = altta();
        mesajlar = mesajlar.concat(eklenecek).sort((a, b) => a.id - b.id);
        ciz();
        if (asagida || kendim) asagiKaydir();
        else if (eklenecek.some((m) => !m.benim)) yeniBtn.style.display = 'inline-flex';
    }

    /* ---------- GÖNDERME ---------- */
    const dosyaInput = $('#dmDosya'), onizleme = $('#dmOnizleme');
    let seciliDosya = null;
    function gonderDurumu() { gonderBtn.disabled = !(input.value.trim() || seciliDosya); }
    function boyutla() { input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 140) + 'px'; }

    let sonYaziyor = 0;
    input?.addEventListener('input', () => {
        boyutla(); gonderDurumu();
        if (input.value.trim() && Date.now() - sonYaziyor > 2500) { sonYaziyor = Date.now(); api('/api/yaziyor', { method: 'POST', json: { alici_id: ALICI } }); }
    });
    input?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); gonder(); }
    });
    gonderBtn?.addEventListener('click', gonder);

    dosyaInput?.addEventListener('change', () => {
        const f = dosyaInput.files[0];
        if (!f) return;
        if (!f.type.startsWith('image/')) { toast('Yalnızca görsel gönderebilirsin.', 'warning'); dosyaInput.value = ''; return; }
        if (f.size > 16 * 1024 * 1024) { toast('Dosya 16 MB sınırını aşıyor.', 'warning'); dosyaInput.value = ''; return; }
        seciliDosya = f;
        const r = new FileReader();
        r.onload = (e) => { $('img', onizleme).src = e.target.result; };
        r.readAsDataURL(f);
        $('#dmDosyaAd').textContent = f.name;
        onizleme.classList.add('goster');
        gonderDurumu(); input.focus();
    });
    $('#dmOnizlemeKaldir')?.addEventListener('click', () => { seciliDosya = null; dosyaInput.value = ''; onizleme.classList.remove('goster'); gonderDurumu(); });

    let gonderiliyor = false;
    async function gonder() {
        const icerik = input.value.trim();
        if ((!icerik && !seciliDosya) || gonderiliyor) return;
        gonderiliyor = true; gonderBtn.disabled = true;
        let v;
        if (seciliDosya) {
            const fd = new FormData();
            fd.append('alici_id', ALICI); fd.append('icerik', icerik); fd.append('gorsel', seciliDosya);
            v = await api('/api/mesaj_gonder', { method: 'POST', form: fd });
        } else {
            v = await api('/api/mesaj_gonder', { method: 'POST', json: { alici_id: ALICI, icerik } });
        }
        gonderiliyor = false;
        if (v.status !== 'success') { gonderDurumu(); return toast(v.mesaj || 'Mesaj gönderilemedi.', 'danger'); }
        input.value = ''; boyutla();
        if (seciliDosya) { seciliDosya = null; dosyaInput.value = ''; onizleme.classList.remove('goster'); }
        gonderDurumu();
        mesajlariEkle([v.mesaj], true);
        input.focus();
        listeYenile();
    }

    /* ---------- EMOJİ ---------- */
    const emojiPanel = $('#emojiPanel');
    if (emojiPanel) {
        emojiPanel.innerHTML = EMOJILER.map((e) => `<button type="button">${e}</button>`).join('');
        $('#emojiBtn').addEventListener('click', (e) => { e.stopPropagation(); emojiPanel.classList.toggle('acik'); });
        emojiPanel.addEventListener('click', (e) => {
            const b = e.target.closest('button');
            if (!b) return;
            const bas = input.selectionStart ?? input.value.length, son = input.selectionEnd ?? input.value.length;
            input.value = input.value.slice(0, bas) + b.textContent + input.value.slice(son);
            input.selectionStart = input.selectionEnd = bas + b.textContent.length;
            input.focus(); gonderDurumu(); boyutla();
        });
        document.addEventListener('click', (e) => { if (!e.target.closest('#emojiPanel, #emojiBtn')) emojiPanel.classList.remove('acik'); });
    }

    /* ---------- TEPKİ & SİLME ---------- */
    async function tepkiVer(id, tepki) {
        const v = await api(`/api/mesaj/${id}/tepki`, { method: 'POST', json: { tepki } });
        if (v.status !== 'success') return toast(v.mesaj || 'Tepki verilemedi.', 'danger');
        const m = mesajlar.find((x) => x.id === id);
        if (m) { m.tepki = v.tepki; const asagida = altta(); ciz(); if (asagida) asagiKaydir(false); }
    }
    liste.addEventListener('dblclick', (e) => {
        const msj = e.target.closest('.msj');
        if (!msj || e.target.closest('img') || msj.querySelector('.silinmis')) return;
        tepkiVer(parseInt(msj.dataset.id, 10), '❤️');
    });
    liste.addEventListener('click', async (e) => {
        const msj = e.target.closest('.msj');
        if (!msj) return;
        const id = parseInt(msj.dataset.id, 10);
        if (e.target.closest('[data-tepki-ac]')) {
            $$('.tepki-secici').forEach((t) => t.remove());
            const secici = document.createElement('div');
            secici.className = 'tepki-secici';
            secici.innerHTML = TEPKILER.map((t) => `<button type="button">${t}</button>`).join('');
            msj.appendChild(secici);
            secici.addEventListener('click', (ev) => { const b = ev.target.closest('button'); if (b) { secici.remove(); tepkiVer(id, b.textContent); } });
            return;
        }
        if (e.target.closest('[data-tepki-kaldir]')) {
            const m = mesajlar.find((x) => x.id === id);
            if (m) tepkiVer(id, m.tepki);
            return;
        }
        if (e.target.closest('[data-msj-sil]')) {
            if (!confirm('Bu mesaj herkes için silinsin mi?')) return;
            const v = await api(`/api/mesaj/${id}/sil`, { method: 'POST' });
            if (v.status !== 'success') return toast(v.mesaj || 'Silinemedi.', 'danger');
            const m = mesajlar.find((x) => x.id === id);
            if (m) { Object.assign(m, { silindi: true, icerik: '', gorsel_url: '', tepki: '' }); ciz(); }
            listeYenile();
        }
    });
    document.addEventListener('click', (e) => { if (!e.target.closest('.tepki-secici, [data-tepki-ac]')) $$('.tepki-secici').forEach((t) => t.remove()); });

    /* ---------- CANLI GÜNCELLEME ---------- */
    const durumEl = $('#durumMetni');
    const varsayilanDurum = durumEl?.textContent || '';
    let sorguda = false;
    async function yokla() {
        if (sorguda) return;
        sorguda = true;
        const v = await api(`/api/mesajlar/${ALICI}?son=${sonId()}`);
        sorguda = false;
        if (v.status !== 'success') return;
        if (v.mesajlar.length) mesajlariEkle(v.mesajlar);
        let degisti = false;
        v.durumlar.forEach((d) => {
            const m = mesajlar.find((x) => x.id === d.id);
            if (!m) return;
            if (m.okundu !== d.okundu || m.silindi !== d.silindi || m.tepki !== d.tepki) {
                m.okundu = d.okundu; m.tepki = d.tepki;
                if (d.silindi && !m.silindi) Object.assign(m, { silindi: true, icerik: '', gorsel_url: '' });
                degisti = true;
            }
        });
        if (degisti) { const asagida = altta(); ciz(); if (asagida) asagiKaydir(false); }

        const asagida = altta();
        yaziyorBalon.classList.toggle('goster', v.yaziyor);
        if (v.yaziyor && asagida) asagiKaydir();
        if (durumEl) {
            if (v.yaziyor) { durumEl.textContent = 'yazıyor...'; durumEl.className = 'durum cevrimici'; }
            else { durumEl.textContent = v.durum_metni || varsayilanDurum; durumEl.className = 'durum ' + (v.cevrimici ? 'cevrimici' : ''); }
        }
        const nokta = $('#ustAvatar .cevrimici-nokta');
        if (v.cevrimici && !nokta) $('#ustAvatar .avatar')?.insertAdjacentHTML('beforeend', '<span class="cevrimici-nokta"></span>');
        else if (!v.cevrimici && nokta) nokta.remove();
    }
    let aralik = setInterval(yokla, 2500);
    document.addEventListener('visibilitychange', () => {
        clearInterval(aralik);
        aralik = setInterval(yokla, document.hidden ? 12000 : 2500);
        if (!document.hidden) { yokla(); listeYenile(); }
    });

    /* ---------- SOHBET AYARLARI ---------- */
    const sohbetEl = $('#dmSohbet');
    $$('input[name="sohbetTema"]').forEach((r) => r.addEventListener('change', () => { sohbetEl.dataset.tema = r.value; }));
    const baslangicTema = sohbetEl.dataset.tema;
    $('#sohbetAyarModal')?.addEventListener('hidden.bs.modal', () => {
        if (!$('#sohbetAyarModal').dataset.kaydedildi) sohbetEl.dataset.tema = sohbetEl.dataset.kayitliTema || baslangicTema;
        delete $('#sohbetAyarModal').dataset.kaydedildi;
    });
    $('#ayarKaydet')?.addEventListener('click', async () => {
        const tema = $('input[name="sohbetTema"]:checked')?.value || 'default';
        const takma_ad = $('#takmaAdInput').value.trim();
        const v = await api('/api/sohbet_ayar', { method: 'POST', json: { alici_id: ALICI, tema, takma_ad } });
        if (v.status !== 'success') return toast(v.mesaj || 'Kaydedilemedi.', 'danger');
        $('#sohbetAyarModal').dataset.kaydedildi = '1';
        sohbetEl.dataset.tema = v.tema; sohbetEl.dataset.kayitliTema = v.tema;
        $('#baslikAd').textContent = v.takma_ad || DM.varsayilanAd;
        bootstrap.Modal.getInstance($('#sohbetAyarModal')).hide();
        toast('Sohbet ayarları kaydedildi.', 'success');
        listeYenile();
    });

    input?.focus();
})();
