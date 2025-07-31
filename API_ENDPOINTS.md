# 🌐 API Endpoints Reference

## HeyGen Interactive Avatar API

### Base URL
```
https://api.heygen.com/v1
```

### Authentication
```http
Headers:
x-api-key: YOUR_HEYGEN_API_KEY
Content-Type: application/json
Accept: application/json
```

## 🔑 Core Endpoints

### 1. Create Session
**Создание новой сессии с аватаром**

```http
POST /streaming/create_session
```

**Request Body:**
```json
{
    "quality": "medium",
    "avatar_id": "default",
    "version": "v2", 
    "video_encoding": "VP8",
    "disable_idle_timeout": false,
    "activity_idle_timeout": 120,
    "voice": {
        "rate": 1.0
    }
}
```

**Response:**
```json
{
    "code": 100,
    "data": {
        "session_id": "uuid-here",
        "websocket_url": "wss://heygen-feapbkvq.livekit.cloud",
        "access_token": "jwt_token_here",
        "realtime_endpoint": "wss://realtime.heygen.com/ws",
        "session_duration_limit": 600
    },
    "message": "success"
}
```

### 2. Start Session
**Запуск созданной сессии**

```http
POST /streaming/start_session
```

**Request Body:**
```json
{
    "session_id": "your-session-id"
}
```

### 3. Send Task
**Отправка задачи аватару**

```http
POST /streaming/send_task
```

**Request Body:**
```json
{
    "session_id": "your-session-id",
    "text": "Привет! Как дела?",
    "task_type": "repeat"
}
```

**Response:**
```json
{
    "code": 100,
    "data": {
        "task_id": "task-uuid",
        "duration_ms": 4829
    },
    "message": "success"
}
```

### 4. Submit ICE
**Отправка ICE кандидатов для WebRTC**

```http
POST /streaming/submit_ice
```

**Request Body:**
```json
{
    "session_id": "your-session-id",
    "candidate": {
        "candidate": "candidate:...",
        "sdpMid": "0",
        "sdpMLineIndex": 0
    }
}
```

### 5. Close Session
**Закрытие сессии**

```http
POST /streaming/close_session
```

**Request Body:**
```json
{
    "session_id": "your-session-id"
}
```

## 🎭 Management Endpoints

### List Avatars
**Получение списка доступных аватаров**

```http
GET /streaming/avatar.list
```

**Response:**
```json
{
    "code": 100,
    "data": [
        {
            "avatar_id": "default",
            "avatar_name": "Anna",
            "preview_image": "https://...",
            "support_live": true
        }
    ]
}
```

### List Sessions
**Получение списка активных сессий**

```http
GET /streaming/list_sessions
```

## 🎥 Live Stream Integration

### LiveKit WebRTC Connection

После создания сессии подключение к LiveKit:

```
WebSocket URL: wss://heygen-feapbkvq.livekit.cloud
Access Token: JWT token from create_session response
Protocol: WebRTC over WebSocket
```

**Connection String:**
```
wss://heygen-feapbkvq.livekit.cloud/rtc?protocol=16&sdk=python&auto_subscribe=1&adaptive_stream=0&version=1.0.12&access_token=YOUR_TOKEN
```

### Stream Tracks

**Video Track:**
- Name: `video`
- Codec: VP8
- Resolution: 1280x720
- Framerate: ~30fps

**Audio Track:**
- Name: `audio` 
- Codec: Opus
- Sample Rate: 48kHz
- Channels: 1 (mono)

## 🔊 Audio APIs

### Deepgram Speech-to-Text

**WebSocket URL:**
```
wss://api.deepgram.com/v1/listen
```

**Parameters:**
```
?model=nova-2
&language=ru
&smart_format=true
&interim_results=true
&utterance_end_ms=1000
&vad_events=true
&encoding=linear16
&channels=1
&sample_rate=16000
```

**Headers:**
```
Authorization: Token YOUR_DEEPGRAM_API_KEY
```

## 🧠 LLM APIs

### Google Gemini

**Base URL:**
```
https://generativelanguage.googleapis.com/v1beta
```

**Generate Content:**
```http
POST /models/gemini-1.5-flash:generateContent?key=YOUR_API_KEY
```

**Request Body:**
```json
{
    "contents": [
        {
            "parts": [
                {
                    "text": "Привет! Как дела?"
                }
            ]
        }
    ]
}
```

### OpenAI (альтернатива)

**Base URL:**
```
https://api.openai.com/v1
```

**Chat Completions:**
```http
POST /chat/completions
```

**Headers:**
```
Authorization: Bearer YOUR_OPENAI_API_KEY
```

## 📊 Status Codes

| Code | Description |
|------|-------------|
| 100  | Success |
| 400  | Bad Request |
| 401  | Unauthorized |
| 403  | Forbidden |
| 404  | Not Found |
| 500  | Internal Server Error |

## 🔧 Error Handling

**Error Response Format:**
```json
{
    "code": 400,
    "message": "Invalid session_id",
    "details": "Session not found or expired"
}
```

## 💡 Usage Examples

### Python Session Management

```python
import aiohttp

async def create_heygen_session():
    url = "https://api.heygen.com/v1/streaming/create_session"
    headers = {
        'x-api-key': 'YOUR_API_KEY',
        'content-type': 'application/json'
    }
    data = {
        "quality": "medium",
        "avatar_id": "default",
        "voice": {"rate": 1.0}
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            return await response.json()
```

### WebSocket Connection

```python
import livekit

async def connect_to_livekit(websocket_url, access_token):
    room = livekit.Room()
    await room.connect(websocket_url, access_token)
    
    @room.on("track_subscribed")
    def on_track_subscribed(track, publication, participant):
        if track.kind == livekit.TrackKind.KIND_VIDEO:
            # Handle video track
            pass
        elif track.kind == livekit.TrackKind.KIND_AUDIO:
            # Handle audio track  
            pass
```

---

**📚 Полная документация**: [HeyGen API Docs](https://docs.heygen.com/reference/streaming-api)
