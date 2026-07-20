# API local de gravação

API FastAPI para gravar áudio local em WAV PCM 24-bit, 48 kHz, salvar metadados em JSON e enviar o áudio para a API remota.

## Instalação

### Windows

```bat
install.bat
```

### Linux

```bash
chmod +x install-linux.sh start_api.sh
./install-linux.sh
```

O script tenta instalar dependências nativas com `apt`, `dnf` ou `pacman`. Em outras distribuições, instale manualmente:

```text
Python 3.11+
PortAudio
libsndfile
```

Exemplo em Ubuntu/Debian:

```bash
sudo apt install python3-venv python3-dev portaudio19-dev libsndfile1
```

### macOS

```bash
chmod +x install-macos.sh start_api.sh
./install-macos.sh
```

O script usa Homebrew para instalar:

```bash
brew install portaudio libsndfile
```

No macOS, conceda permissão de microfone ao Terminal, Python ou IDE que iniciar a API.

## Execução

### Windows

```bat
start_api.bat
```

### Linux/macOS

```bash
./start_api.sh
```

A API ficará disponível em:

```text
http://127.0.0.1:9000
```

## Fluxo básico

1. Liste microfones com `GET /api/microphones`.
2. Selecione um microfone com `PUT /api/microphones/selected`.
3. Monitore nível com `WS /api/audio/stream`.
4. Inicie a gravação com `POST /api/recordings/start`.
5. Pare a gravação com `POST /api/recordings/stop`.
6. Consulte a última gravação com `GET /api/recordings/latest/{user_id}`.
7. Reproduza o WAV com `GET /api/recordings/latest/{user_id}/audio`.
8. Envie para a API remota com `POST /api/recordings/latest/{user_id}/upload`.

Nos endpoints de upload, envie o mesmo token recebido/usado pelo front:

```bash
curl -X POST "http://localhost:9000/api/recordings/1784551800469/upload" \
  -H "accept: application/json" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"eeb16762-def1-45fc-aac6-e71c779b5ad3"}'
```

O `user_id` é um UUID e, por isso, precisa estar entre aspas no JSON. No upload
por `id_recordings`, o corpo é opcional; quando enviado, ele é usado para conferir
o proprietário da gravação. O header `Authorization` é obrigatório para o envio à
API remota.

A API local repassa esse header para:

```http
POST https://akcitapi.duckdns.org/api/v1/recordings
Authorization: Bearer SEU_TOKEN
Content-Type: multipart/form-data
```

O arquivo WAV é enviado no campo multipart `audio_file`, conforme o contrato da
API remota.

O token não é salvo no JSON local da gravação.

Os arquivos são salvos em:

```text
recordings/{user_id}/session_{session_id}/recording_{id_recordings}.wav
recordings/{user_id}/session_{session_id}/recording_{id_recordings}.json
```

O áudio é gravado sem filtro, ganho, normalização, compressão ou edição.

## Endpoints principais

```text
GET /health
GET /api/microphones
GET /api/microphones/selected
PUT /api/microphones/selected
WS  /api/audio/stream
POST /api/recordings/start
POST /api/recordings/stop
GET /api/recordings/status
GET /api/recordings/latest/{user_id}
GET /api/recordings/latest/{user_id}/audio
GET /api/recordings/{id_recordings}
GET /api/recordings/{id_recordings}/audio
POST /api/recordings/latest/{user_id}/upload
POST /api/recordings/{id_recordings}/upload
```

## Observações por plataforma

- Windows: normalmente basta executar `install.bat`; confirme que o driver do microfone suporta 48000 Hz.
- Linux: confirme que PulseAudio, PipeWire, ALSA ou JACK está ativo e que o usuário tem permissão para capturar áudio.
- macOS: a permissão de microfone é obrigatória; sem ela o stream/gravação pode falhar mesmo com a instalação correta.
