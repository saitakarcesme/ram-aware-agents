# MacBook Ajan Performans Profilleri

Codex ve Claude Code kullanırken MacBook'un kullanılabilir kalmasını hedefleyen, performans-öncelikli talimat dosyaları.

[English README](README.md)

## Kullanım

Ana [`README.md`](README.md) tablosundan unified memory miktarınızı seçin. Codex için ilgili `AGENTS.md`, Claude Code için ilgili `CLAUDE.md` dosyasını projenizin köküne kopyalayın. Tam RAM miktarınız listede yoksa bir alt profili kullanın.

Örnek:

```sh
cp profiles/16gb/AGENTS.md /proje/yolu/AGENTS.md
cp profiles/16gb/CLAUDE.md /proje/yolu/CLAUDE.md
```

Profiller; aynı anda açılan ajan, alt ajan, terminal komutu, tarayıcı sekmesi, test, build, watcher ve geliştirme sunucusu sayısını sınırlar. Geniş disk taramaları yerine hedefli arama, tüm testler yerine önce ilgili testler ve büyük dosyalarda parça parça okuma ister.

Compiler, test runner, paket yöneticisi, browser automation ve veri işleme araçlarının kendi iç worker sayıları da RAM seviyesine göre sınırlandırılır. Repository açıkça karma bir kurulum tanımlamıyorsa tek paket yöneticisi ve tek lockfile düzeni korunur. Gerekli proje bağımlılıklarının kurulmasına izin verilir; eksik bağımlılık nedeniyle zorunlu test atlamak başarı sayılmaz. Codex ve Claude dosyaları içerik farkı oluşmaması için [`scripts/generate_profiles.py`](scripts/generate_profiles.py) üzerinden üretilir.

## Görev kapsamlı skill'ler

[`skills/`](skills/README.md) klasöründe iki taşınabilir skill bulunur:

- Codex: `codex-ram-profile`
- Claude Code: `claude-ram-profile`

`profiles/` altındaki dosyalar projede kalıcı davranış sağlar. Skill ise çağrıldığı görev boyunca seçilen RAM bütçesini bütün repository işlemlerine uygular; `AGENTS.md` veya `CLAUDE.md` dosyasını değiştirmez. RAM otomatik algılanabilir veya çağırırken `16` gibi açık bir değer verilebilir.

Codex'te `$codex-ram-profile 16`, Claude Code'da `/claude-ram-profile 16` şeklinde çağrılabilir. Kurulum yolları ve kopyalama bilgileri [`skills/README.md`](skills/README.md) dosyasındadır.

Bu dosyalar davranış talimatıdır; macOS seviyesinde kesin RAM limiti uygulamaz. Activity Monitor, container limitleri, build worker ayarları ve etkin plugin/MCP sayısı da kaynak tüketimini etkiler.

## Temel hedef

Zamandan tasarruf ikinci plandadır. Bilgisayarın arayüzü, tarayıcı, editör ve diğer uygulamalar akıcı kalmalıdır. Bellek baskısı veya swap yükselirse ajan ek işleri durdurur, paralelliği kapatır ve daha küçük adımlarla devam eder.

## Benchmark

Güncel yayımlanmış v2 kanıt paketi [`benchmarks/v2/evidence/8gb-m1-2026-09-02/`](benchmarks/v2/evidence/8gb-m1-2026-09-02/README.md), tekrar üretilebilir protokol ve runner ise [`benchmarks/v2/`](benchmarks/v2/README.md) altındadır. Her koşul yeni proje ve yeni ajan oturumu kullanır; aynı beş prompt, dönüşümlü koşul sırası, saniyelik ölçüm ve bağımsız doğruluk kapılarıyla çalışır.

Doğruluk kapısını geçen iki browser-ağır React/Playwright çiftinde 8 GB profili, medyan P95 Codex işlem-ağacı RSS değerini %57,0 ve medyan tepe RSS değerini %58,9 azalttı. Browser process tepe sayısı 22–24'ten 7'ye düştü; minimum boş sistem belleği %32–49 aralığından %55–60 aralığına çıktı. Medyan aktif süre farkı, koşular arası yüksek değişkenlikle, +%5,0 oldu.

Bu güçlü bir sinyaldir; evrensel veya tamamlanmış sonuç değildir. Protokol en az üç geçerli çift ister. Bu kanıt anında Claude Code'un yerel OAuth oturumu yeniden kimlik doğrulama gerektirdiği için Claude ölçülemedi. 16–128 GB katmanları fiziksel donanımda henüz ölçülmedi. İlk dört-prompt pilotu tarihsel karşılaştırma amacıyla [`benchmarks/codex-8gb-2026-09-01/`](benchmarks/codex-8gb-2026-09-01/README.md) altında tutulur.

## Kaynaklar

- [OpenAI: AGENTS.md ile özel talimatlar](https://developers.openai.com/codex/guides/agents-md)
- [OpenAI: Codex skill oluşturma ve kurulum yolları](https://developers.openai.com/codex/skills)
- [Anthropic: CLAUDE.md kapsamı ve yükleme düzeni](https://code.claude.com/docs/en/memory)
- [Anthropic: Claude Code skill'leri](https://code.claude.com/docs/en/slash-commands)
