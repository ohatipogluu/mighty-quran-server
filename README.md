# 🕌 Akıllı İslami Portal - Mobil Uygulama

**Premium Lüks İslami Yaşam Asistanı**

Modern, şık ve kullanıcı dostu bir İslami yaşam platformu. Diyanet uyumlu namaz vakitleri, canlı piyasa verili zekat hesaplayıcı, yapay zeka destekli Kuran rehberi ve premium kıble bulucu içerir.

---

## 📋 İçindekiler

- [Özellikler](#-özellikler)
- [Teknik Gereksinimler](#-teknik-gereksinimler)
- [Kurulum](#-kurulum)
- [Yapılandırma](#️-yapılandırma)
- [Proje Yapısı](#-proje-yapısı)
- [Derleme ve Yayınlama](#-derleme-ve-yayınlama)
- [Özelleştirme](#-özelleştirme)
- [Sorun Giderme](#-sorun-giderme)
- [Lisans](#-lisans)

---

## ✨ Özellikler

### 🕐 Namaz Vakitleri
- **Diyanet Uyumlu** hesaplama metodolojisi
- **Canlı Konum** bazlı otomatik şehir tespiti
- **Premium Tasarım** - Modern kadran görünümü
- Dünya genelinde doğru hesaplama desteği
- Sonraki namaza geri sayım
- Bildirim desteği (yakında)

### 💰 Zekat Hesaplayıcı
- **Canlı Altın Fiyatları** ile gerçek zamanlı Nisab hesabı
- **Nisab Koruması** - Düşük varlıklar için otomatik uyarı
- Altın, gümüş, nakit para ve borç girişi
- İslami fıkha uygun %2.5 zekat oranı
- Detaylı hesaplama raporu

### 📖 Kuran Okuyucu
- Tam 604 sayfa Kuran-ı Kerim metni
- **Dinamik Mealler** - Türkçe (Diyanet) ve İngilizce (Sahih International)
- Hızlı sayfa atlama ve navigasyon
- Sure ve cüz bazlı erişim
- Temiz, göz yormayan tasarım

### 🤖 Yapay Zeka Kuran Rehberi
- **Sadece Kuran Ayetleri** ile cevap veren akıllı asistan
- Konu bazlı ayet arama
- **Gizli Mod** - Mesajlar cihazda saklanmaz
- Türkçe, İngilizce ve Arapça dil desteği
- Fetva veya hadis vermez, sadece ayetleri sunar

### 🧭 Premium Kıble Bulucu
- **3D Altın Pusula** tasarımı
- **Pürüzsüz Animasyonlar** - Low-pass filter ile akıcı hareket
- İslami geometrik desen arka planı
- Hedef kilitlendiğinde haptic feedback
- Mekke'ye mesafe gösterimi

### 📿 İbadet Rehberi
- Namaz kılınışı görselleri
- Abdest alma adımları
- Temel dualar ve zikirler
- Adım adım görsel anlatım

---

## 🔧 Teknik Gereksinimler

### Geliştirme Ortamı
| Araç | Minimum Versiyon |
|------|------------------|
| Node.js | 18.0+ |
| npm / yarn | 8.0+ / 1.22+ |
| Expo CLI | 50.0+ |
| Python | 3.10+ |

### Desteklenen Platformlar
| Platform | Minimum Versiyon |
|----------|------------------|
| iOS | 13.0+ |
| Android | API 21 (Android 5.0)+ |
| Web | Modern tarayıcılar |

---

## 🚀 Kurulum

### 1. Depoyu Klonlayın
```bash
git clone <repo-url>
cd islamic-portal
```

### 2. Frontend Bağımlılıklarını Yükleyin
```bash
cd frontend
npm install
# veya
yarn install
```

### 3. Backend Bağımlılıklarını Yükleyin
```bash
cd ../backend
pip install -r requirements.txt
```

### 4. Ortam Değişkenlerini Ayarlayın

**Frontend (`frontend/.env`):**
```env
EXPO_PUBLIC_BACKEND_URL=http://localhost:8001
```

**Backend (`backend/.env`):**
```env
EMERGENT_LLM_KEY=your_llm_api_key_here
MONGO_URL=mongodb://localhost:27017/islamic_portal
```

### 5. Uygulamayı Başlatın

**Backend:**
```bash
cd backend
uvicorn server:app --reload --port 8001
```

**Frontend (ayrı terminalde):**
```bash
cd frontend
npx expo start
```

---

## ⚙️ Yapılandırma

### Merkezi Anahtar Dosyası

Tüm API anahtarları ve uygulama ayarları tek bir dosyada yönetilir:

📁 `frontend/src/config/AppKeys.ts`

```typescript
export const AppKeys = {
  // Yapay Zeka için (zorunlu)
  GEMINI_API_KEY: "your_gemini_api_key",
  
  // Reklamlar için (opsiyonel)
  AdMob: {
    APP_ID_ANDROID: "ca-app-pub-xxx~yyy",
    APP_ID_IOS: "ca-app-pub-xxx~zzz",
    BANNER_ID: "ca-app-pub-xxx/aaa",
  },
  
  // Zekat için canlı altın fiyatı (opsiyonel)
  GOLD_API_KEY: "",
};
```

### API Anahtarı Alma Rehberi

| Servis | Amaç | Nereden Alınır |
|--------|------|----------------|
| Google Gemini | AI Asistan | [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| AdMob | Reklam Geliri | [apps.admob.com](https://apps.admob.com) |
| Gold API | Canlı Altın | [goldapi.io](https://www.goldapi.io) |

---

## 📁 Proje Yapısı

```
/
├── backend/
│   ├── server.py           # FastAPI ana sunucu
│   ├── requirements.txt    # Python bağımlılıkları
│   └── .env               # Backend ortam değişkenleri
│
└── frontend/
    ├── app/
    │   ├── (tabs)/         # Ana tab navigasyonu
    │   │   ├── index.tsx   # Ana sayfa (Namaz vakitleri)
    │   │   ├── quran.tsx   # Kuran okuyucu
    │   │   └── ...
    │   ├── assistant.tsx   # AI Kuran Rehberi
    │   ├── zakat.tsx       # Zekat Hesaplayıcı
    │   └── qibla.tsx       # Kıble Bulucu
    │
    ├── src/
    │   ├── components/     # Yeniden kullanılabilir bileşenler
    │   ├── config/         # Yapılandırma dosyaları
    │   │   └── AppKeys.ts  # ⭐ MERKEZI ANAHTAR DOSYASI
    │   ├── services/       # API ve servis katmanı
    │   ├── context/        # Uygulama state yönetimi
    │   └── constants/      # Sabitler ve tema
    │
    ├── assets/
    │   ├── images/         # Uygulama ikonları
    │   └── quran_pages/    # Kuran sayfa görselleri
    │
    ├── app.json           # Expo yapılandırması
    └── .env               # Frontend ortam değişkenleri
```

---

## 📦 Derleme ve Yayınlama

### Geliştirme Testi
```bash
# iOS Simulator
npx expo run:ios

# Android Emulator
npx expo run:android

# Web tarayıcı
npx expo start --web
```

### Production Build

#### EAS Build (Önerilen)
```bash
# EAS CLI kurulumu
npm install -g eas-cli
eas login

# Tüm platformlar için build
eas build --platform all

# Sadece Android
eas build --platform android

# Sadece iOS
eas build --platform ios
```

#### Klasik Expo Build
```bash
# Android APK
npx expo build:android -t apk

# Android App Bundle (Play Store için)
npx expo build:android -t app-bundle

# iOS Archive (App Store için)
npx expo build:ios -t archive
```

### Store'a Gönderme
```bash
# Play Store'a gönder
eas submit --platform android

# App Store'a gönder
eas submit --platform ios
```

---

## 🎨 Özelleştirme

### Tema Renkleri

`src/config/AppKeys.ts` dosyasında renkleri değiştirin:

```typescript
colors: {
  primary: "#D4AF37",      // Ana renk (Altın)
  secondary: "#0A0F1C",    // İkincil renk
  accent: "#00C853",       // Vurgu rengi
  background: "#0C121E",   // Arka plan
}
```

### Uygulama Adı ve İkonu

`app.json` dosyasını düzenleyin:

```json
{
  "expo": {
    "name": "Uygulama Adınız",
    "icon": "./assets/images/icon.png",
    "splash": {
      "image": "./assets/images/splash.png"
    }
  }
}
```

### Dil Desteği

Mevcut diller: Türkçe (tr), İngilizce (en), Arapça (ar)

Yeni dil eklemek için ilgili ekran dosyasındaki `UI_STRINGS` objesine çeviri ekleyin.

---

## 🔍 Sorun Giderme

### Sık Karşılaşılan Sorunlar

#### "Metro bundler başlamıyor"
```bash
# Cache temizleme
npx expo start --clear
```

#### "Konum izni alınamıyor"
- iOS: `Info.plist` dosyasında `NSLocationWhenInUseUsageDescription` kontrol edin
- Android: `AndroidManifest.xml` dosyasında `ACCESS_FINE_LOCATION` izni kontrol edin

#### "AI Asistan cevap vermiyor"
1. `AppKeys.ts` dosyasında `GEMINI_API_KEY` doğru mu kontrol edin
2. Backend sunucusunun çalıştığından emin olun
3. İnternet bağlantısını kontrol edin

#### "Zekat hesaplayıcı fiyat çekemiyor"
- Varsayılan değerler kullanılacaktır
- Canlı fiyat için `GOLD_API_KEY` ekleyin

### Log Görüntüleme
```bash
# Frontend logları
npx expo start --dev-client

# Backend logları
tail -f backend/logs/app.log
```

---

## 📱 Store Gereksinimleri

### Google Play Store
- [x] 512x512 uygulama ikonu
- [x] Feature graphic (1024x500)
- [x] En az 4 ekran görüntüsü
- [x] Gizlilik politikası URL
- [x] İçerik derecelendirmesi

### Apple App Store
- [x] 1024x1024 uygulama ikonu
- [x] 6.5" ve 5.5" ekran görüntüleri
- [x] App Store açıklaması
- [x] Gizlilik politikası URL
- [x] Yaş sınırlandırması

---

## 📄 Lisans

Bu yazılım özel lisans altında sunulmaktadır. Ticari kullanım, dağıtım ve değişiklik hakları için lisans sahibiyle iletişime geçiniz.

**Telif Hakkı © 2024-2026**

---

## 📞 Destek

Teknik destek ve sorularınız için:
- 📧 E-posta: destek@seninwebsiten.com
- 🌐 Web: https://seninwebsiten.com/destek
- 📚 Dokümantasyon: https://docs.seninwebsiten.com

---

**Versiyon:** 1.0.0  
**Son Güncelleme:** Şubat 2026

---

*Bu uygulama, Müslümanların dijital çağda dini pratiklerini kolaylaştırmak amacıyla özenle geliştirilmiştir.*
