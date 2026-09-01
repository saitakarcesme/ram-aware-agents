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

## Görev kapsamlı skill'ler

[`skills/`](skills/README.md) klasöründe iki taşınabilir skill bulunur:

- Codex: `codex-ram-profile`
- Claude Code: `claude-ram-profile`

`profiles/` altındaki dosyalar projede kalıcı davranış sağlar. Skill ise çağrıldığı görev boyunca seçilen RAM bütçesini bütün repository işlemlerine uygular; `AGENTS.md` veya `CLAUDE.md` dosyasını değiştirmez. RAM otomatik algılanabilir veya çağırırken `16` gibi açık bir değer verilebilir.

Codex'te `$codex-ram-profile 16`, Claude Code'da `/claude-ram-profile 16` şeklinde çağrılabilir. Kurulum yolları ve kopyalama bilgileri [`skills/README.md`](skills/README.md) dosyasındadır.

Bu dosyalar davranış talimatıdır; macOS seviyesinde kesin RAM limiti uygulamaz. Activity Monitor, container limitleri, build worker ayarları ve etkin plugin/MCP sayısı da kaynak tüketimini etkiler.

## Temel hedef

Zamandan tasarruf ikinci plandadır. Bilgisayarın arayüzü, tarayıcı, editör ve diğer uygulamalar akıcı kalmalıdır. Bellek baskısı veya swap yükselirse ajan ek işleri durdurur, paralelliği kapatır ve daha küçük adımlarla devam eder.
