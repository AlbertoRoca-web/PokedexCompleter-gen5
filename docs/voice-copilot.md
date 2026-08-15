# Voice Copilot

GPT Realtime can be used as an optional voice layer while the emulator is running.

It should not be the direct controller.

## Modes

```text
off
```

No voice.

```text
talk-to-me
```

The assistant narrates important progress and answers Alberto.

```text
rubberduck
```

The assistant commentates observations and sends claims to validation before any game action.

Example:

```text
"We finally found the 1 percent encounter for this route. Sending observation to validator."
```

## Safety architecture

```text
Browser microphone/audio
  -> Realtime voice session
  -> commentary events
  -> validator
  -> deterministic planner/executor
  -> BizHawk bridge
```

Voice can talk. Voice can suggest. Voice does not get the steering wheel.

## Current implementation

Endpoint:

```text
GET /api/voice/config?mode=rubberduck
```

CLI/local website can check whether Realtime is ready. It does not expose `OPENAI_API_KEY`.

Actual browser Realtime session minting is pending. The backend must mint ephemeral Realtime credentials; the browser must never receive the long-lived OpenAI API key.

## Environment

```env
OPENAI_API_KEY=
OPENAI_REALTIME_MODEL=gpt-realtime
```

`OPENAI_REALTIME_MODEL` is optional.
