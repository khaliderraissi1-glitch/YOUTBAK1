# YouTube Downloader Backend

Backend مستقل مبني بـ **FastAPI + yt-dlp** لاستخراج بيانات فيديو YouTube وتوفير روابط تنزيل مؤقتة للفيديو والصوت.

> استخدمه فقط للمحتوى الذي تملك حق تنزيله أو لديك إذن بتنزيله، وراجع شروط YouTube والقوانين المحلية.

## الميزات

- استخراج العنوان، الصورة المصغرة، اسم القناة، رابط القناة، المدة، عدد المشاهدات وتاريخ الرفع.
- رابط فيديو HD بصيغة MP4، مع اختيار أفضل صيغة مدمجة متاحة.
- رابط فيديو SD بصيغة MP4 حتى 480p عند توفرها.
- رابط صوت MP3 بجودة 192kbps، يتم تحويله عبر ffmpeg عند الطلب.
- روابط Proxy مؤقتة، حتى لا يضطر المتصفح إلى الاتصال مباشرة بروابط CDN قصيرة العمر.
- CORS وRate limiting وHealth check وDocker/Railway جاهزة.

ملاحظة: YouTube لا يستخدم مفهوم «بدون علامة مائية» مثل TikTok؛ لذلك يسمى الخيار `Video HD` وهو أفضل فيديو MP4 مدمج متاح.

## التشغيل المحلي

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# يلزم تثبيت ffmpeg لتحويل MP3
uvicorn app.main:app --reload --port 8000
```

افتح `http://localhost:8000/docs`.

## API

### المسارات المتاحة

| المسار | الوظيفة |
|---|---|
| `GET /health` | فحص صحة الخدمة؛ والمسار القديم `GET /api/health` ما زال مدعومًا. |
| `GET /info?url=...` | استخراج بيانات الفيديو؛ والمساران `GET /api/info?url=...` و`POST /api/info` ما زالا مدعومين. |
| `GET /download/mp4?url=...` | تنزيل أفضل صيغة MP4 مدمجة متاحة مباشرة. |
| `GET /download/mp3?url=...` | استخراج الصوت وتحويله إلى MP3 مباشرة. |
| `GET /api/download/{token}/{kind}` | تنزيل مؤقت باستخدام الرمز الناتج من مسار المعلومات، كما في النسخة السابقة. |

تتطلب مسارات التنزيل المباشرة معامل `url` برابط فيديو YouTube. الاستجابات الناجحة تحتوي ملفًا قابلًا للتنزيل، لا استجابة JSON.

### POST `/api/info`

```bash
curl -X POST http://localhost:8000/api/info \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://www.youtube.com/watch?v=VIDEO_ID"}'
```

ويمكن استخدام `GET /api/info?url=...`.

الاستجابة تحتوي على:

```json
{
  "video_id": "...",
  "title": "...",
  "thumbnail": "https://i.ytimg.com/...",
  "author": "...",
  "duration": "3m 14s",
  "views_formatted": "2.3M",
  "downloads": [
    {"id":"video_hd","label":"Video HD","format":"MP4","quality":"1080p","file_size":"...","download_url":"..."},
    {"id":"video_sd","label":"Video SD","format":"MP4","quality":"480p","file_size":"...","download_url":"..."},
    {"id":"audio_mp3","label":"Audio","format":"MP3","quality":"MP3","file_size":"...","download_url":"..."}
  ]
}
```

روابط التنزيل مؤقتة افتراضيًا لمدة 15 دقيقة ويمكن تغييرها عبر `CACHE_TTL_SECONDS`.

## النشر على GitHub وRailway

```bash
git init
git add .
git commit -m "Create YouTube downloader backend"
git branch -M main
git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
git push -u origin main
```

في Railway: **New Project → Deploy from GitHub Repo**، اختر المستودع. سيكتشف Railway ملف `Dockerfile` تلقائيًا. أضف متغيرات البيئة من `.env.example`، خصوصًا `PUBLIC_BASE_URL` بعد معرفة رابط الخدمة، و`ALLOWED_ORIGINS` لرابط الواجهة الأمامية.

إذا احتجت cookies لحسابك أو لمحتوى مصرح به، ارفع `cookies.txt` كـ Secret File داخل Railway واضبط `COOKIES_FILE=/app/cookies.txt`. لا تضع cookies داخل GitHub.

## ملاحظات إنتاجية

- الذاكرة المؤقتة داخل الذاكرة؛ في حالة تشغيل عدة نسخ يجب إضافة Redis أو توجيه الطلبات إلى نفس النسخة.
- بعض فيديوهات YouTube قد تمنع التحميل أو لا توفر صيغًا مدمجة؛ عندها يعيد API الصيغ المتاحة فقط.
- الصور المصغرة وروابط CDN لا تُنسخ إلى الخادم؛ يتم إرجاعها كما يوفرها YouTube.
