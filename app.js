/* =========================================================
   ARONSAN — ORTAK İSTEMCİ KODU
========================================================= */
(function () {
    'use strict';

    const $ = (s, el = document) => el.querySelector(s);
    const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
    const CSRF = document.querySelector('meta[name="csrf-token"]')?.content || '';
    const KULLANICI = (window.ARONSAN || {}).kullanici;
    const AVATAR_YEDEK = (window.ARONSAN || {}).avatarYedek || '';

    /* ---------- Yardımcılar ---------- */
    const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    const tikHTML = (v) => (v ? '<i class="bi bi-patch-check-fill mavi-tik" title="Onaylı hesap"></i>' : '');
    const avatarHTML = (url, boyut = 40, cevrimici = false, halka = false) =>
        `<span class="avatar ${halka ? 'halka' : ''}" style="--s:${boyut}px"><img src="${esc(url || AVATAR_YEDEK)}" alt="" loading="lazy" onerror="this.onerror=null;this.src='${AVATAR_YEDEK}'">${cevrimici ? '<span class="cevrimici-nokta"></span>' : ''}</span>`;
    const isimHTML = (k, link = true, ad = null) => {
        const ic = `<span>${esc(ad || k.ad_soyad)}</span>${tikHTML(k.mavi_tik)}`;
        return link ? `<a href="/profil/${k.id}" class="kisi-isim">${ic}</a>` : `<span class="kisi-isim">${ic}</span>`;
    };

    async function api(url, { method = 'GET', json, form } = {}) {
        const opts = { method, headers: { 'X-CSRF-Token': CSRF, 'X-Requested-With': 'fetch' } };
        if (json !== undefined) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(json); }
        if (form) opts.body = form;
        let veri;
        try {
            const res = await fetch(url, opts);
            veri = await res.json().catch(() => ({ status: 'error', mesaj: 'Beklenmeyen yanıt.' }));
            if (res.status === 401) { girisIste(); }
        } catch (e) {
            veri = { status: 'error', mesaj: 'Bağlantı hatası. İnternetinizi kontrol edin.' };
        }
        return veri;
    }

    function girisIste() {
        toast('Bu işlem için giriş yapmalısınız.', 'warning', { link: '/giris?next=' + encodeURIComponent(location.pathname), linkMetin: 'Giriş yap' });
    }

    const TOAST_IKON = { success: 'bi-check-circle-fill', danger: 'bi-x-octagon-fill', warning: 'bi-exclamation-triangle-fill', info: 'bi-info-circle-fill', message: 'bi-info-circle-fill' };
    function toast(mesaj, tur = 'info', ek = {}) {
        if (tur === 'message') tur = 'info';
        const alan = $('#toastAlani');
        if (!alan) return;
        const el = document.createElement('div');
        el.className = `bildirim-toast ${tur}`;
        el.setAttribute('role', 'status');
        el.innerHTML = `<i class="bi ${TOAST_IKON[tur] || TOAST_IKON.info} ikon"></i>
            <div class="flex-grow-1">${esc(mesaj)}${ek.link ? ` <a href="${ek.link}" class="fw-semibold ms-1">${esc(ek.linkMetin || 'Git')}</a>` : ''}</div>
            <button class="kapat" aria-label="Kapat"><i class="bi bi-x-lg"></i></button><span class="sure"></span>`;
        alan.appendChild(el);
        const kapat = () => { el.classList.add('cikis'); setTimeout(() => el.remove(), 350); };
        el.querySelector('.kapat').onclick = kapat;
        setTimeout(kapat, 4500);
    }

    function kopyala(metin) {
        const bitti = () => toast('Bağlantı panoya kopyalandı.', 'success');
        if (navigator.share && /Mobi|Android/i.test(navigator.userAgent)) {
            navigator.share({ url: metin }).catch(() => {});
            return;
        }
        if (navigator.clipboard) navigator.clipboard.writeText(metin).then(bitti, () => prompt('Bağlantıyı kopyalayın:', metin));
        else prompt('Bağlantıyı kopyalayın:', metin);
    }

    function butonYukleniyor(btn, durum) {
        if (!btn) return;
        if (durum) {
            btn.dataset.eskiHtml = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border" role="status"></span>';
        } else if (btn.dataset.eskiHtml) {
            btn.disabled = false;
            btn.innerHTML = btn.dataset.eskiHtml;
        }
    }

    window.Aronsan = { api, toast, esc, tikHTML, avatarHTML, isimHTML, kopyala, butonYukleniyor, $, $$ };

    /* ---------- Flash mesajları ---------- */
    try {
        JSON.parse($('#flashVeri')?.textContent || '[]').forEach(([tur, mesaj], i) => setTimeout(() => toast(mesaj, tur), 250 + i * 150));
    } catch (e) {}

    /* ---------- Tema ---------- */
    const TEMALAR = ['dark', 'light'];
    function temaUygula(t) {
        const d = document.documentElement;
        let gercek = t;
        if (t === 'sistem') gercek = matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
        d.dataset.theme = gercek;
        d.setAttribute('data-bs-theme', gercek === 'light' ? 'light' : 'dark');
        localStorage.setItem('aronsan_theme', t);
        arkaplanUygula(localStorage.getItem('aronsan_bg') || '');
        document.dispatchEvent(new CustomEvent('aronsan:tema', { detail: gercek }));
    }
    function arkaplanUygula(url) {
        const b = document.body;
        if (url) {
            const light = document.documentElement.dataset.theme === 'light';
            const ortu = light ? 'rgba(243,246,251,.88)' : 'rgba(6,10,19,.9)';
            b.style.backgroundImage = `linear-gradient(${ortu}, ${ortu}), url('${url.replace(/'/g, '')}')`;
            b.classList.add('has-bg-image');
        } else {
            b.style.backgroundImage = '';
            b.classList.remove('has-bg-image');
        }
    }
    arkaplanUygula(localStorage.getItem('aronsan_bg') || '');
    $$('[data-tema-degistir]').forEach((b) => b.addEventListener('click', () => {
        const simdi = document.documentElement.dataset.theme;
        const yeni = simdi === 'light' ? 'dark' : 'light';
        temaUygula(yeni);
        toast(yeni === 'light' ? 'Açık temaya geçildi.' : 'Koyu temaya geçildi.', 'info');
    }));
    window.Aronsan.temaUygula = temaUygula;
    window.Aronsan.arkaplanUygula = arkaplanUygula;

    /* ---------- Navbar, kaydırma, yukarı çık ---------- */
    const nav = $('#anaNav'), scrollBar = $('#scrollIlerleme'), geri = $('#geriDon');
    let tikliyor = false;
    function kaydirma() {
        const y = window.scrollY;
        nav?.classList.toggle('kucuk', y > 20);
        geri?.classList.toggle('goster', y > 600);
        if (scrollBar) {
            const h = document.documentElement.scrollHeight - innerHeight;
            scrollBar.style.width = (h > 0 ? (y / h) * 100 : 0) + '%';
        }
        tikliyor = false;
    }
    addEventListener('scroll', () => { if (!tikliyor) { requestAnimationFrame(kaydirma); tikliyor = true; } }, { passive: true });
    kaydirma();
    geri?.addEventListener('click', () => scrollTo({ top: 0, behavior: 'smooth' }));

    const mobilPanel = $('#mobilPanel');
    $('#mobilMenuAc')?.addEventListener('click', () => { mobilPanel.classList.add('acik'); document.body.style.overflow = 'hidden'; });
    const mobilKapat = () => { mobilPanel?.classList.remove('acik'); document.body.style.overflow = ''; };
    $('#mobilMenuKapat')?.addEventListener('click', mobilKapat);
    mobilPanel?.addEventListener('click', (e) => { if (e.target === mobilPanel) mobilKapat(); });

    /* Sayfa geçiş çubuğu */
    const ilerleme = $('#sayfaIlerleme');
    document.addEventListener('click', (e) => {
        const a = e.target.closest('a[href]');
        if (!a || e.ctrlKey || e.metaKey || e.shiftKey || a.target === '_blank' || a.hasAttribute('download')) return;
        const href = a.getAttribute('href');
        if (!href || href.startsWith('#') || href.startsWith('javascript') || a.dataset.bsToggle) return;
        if (a.origin !== location.origin) return;
        if (ilerleme) { ilerleme.style.opacity = 1; ilerleme.style.width = '70%'; }
    });
    addEventListener('pageshow', () => { if (ilerleme) { ilerleme.style.width = '100%'; setTimeout(() => { ilerleme.style.opacity = 0; ilerleme.style.width = '0'; }, 300); } });

    /* ---------- Görünüm animasyonları ---------- */
    const gozlemci = 'IntersectionObserver' in window ? new IntersectionObserver((girisler) => {
        girisler.forEach((g) => {
            if (g.isIntersecting) {
                g.target.classList.add('gorundu');
                if (g.target.dataset.sayacHedef !== undefined) sayacBaslat(g.target);
                gozlemci.unobserve(g.target);
            }
        });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }) : null;
    function gozle(kok = document) {
        $$('[data-reveal]:not(.gorundu), [data-sayac-hedef]', kok).forEach((el) => {
            if (gozlemci) gozlemci.observe(el); else { el.classList.add('gorundu'); if (el.dataset.sayacHedef !== undefined) sayacBaslat(el); }
        });
    }
    function sayacBaslat(el) {
        const hedef = parseInt(el.dataset.sayacHedef, 10) || 0;
        const ek = el.dataset.sayacEk || '';
        const sure = 1600, bas = performance.now();
        const adim = (t) => {
            const p = Math.min((t - bas) / sure, 1);
            const e = 1 - Math.pow(1 - p, 4);
            el.textContent = Math.round(hedef * e).toLocaleString('tr-TR') + ek;
            if (p < 1) requestAnimationFrame(adim);
        };
        requestAnimationFrame(adim);
    }
    gozle();
    window.Aronsan.gozle = gozle;

    /* Tilt efekti */
    if (matchMedia('(hover: hover)').matches) {
        $$('[data-tilt]').forEach((el) => {
            el.addEventListener('mousemove', (e) => {
                const r = el.getBoundingClientRect();
                const x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
                el.style.transform = `perspective(900px) rotateY(${x * 8}deg) rotateX(${-y * 8}deg) translateY(-4px)`;
            });
            el.addEventListener('mouseleave', () => { el.style.transform = ''; });
        });
    }

    /* ---------- Canlı arama ---------- */
    const aramaInput = $('#aramaInput'), aramaSonuc = $('#aramaSonuc');
    if (aramaInput && aramaSonuc) {
        let zamanlayici, secili = -1;
        const kapat = () => { aramaSonuc.classList.remove('acik'); secili = -1; };
        aramaInput.addEventListener('input', () => {
            clearTimeout(zamanlayici);
            const q = aramaInput.value.trim();
            if (!q) return kapat();
            zamanlayici = setTimeout(async () => {
                const v = await api('/api/arama?q=' + encodeURIComponent(q));
                let h = '';
                if (v.kisiler?.length) {
                    h += '<div class="grup">Kişiler</div>' + v.kisiler.map((k) =>
                        `<a href="/profil/${k.id}">${avatarHTML(k.profil_fotografi, 38, k.cevrimici)}<span class="kisi-isim"><span>${esc(k.ad_soyad)}</span>${tikHTML(k.mavi_tik)}</span>${k.yetki === 'personel' ? '<span class="personel-rozet">EKİP</span>' : ''}</a>`).join('');
                }
                if (v.haberler?.length) {
                    h += '<div class="grup">Haberler</div>' + v.haberler.map((x) =>
                        `<a href="/haber/${x.id}">${x.gorsel_url ? `<img class="kucuk-gorsel" src="${esc(x.gorsel_url)}" alt="">` : '<span class="kucuk-gorsel"><i class="bi bi-newspaper"></i></span>'}<span class="text-truncate">${esc(x.baslik)}<small class="d-block text-muted">${esc(x.firma_adi)}</small></span></a>`).join('');
                }
                if (v.projeler?.length) {
                    h += '<div class="grup">Projeler</div>' + v.projeler.map((x) =>
                        `<a href="/proje/${x.id}"><span class="kucuk-gorsel"><i class="bi bi-rocket-takeoff"></i></span><span class="text-truncate">${esc(x.baslik)}</span></a>`).join('');
                }
                h = h ? h + `<a href="/ara?q=${encodeURIComponent(q)}" class="justify-content-center fw-semibold" style="color:var(--primary)">Tüm sonuçları gör <i class="bi bi-arrow-right"></i></a>`
                    : `<div class="p-4 text-center text-muted"><i class="bi bi-search fs-3 d-block mb-2"></i>"${esc(q)}" için sonuç bulunamadı.</div>`;
                aramaSonuc.innerHTML = h;
                aramaSonuc.classList.add('acik');
                secili = -1;
            }, 220);
        });
        aramaInput.addEventListener('keydown', (e) => {
            const ogeler = $$('a', aramaSonuc);
            if (!ogeler.length) return;
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                e.preventDefault();
                secili = (secili + (e.key === 'ArrowDown' ? 1 : -1) + ogeler.length) % ogeler.length;
                ogeler.forEach((o, i) => o.classList.toggle('secili', i === secili));
            } else if (e.key === 'Enter' && secili >= 0) {
                e.preventDefault(); location.href = ogeler[secili].href;
            } else if (e.key === 'Escape') { kapat(); aramaInput.blur(); }
        });
        aramaInput.addEventListener('focus', () => { if (aramaInput.value.trim() && aramaSonuc.innerHTML) aramaSonuc.classList.add('acik'); });
        document.addEventListener('click', (e) => { if (!e.target.closest('.nav-arama')) kapat(); });
        document.addEventListener('keydown', (e) => {
            if (e.key === '/' && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName) && !document.activeElement.isContentEditable) {
                e.preventDefault(); aramaInput.focus();
            }
        });
    }

    /* ---------- Bildirimler ---------- */
    const BILDIRIM_IKON = { takip: 'bi-person-plus-fill', begeni: 'bi-heart-fill', yorum: 'bi-chat-fill', gonderi: 'bi-image', sistem: 'bi-shield-check', duyuru: 'bi-megaphone-fill', genel: 'bi-bell-fill' };
    function rozetGuncelle(sel, sayi) {
        $$(sel).forEach((r) => { r.dataset.sayi = sayi; r.textContent = sayi > 0 ? (sayi > 99 ? '99+' : sayi) : ''; });
    }
    window.Aronsan.rozetGuncelle = rozetGuncelle;
    async function bildirimleriYukle() {
        const liste = $('#bildirimListe');
        const v = await api('/api/bildirimler');
        if (v.status !== 'success') return;
        if (!v.bildirimler.length) {
            liste.innerHTML = '<div class="bos-durum py-5"><div class="ikon"><i class="bi bi-bell-slash"></i></div><h6 class="fw-bold" style="color:var(--text)">Her şey yolunda</h6><p class="small mb-0">Yeni bildirimin yok.</p></div>';
            return;
        }
        liste.innerHTML = v.bildirimler.map((b) => {
            const g = b.gonderen;
            const sol = g ? avatarHTML(g.profil_fotografi, 40) : `<span class="bildirim-ikon"><i class="bi ${BILDIRIM_IKON[b.tur] || BILDIRIM_IKON.genel}"></i></span>`;
            const metin = g ? `<strong class="kisi-isim d-inline-flex"><span>${esc(g.ad_soyad)}</span>${tikHTML(g.mavi_tik)}</strong> ${esc(b.icerik)}` : esc(b.icerik);
            return `<div class="bildirim-oge ${b.okundu ? '' : 'yeni'}" data-link="${esc(b.link)}" data-id="${b.id}">
                ${sol}<div class="metin">${metin}<div class="zaman"><i class="bi ${BILDIRIM_IKON[b.tur] || 'bi-bell'} me-1"></i>${esc(b.zaman)}</div></div>
                <button class="sil" title="Sil" aria-label="Bildirimi sil"><i class="bi bi-x-lg"></i></button></div>`;
        }).join('');
        api('/api/bildirimleri_okudum', { method: 'POST' }).then(() => rozetGuncelle('#bildirimRozet', 0));
    }
    const bildirimDD = $('#bildirimDropdown');
    if (bildirimDD) {
        bildirimDD.addEventListener('show.bs.dropdown', bildirimleriYukle);
        $('#bildirimListe').addEventListener('click', async (e) => {
            const oge = e.target.closest('.bildirim-oge');
            if (!oge) return;
            if (e.target.closest('.sil')) {
                e.stopPropagation();
                oge.style.transition = 'all .3s'; oge.style.opacity = 0; oge.style.transform = 'translateX(30px)';
                await api(`/api/bildirim/sil/${oge.dataset.id}`, { method: 'POST' });
                setTimeout(() => { oge.remove(); if (!$('.bildirim-oge', $('#bildirimListe'))) bildirimleriYukle(); }, 300);
                return;
            }
            if (oge.dataset.link) location.href = oge.dataset.link;
        });
        $('#bildirimTemizle').addEventListener('click', async () => {
            const v = await api('/api/bildirim/sil_tumu', { method: 'POST' });
            if (v.status === 'success') { bildirimleriYukle(); toast('Tüm bildirimler temizlendi.', 'success'); }
        });
    }
    const asilBaslik = document.title;
    function baslikGuncelle(sayi) {
        const acik = localStorage.getItem('aronsan_baslik_sayac') !== '0';
        document.title = acik && sayi > 0 ? `(${sayi}) ${asilBaslik}` : asilBaslik;
    }
    if (KULLANICI) {
        let oncekiMesaj = parseInt($('[data-mesaj-rozet]')?.dataset.sayi || '0', 10);
        baslikGuncelle(parseInt($('#bildirimRozet')?.dataset.sayi || '0', 10) + oncekiMesaj);
        setInterval(async () => {
            if (document.hidden) return;
            const v = await api('/api/sayaclar');
            if (v.status !== 'success') return;
            rozetGuncelle('#bildirimRozet', v.bildirim);
            if (!location.pathname.startsWith('/mesajlar')) {
                if (v.mesaj > oncekiMesaj && localStorage.getItem('aronsan_msj_toast') !== '0') toast('Yeni bir mesajın var.', 'info', { link: '/mesajlar', linkMetin: 'Görüntüle' });
                rozetGuncelle('[data-mesaj-rozet]', v.mesaj);
            }
            baslikGuncelle(v.bildirim + v.mesaj);
            oncekiMesaj = v.mesaj;
        }, 25000);
    }

    /* ---------- Takip butonları ---------- */
    function takipButonuAyarla(btn, takipEdiyor) {
        btn.dataset.durum = takipEdiyor ? '1' : '0';
        if (btn.dataset.stil === 'buyuk') {
            btn.className = `btn ${takipEdiyor ? 'btn-ghost' : 'btn-primary'}`;
            btn.innerHTML = takipEdiyor ? '<i class="bi bi-person-check"></i>Takip ediliyor' : '<i class="bi bi-person-plus"></i>Takip Et';
        } else if (btn.dataset.stil === 'link') {
            btn.textContent = takipEdiyor ? 'Takip ediliyor' : 'Takip Et';
            btn.style.color = takipEdiyor ? 'var(--muted)' : 'var(--primary)';
        } else {
            btn.className = `btn btn-sm btn-pill ${takipEdiyor ? 'btn-ghost' : 'btn-outline-primary'}`;
            btn.textContent = takipEdiyor ? 'Takip ediliyor' : 'Takip Et';
        }
    }
    $$('[data-takip][data-durum]').forEach((b) => takipButonuAyarla(b, b.dataset.durum === '1'));
    document.addEventListener('click', async (e) => {
        const btn = e.target.closest('[data-takip]');
        if (!btn) return;
        e.preventDefault();
        if (!KULLANICI) return girisIste();
        btn.disabled = true;
        const v = await api(`/api/takip/${btn.dataset.takip}`, { method: 'POST' });
        btn.disabled = false;
        if (v.status !== 'success') return v.mesaj && toast(v.mesaj, 'danger');
        const takip = v.durum === 'takip_edildi';
        $$(`[data-takip="${btn.dataset.takip}"]`).forEach((b) => takipButonuAyarla(b, takip));
        const sayac = $(`[data-takipci-sayi="${btn.dataset.takip}"]`);
        if (sayac) sayac.textContent = v.takipci_sayisi;
        if (takip) toast('Takip etmeye başladın.', 'success');
    });

    /* ---------- Takipçi listesi modalı ---------- */
    let takipModal;
    document.addEventListener('click', async (e) => {
        const btn = e.target.closest('[data-takip-liste]');
        if (!btn) return;
        const modalEl = $('#takipModal');
        takipModal = takipModal || new bootstrap.Modal(modalEl);
        $('#takipModalBaslik').textContent = btn.dataset.tur === 'takip_edilenler' ? 'Takip edilenler' : 'Takipçiler';
        const liste = $('#takipListe');
        $('#takipAra').value = '';
        liste.innerHTML = '<div class="iskelet mb-2" style="height:56px"></div>'.repeat(4);
        takipModal.show();
        const v = await api(`/api/takip_listesi/${btn.dataset.takipListe}?tur=${btn.dataset.tur}`);
        if (!v.liste?.length) {
            liste.innerHTML = `<div class="bos-durum py-4"><div class="ikon"><i class="bi bi-people"></i></div><p class="mb-0">${btn.dataset.tur === 'takip_edilenler' ? 'Henüz kimseyi takip etmiyor.' : 'Henüz takipçisi yok.'}</p></div>`;
            return;
        }
        liste.innerHTML = v.liste.map((k) => `<div class="kisi-satir" data-ad="${esc(k.ad_soyad.toLocaleLowerCase('tr'))}">
            <a href="/profil/${k.id}">${avatarHTML(k.profil_fotografi, 46, k.cevrimici)}</a>
            <div class="bilgi">${isimHTML(k)}<div class="alt">${esc(k.biyografi || '')}</div></div>
            ${KULLANICI && !k.ben ? `<button class="btn btn-sm btn-pill" data-takip="${k.id}" data-durum="${k.takip_ediyorum ? 1 : 0}"></button>` : ''}
        </div>`).join('');
        $$('[data-takip][data-durum]', liste).forEach((b) => takipButonuAyarla(b, b.dataset.durum === '1'));
    });
    $('#takipAra')?.addEventListener('input', (e) => {
        const q = e.target.value.trim().toLocaleLowerCase('tr');
        $$('#takipListe .kisi-satir').forEach((s) => { s.style.display = s.dataset.ad.includes(q) ? '' : 'none'; });
    });

    /* ---------- Gönderi etkileşimleri ---------- */
    async function gonderiBegen(id, zorlaBegen = false) {
        if (!KULLANICI) return girisIste();
        const btnler = $$(`[data-gonderi-begen="${id}"]`);
        if (zorlaBegen && btnler[0]?.classList.contains('aktif')) return;
        const v = await api(`/api/gonderi/${id}/begen`, { method: 'POST' });
        if (v.status !== 'success') return;
        btnler.forEach((b) => {
            b.classList.toggle('aktif', v.begendim);
            b.querySelector('i').className = `bi ${v.begendim ? 'bi-heart-fill' : 'bi-heart'}`;
        });
        $$(`[data-begeni-sayi="${id}"]`).forEach((s) => (s.textContent = v.begeni));
    }
    document.addEventListener('click', (e) => {
        const b = e.target.closest('[data-gonderi-begen]');
        if (b) { e.preventDefault(); gonderiBegen(b.dataset.gonderiBegen); }
    });

    let tiklamaZamani = null;
    document.addEventListener('click', (e) => {
        const medya = e.target.closest('[data-cift-begen]');
        const acici = e.target.closest('[data-gonderi-ac]');
        if (medya) {
            if (tiklamaZamani) {
                clearTimeout(tiklamaZamani); tiklamaZamani = null;
                const kalp = medya.querySelector('.cift-tik-kalp');
                if (kalp) { kalp.classList.remove('oynat'); void kalp.offsetWidth; kalp.classList.add('oynat'); }
                gonderiBegen(medya.dataset.ciftBegen, true);
            } else {
                tiklamaZamani = setTimeout(() => { tiklamaZamani = null; gonderiAc(medya.dataset.gonderiAc); }, 260);
            }
            return;
        }
        if (acici && !e.target.closest('a')) { gonderiAc(acici.dataset.gonderiAc); }
    });

    document.addEventListener('click', (e) => {
        const k = e.target.closest('[data-kopyala]');
        if (k) { e.preventDefault(); kopyala(k.dataset.kopyala); }
    });

    document.addEventListener('click', async (e) => {
        const s = e.target.closest('[data-gonderi-sil]');
        if (!s) return;
        if (!confirm('Bu gönderi kalıcı olarak silinsin mi?')) return;
        const id = s.dataset.gonderiSil;
        const v = await api(`/api/gonderi/${id}/sil`, { method: 'POST' });
        if (v.status !== 'success') return toast(v.mesaj || 'Silinemedi.', 'danger');
        $$(`#gonderi-${id}, [data-izgara-gonderi="${id}"]`).forEach((el) => { el.style.transition = 'all .4s'; el.style.opacity = 0; el.style.transform = 'scale(.95)'; setTimeout(() => el.remove(), 400); });
        bootstrap.Modal.getInstance($('#gonderiDetayModal'))?.hide();
        toast('Gönderi silindi.', 'success');
    });

    document.addEventListener('click', async (e) => {
        const d = e.target.closest('[data-gonderi-duzenle]');
        if (!d) return;
        const id = d.dataset.gonderiDuzenle;
        const metinEl = $(`#gonderi-${id} [data-gonderi-metin]`) || $('#gdMetin');
        const mevcut = metinEl ? metinEl.textContent.trim() : '';
        const yeni = prompt('Gönderini düzenle:', mevcut);
        if (yeni === null || yeni.trim() === mevcut) return;
        const v = await api(`/api/gonderi/${id}/duzenle`, { method: 'POST', json: { icerik: yeni } });
        if (v.status !== 'success') return toast(v.mesaj || 'Güncellenemedi.', 'danger');
        $$(`#gonderi-${id} [data-gonderi-metin]`).forEach((el) => (el.textContent = v.icerik));
        if ($('#gdMetin')) $('#gdMetin').textContent = v.icerik;
        toast('Gönderi güncellendi.', 'success');
    });

    /* ---------- Gönderi detay modalı ---------- */
    let gdModal;
    async function gonderiAc(id) {
        const kutu = $('#gonderiDetayIcerik');
        gdModal = gdModal || new bootstrap.Modal($('#gonderiDetayModal'));
        kutu.innerHTML = '<div class="p-5 text-center"><div class="spinner-border text-primary"></div></div>';
        gdModal.show();
        const v = await api(`/api/gonderi/${id}`);
        if (v.status !== 'success') { kutu.innerHTML = `<div class="p-5 text-center text-muted">${esc(v.mesaj || 'Gönderi yüklenemedi.')}</div>`; return; }
        gonderiCiz(v.gonderi);
    }
    window.Aronsan.gonderiAc = gonderiAc;

    function yorumlarHTML(g) {
        if (!g.yorumlar.length) return '<div class="text-center text-muted small py-4"><i class="bi bi-chat-square-dots fs-3 d-block mb-2"></i>Henüz yorum yok. İlk yorumu sen yap!</div>';
        return g.yorumlar.map((y) => `<div class="yorum-satir">
            <a href="/profil/${y.yazar.id}">${avatarHTML(y.yazar.profil_fotografi, 34)}</a>
            <div class="icerik">${isimHTML(y.yazar)} <span class="metin">${esc(y.yorum)}</span>
                <div class="alt"><span>${esc(y.tarih)}</span>${y.silinebilir || (KULLANICI && KULLANICI.personel) ? `<button class="btn-link-plain" data-yorum-sil="${y.id}">Sil</button>` : ''}</div>
            </div></div>`).join('');
    }

    function gonderiCiz(g) {
        const kutu = $('#gonderiDetayIcerik');
        const medya = g.gorsel_url
            ? `<img src="${esc(g.gorsel_url)}" alt="" data-isik><i class="bi bi-heart-fill cift-tik-kalp"></i>`
            : `<div class="metin-gonderi">${esc(g.icerik)}</div>`;
        kutu.innerHTML = `<div class="row g-0">
            <div class="col-lg-7 medya position-relative" id="gdMedya">${medya}</div>
            <div class="col-lg-5 yan">
                <div class="d-flex align-items-center gap-3 p-3 border-bottom" style="border-color:var(--border)!important">
                    <a href="/profil/${g.yazar.id}">${avatarHTML(g.yazar.profil_fotografi, 40, false, g.yazar.mavi_tik)}</a>
                    <div class="flex-grow-1" style="min-width:0">${isimHTML(g.yazar)}<div class="small text-muted">${esc(g.tarih_uzun)}</div></div>
                    ${g.benim || g.yonetici ? `<div class="dropdown"><button class="btn-link-plain fs-5 px-2" data-bs-toggle="dropdown"><i class="bi bi-three-dots"></i></button><ul class="dropdown-menu dropdown-menu-end">
                        ${g.benim ? `<li><button class="dropdown-item" data-gonderi-duzenle="${g.id}"><i class="bi bi-pencil"></i>Düzenle</button></li>` : ''}
                        <li><button class="dropdown-item tehlike" data-gonderi-sil="${g.id}"><i class="bi bi-trash3"></i>Sil</button></li></ul></div>` : ''}
                    <button type="button" class="btn-close ms-1" data-bs-dismiss="modal" aria-label="Kapat"></button>
                </div>
                <div class="yorumlar" id="gdYorumlar">
                    ${g.icerik && g.gorsel_url ? `<div class="yorum-satir pb-3 mb-2 border-bottom" style="border-color:var(--border)!important"><a href="/profil/${g.yazar.id}">${avatarHTML(g.yazar.profil_fotografi, 34)}</a><div class="icerik">${isimHTML(g.yazar)} <span class="metin" id="gdMetin">${esc(g.icerik)}</span></div></div>` : ''}
                    <div id="gdYorumListe">${yorumlarHTML(g)}</div>
                </div>
                <div class="p-3 border-top" style="border-color:var(--border)!important">
                    <div class="d-flex align-items-center gap-3 mb-2">
                        <button class="begen-btn ${g.begendim ? 'aktif' : ''}" data-gonderi-begen="${g.id}"><i class="bi ${g.begendim ? 'bi-heart-fill' : 'bi-heart'}"></i></button>
                        <button class="aksiyon-btn" onclick="document.getElementById('gdYorumInput')?.focus()"><i class="bi bi-chat"></i></button>
                        <button class="aksiyon-btn" data-kopyala="${location.origin}/profil/${g.yazar.id}?gonderi=${g.id}"><i class="bi bi-send"></i></button>
                    </div>
                    <div class="fw-semibold small"><span data-begeni-sayi="${g.id}">${g.begeni}</span> beğenme</div>
                    ${KULLANICI ? `<form class="d-flex align-items-center gap-2 mt-3" id="gdYorumForm">
                        <input class="form-control" id="gdYorumInput" placeholder="Yorum ekle..." maxlength="1000" autocomplete="off">
                        <button class="btn btn-primary btn-sm px-3" type="submit"><i class="bi bi-send"></i></button></form>`
                : '<div class="small text-muted mt-3">Yorum yapmak için <a href="/giris">giriş yap</a>.</div>'}
                </div>
            </div></div>`;
        const medyaEl = $('#gdMedya');
        if (g.gorsel_url) {
            medyaEl.addEventListener('dblclick', () => {
                const k = $('.cift-tik-kalp', medyaEl); k.classList.remove('oynat'); void k.offsetWidth; k.classList.add('oynat');
                gonderiBegen(g.id, true);
            });
        }
        $('#gdYorumForm')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const inp = $('#gdYorumInput'), yorum = inp.value.trim();
            if (!yorum) return;
            inp.disabled = true;
            const v = await api(`/api/gonderi/${g.id}/yorum`, { method: 'POST', json: { yorum } });
            inp.disabled = false;
            if (v.status !== 'success') return toast(v.mesaj || 'Yorum gönderilemedi.', 'danger');
            inp.value = '';
            yorumGuncelle(v.gonderi);
            const liste = $('#gdYorumlar'); liste.scrollTop = liste.scrollHeight;
        });
    }
    function yorumGuncelle(g) {
        $('#gdYorumListe').innerHTML = yorumlarHTML(g);
        $$(`#gonderi-${g.id} .yorum-link`).forEach((el) => (el.textContent = g.yorum_sayisi ? `${g.yorum_sayisi} yorumun tümünü gör` : 'Yorum ekle...'));
    }
    document.addEventListener('click', async (e) => {
        const s = e.target.closest('[data-yorum-sil]');
        if (!s || !confirm('Yorum silinsin mi?')) return;
        const v = await api(`/api/gonderi_yorum/${s.dataset.yorumSil}/sil`, { method: 'POST' });
        if (v.status === 'success') yorumGuncelle(v.gonderi); else toast(v.mesaj || 'Silinemedi.', 'danger');
    });

    /* URL'den gönderi aç: ?gonderi=ID */
    const urlGonderi = new URLSearchParams(location.search).get('gonderi');
    if (urlGonderi) setTimeout(() => gonderiAc(urlGonderi), 350);

    /* ---------- Yeni gönderi formu ---------- */
    const gForm = $('#gonderiForm');
    if (gForm) {
        const dosya = $('input[type=file]', gForm), onizleme = $('#gonderiOnizleme'), alan = $('#gonderiYukleme');
        const goster = (f) => {
            if (!f || !f.type.startsWith('image/')) return;
            const r = new FileReader();
            r.onload = (ev) => { $('img', onizleme).src = ev.target.result; onizleme.style.display = 'block'; alan.style.display = 'none'; };
            r.readAsDataURL(f);
        };
        dosya.addEventListener('change', () => goster(dosya.files[0]));
        $('.kaldir', onizleme).addEventListener('click', () => { dosya.value = ''; onizleme.style.display = 'none'; alan.style.display = 'block'; });
        ['dragenter', 'dragover'].forEach((ev) => alan.addEventListener(ev, (e) => { e.preventDefault(); alan.classList.add('surukle'); }));
        ['dragleave', 'drop'].forEach((ev) => alan.addEventListener(ev, (e) => { e.preventDefault(); alan.classList.remove('surukle'); }));
        alan.addEventListener('drop', (e) => { if (e.dataTransfer.files[0]) { dosya.files = e.dataTransfer.files; goster(e.dataTransfer.files[0]); } });
        gForm.addEventListener('submit', (e) => {
            if (!$('textarea', gForm).value.trim() && !dosya.files.length) { e.preventDefault(); toast('Bir şeyler yaz ya da fotoğraf ekle.', 'warning'); return; }
            butonYukleniyor($('[type=submit]', gForm), true);
        });
        $('#gonderiModal').addEventListener('shown.bs.modal', () => $('textarea', gForm).focus());
    }

    /* ---------- Karakter sayaçları ---------- */
    $$('[data-sayac]').forEach((el) => {
        const hedef = document.getElementById(el.dataset.sayac);
        const max = parseInt(el.getAttribute('maxlength'), 10) || 0;
        const guncelle = () => {
            if (!hedef) return;
            hedef.textContent = `${el.value.length} / ${max}`;
            hedef.classList.toggle('uyari', max && el.value.length > max * 0.9);
        };
        el.addEventListener('input', guncelle); guncelle();
    });

    /* ---------- Şifre göster / güç ---------- */
    document.addEventListener('click', (e) => {
        const b = e.target.closest('.sifre-goster');
        if (!b) return;
        const inp = b.parentElement.querySelector('input');
        const gizli = inp.type === 'password';
        inp.type = gizli ? 'text' : 'password';
        b.innerHTML = `<i class="bi ${gizli ? 'bi-eye-slash' : 'bi-eye'}"></i>`;
    });
    $$('[data-sifre-guc]').forEach((inp) => {
        const bar = document.getElementById(inp.dataset.sifreGuc), etiket = document.getElementById(inp.dataset.sifreGuc + 'Metin');
        inp.addEventListener('input', () => {
            const s = inp.value;
            let p = 0;
            if (s.length >= 6) p++; if (s.length >= 10) p++;
            if (/[A-Z]/.test(s) && /[a-z]/.test(s)) p++; if (/\d/.test(s)) p++; if (/[^A-Za-z0-9]/.test(s)) p++;
            const seviyeler = [['', '0%', 'transparent'], ['Çok zayıf', '20%', '#ef4444'], ['Zayıf', '40%', '#f97316'], ['Orta', '60%', '#f59e0b'], ['Güçlü', '80%', '#22c55e'], ['Çok güçlü', '100%', '#10b981']];
            const [m, w, c] = seviyeler[s ? Math.max(1, p) : 0];
            bar.firstElementChild.style.width = w; bar.firstElementChild.style.background = c;
            if (etiket) { etiket.textContent = m; etiket.style.color = c; }
        });
    });

    /* ---------- Onay gerektiren formlar & yükleniyor ---------- */
    document.addEventListener('submit', (e) => {
        const f = e.target;
        if (f.dataset.onay && !confirm(f.dataset.onay)) { e.preventDefault(); return; }
        if (f.hasAttribute('data-yukleniyor')) butonYukleniyor(f.querySelector('[type=submit]'), true);
    });

    /* ---------- Işık kutusu ---------- */
    const isik = $('#isikKutusu');
    document.addEventListener('click', (e) => {
        const img = e.target.closest('[data-isik], .balon img');
        if (!img || !isik) return;
        $('img', isik).src = img.src;
        isik.classList.add('acik');
    });
    isik?.addEventListener('click', () => isik.classList.remove('acik'));
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') isik?.classList.remove('acik'); });

    /* ---------- Bülten ---------- */
    $('#bultenForm')?.addEventListener('submit', (e) => {
        e.preventDefault();
        e.target.reset();
        toast('Bültenimize kaydoldun. Teşekkürler!', 'success');
    });

    /* ---------- Kırık görseller ---------- */
    document.addEventListener('error', (e) => {
        const img = e.target;
        if (img.tagName === 'IMG' && img.closest('.makale-hero')) { img.closest('.makale-hero').parentElement.style.display = 'none'; return; }
        if (img.tagName === 'IMG' && img.closest('.gorsel-kutu') && !img.dataset.hata) {
            img.dataset.hata = '1';
            img.replaceWith(Object.assign(document.createElement('div'), { className: 'gorsel-yok w-100 h-100', innerHTML: '<i class="bi bi-image"></i>' }));
        }
    }, true);
})();
