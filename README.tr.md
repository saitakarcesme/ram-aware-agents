# MacBook Ajan Performans Profilleri

Codex ve Claude Code kullanırken MacBook'un kullanılabilir kalmasını hedefleyen, performans-öncelikli talimat dosyaları.

## Kullanım

Ana [`README.md`](README.md) tablosundan unified memory miktarınızı seçin. Codex için ilgili `AGENTS.md`, Claude Code için ilgili `CLAUDE.md` dosyasını projenizin köküne kopyalayın. Tam RAM miktarınız listede yoksa bir alt profili kullanın.

Örnek:

```sh
cp profiles/16gb/AGENTS.md /proje/yolu/AGENTS.md
cp profiles/16gb/CLAUDE.md /proje/yolu/CLAUDE.md
```

Profiller; aynı anda açılan ajan, alt ajan, terminal komutu, tarayıcı sekmesi, test, build, watcher ve geliştirme sunucusu sayısını sınırlar. Geniş disk taramaları yerine hedefli arama, tüm testler yerine önce ilgili testler ve büyük dosyalarda parça parça okuma ister.

Compiler, test runner, paket yöneticisi, browser automation ve veri işleme araçlarının kendi iç worker sayıları da RAM seviyesine göre sınırlandırılır. Gerekli proje bağımlılıklarının kurulmasına izin verilir; eksik bağımlılık nedeniyle zorunlu test atlamak başarı sayılmaz. Codex ve Claude dosyaları içerik farkı oluşmaması için [`scripts/generate_profiles.py`](scripts/generate_profiles.py) üzerinden üretilir.

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

İlk kontrollü karşılaştırma [`benchmarks/codex-8gb-2026-09-01/`](benchmarks/codex-8gb-2026-09-01/README.md) altında yayımlanmıştır. Aynı dört prompt iki temiz projede çalıştırıldı. Bu tek koşuda 8 GB profili ortalama Codex işlem ağacı RSS kullanımını %30,7, P95 RSS kullanımını %18,0 azalttı; toplam süre %13,3 uzadı. Mutlak tepe RSS ise azalmadı ve %3,2 daha yüksek çıktı. Grafikler, saniyelik ham örnekler, yöntem ve sınırlamalar raporda yer alır.
