# Raithanna (రైతన్న) — Kisan Cold Link farmer advisory app

A native Android app in which **Raithanna**, a friendly Telugu village companion, calls the farmer
(always addressed as **Babai / బాబాయ్**) and tells them today's mandi prices, transport costs, and where and
when they keep the most money. It reads only **lots the admin created** in the web admin portal
(ADR-026); farmers never create or edit lots. Decisions: `DECISIONS.md` ADR-030.

The call is **button-controlled audio**: Raithanna speaks with server-generated voice, and the farmer answers with
large on-screen **1** and **2** buttons. No microphone, no recording, no speech recognition, no real phone calls.

## How it works

```
Admin portal ── creates lot (farmer, phone, village, crop, quantity, fare, mandis + road km, storage)
      │
FastAPI backend
  POST /api/v1/mobile/identify            name + mobile must both match → per-lot token
  GET  /api/v1/mobile/lots/{id}           lot + best-mandi comparison + stored prices   (X-Farmer-Token)
  GET  /api/v1/mobile/lots/{id}/market    today's live price for one mandi, labelled    (X-Farmer-Token)
  POST /api/v1/mobile/lots/{id}/advisory  greeting | report | goodbye, te | en          (X-Farmer-Token)
  GET  /api/v1/mobile/lots/{id}/audio/{k} cached MP3                                    (X-Farmer-Token)
      │   figures: lot_service.compare → storage planner + trained forecasts (deterministic)
      │   words:   advisory_script template → optional Bedrock rewording (numbers verified) → Azure TTS
      ▼
Android app ── Retrofit → repositories → ViewModels (StateFlow) → Compose; Media3 ExoPlayer plays the MP3
```

Every price, distance, transport cost, commission, storage cost, loss and net figure is calculated by the
backend. AI only rewords finished sentences, and any rewording that changes a number is thrown away.

## Requirements

- Android Studio Ladybug or newer (or just the command line), JDK 21, Android SDK platform 35.
- The backend running with `MOBILE_LINK_SECRET` set (see below).

## Build and test

```bash
cd android
echo "sdk.dir=$HOME/Android/Sdk" > local.properties   # Android Studio writes this for you
./gradlew test --console=plain     # unit + Compose UI tests (JVM, Robolectric), debug variant
./gradlew assembleDebug            # APK: app/build/outputs/apk/debug/app-debug.apk
```

`JAVA_HOME` must point to JDK 21 if your default Java is older
(e.g. `JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 ./gradlew test`).

## Backend networking

The backend URL is baked into the build (`BuildConfig.BACKEND_BASE_URL`), with no other settings and no keys:

| Where the app runs | Command |
| --- | --- |
| Android emulator (default) | `./gradlew assembleDebug` → `http://10.0.2.2:8000/api/v1/` (the host machine) |
| Phone on the same Wi-Fi | `./gradlew assembleDebug -PkclBackendUrl=http://192.168.1.100:8000/api/v1/` |
| Production | `-PkclBackendUrl=https://your-domain/api/v1/` (release builds refuse plain HTTP) |

For a phone, start the backend on the LAN: `API_HOST=0.0.0.0 API_PORT=8000 bash dev.sh` from the repo root.
Debug builds allow plain HTTP (`src/debug/res/xml/network_security_config.xml`); release builds do not.

## Backend configuration (`backend/.env`)

```env
MOBILE_LINK_SECRET=<random hex>      # required; signs the per-lot farmer tokens. Empty = mobile API off.
AWS_REGION=us-east-1                 # optional Bedrock narration
BEDROCK_MODEL_ID=us.anthropic.claude-haiku-5-5
AZURE_SPEECH_KEY=<key>               # optional; without it the app shows text and no audio
AZURE_SPEECH_REGION=<region>         # e.g. centralindia
AZURE_VOICE_TE=te-IN-MohanNeural     # or te-IN-ShrutiNeural
AZURE_VOICE_EN=en-IN-PrabhatNeural   # or en-IN-NeerjaNeural
```

Generate the secret with `python -c "import secrets; print(secrets.token_hex(32))"`.

### AWS Bedrock

Credentials come from the normal AWS chain on the server (`~/.aws`, environment, or an instance role); the
backend calls `bedrock-runtime` `converse` with boto3. Check access with:

```bash
aws sts get-caller-identity
aws configure get region
aws bedrock list-inference-profiles --query "inferenceProfileSummaries[?contains(inferenceProfileId,'haiku')].inferenceProfileId"
```

Model choice was tested on 2026-11-12 in us-east-1: Amazon Nova Micro and Nova Lite mistranslated crop words
in Telugu, Claude Haiku 5.5 did not. Leave `BEDROCK_MODEL_ID` empty to use the deterministic template only.
Rewordings are cached per template, so an unchanged report never calls Bedrock twice.

### Azure Speech

Create a Speech resource in the Azure portal, copy its key and region into `backend/.env`, and restart the
backend. Telugu neural voices are listed at
https://learn.microsoft.com/azure/ai-services/speech-service/language-support. Audio is generated on the
server, cached under `backend/data/advisory/audio/`, and downloaded by the app; no key ever reaches the APK.

## Farmer flow

1. **Welcome**: Raithanna, the heading "మీ పంటకు మంచి ధర. మీ కష్టానికి మంచి ఫలితం.", Telugu (default) or English.
2. **Identification**: farmer name + mobile number. The backend returns only lots whose name *and* number match.
   With several lots the farmer picks one, then confirms. No match: "బాబాయ్, మీ వివరాలు ఇంకా నమోదు కాలేదు…".
   This is a demo sign-in, not OTP verification.
3. **Home**: "నమస్కారం బాబాయ్!", the lot (crop from the lot, quantity in quintals and kg, village, storage),
   today's market for the best mandi (modal, min, max per quintal and per kg, date, source), Raithanna's
   suggestion with estimated net money, and the big **రైతన్నతో మాట్లాడండి** button.
4. **Raithanna call** (full screen, state machine in `features/call/`):
   greeting audio → buttons 1 and 2 activate → **1**: intro + full report (lot, prices, each mandi's distance,
   sale value, transport, commission, net, sell-now vs 7/14/30-day storage where allowed, recommendation)
   → replay / detailed analysis / home. **2**: goodbye, then back home.
5. **Market, My Lot, Raithanna, Profile** tabs: per-mandi prices (with an on-demand live check), mandi
   comparison, storage comparison, last report, language, daily reminder time, sign out.

## Audio and offline behaviour

- Media3 ExoPlayer plays downloaded MP3s; the screen shows "speaking" and the waveform only while audio is
  actually playing. Audio pauses when the app goes to the background; recomposition and rotation never
  restart it.
- If TTS is unavailable, the call continues with the text on screen and a "try audio again" button.
- The last lot view and last report (text + audio) are saved on the phone. When the server can't be reached,
  saved data is shown with its date and labelled saved; stored prices are never shown as live.

## Daily reminder

Profile → daily reminder, pick a time. WorkManager checks once a day that the backend still serves the lot,
and only then posts "బాబాయ్, ఈరోజు నీ పంట ధరలు తెలుసుకోవాలా?". Tapping it opens the Raithanna call.

## Project layout

```
app/src/main/java/in/kisancoldlink/app/
  core/design        colours, type, theme, components, Raithanna avatar, waveform
  core/networking    error mapping (network / not registered / unauthorized / server)
  core/preferences   DataStore: language, onboarding, lot reference + token, reminder
  core/utils         rupee formatting, quintal↔kg, in-app language switching
  data/{dto,remote,local,repository}   Retrofit API, backend DTOs, file caches, repositories
  domain/{model,repository,usecase}    plain models, interfaces, identification rules
  features/{onboarding,authentication,home,lot,market,mandi,storage,advisory,call,settings}
  audio/             AudioPlayer interface + ExoPlayer implementation
  notifications/     reminder scheduling and worker
  navigation/        routes, bottom navigation, start screen
```

The Kotlin package is `` `in`.kisancoldlink.app `` in source because `in` is a Kotlin keyword.

## Tests

`./gradlew test` runs 47 JVM tests: the call state machine, the call ViewModel (option 1, option 2, goodbye,
duplicate presses, TTS failure, playback error, network failure and retry, backgrounding, replay), formatting
and quintal/kg conversion, identification rules, the repositories against a mock server (token header, not-registered
message, offline cache labelling, audio download and caching), parsing of responses recorded from the real backend
(`src/test/resources/fixtures/`, a sample lot), and Compose UI tests (onboarding, identification, lot selection,
dashboard, call options, report actions, audio-unavailable and network errors) in Telugu and English via Robolectric.

## Known limitations

- Identification is not verification: anyone who knows a farmer's registered name and number can open that lot.
- No on-device or emulator run was done while building this; tests run on the JVM (Robolectric).
- Azure Speech was not exercised (no key configured); the app's no-audio path was.
- Backend reasons ("not enough history") and the assumptions list are English in both languages.
- Road distances are whatever the admin typed (ADR-026); the forecast data ends where the stored history ends.
- Plain HTTP on the development network; put the backend behind HTTPS before real use.
