"""Reproduce published-rate base audio estimates; never calls a model API."""
from decimal import Decimal as D
from pathlib import Path
import json

SESSION_MINUTES = D(300)
USER_SPEECH_MINUTES = D(150)
ASSISTANT_MINUTES = D(150)

def audio_cost(input_minutes, input_tps, output_tps, input_usd_m, output_usd_m):
    input_tokens = input_minutes * D(60) * D(str(input_tps))
    output_tokens = ASSISTANT_MINUTES * D(60) * D(str(output_tps))
    return (input_tokens * D(str(input_usd_m)) + output_tokens * D(str(output_usd_m))) / D(1_000_000)

rows = []
for model, in_tps, out_tps, in_rate, out_rate, source in [
    ('qwen-audio-3.0-realtime-flash', 12.5, 12.5, .93, 1.87, 'https://www.alibabacloud.com/help/en/model-studio/model-pricing'),
    ('qwen3.8-omni-flash-realtime', 7, 12.5, .93, 1.87, 'https://www.alibabacloud.com/help/en/model-studio/realtime'),
    ('qwen-audio-3.1-realtime-plus', 12.5, 12.5, 6.4, 24, 'https://www.alibabacloud.com/help/en/model-studio/model-pricing'),
]:
    rows.append({'model': model, 'region': 'Singapore', 'basis': 'new audio only; two hypothetical input meters, not bill bounds', 'rates_per_million': {'audio_input': str(in_rate), 'audio_output': str(out_rate)}, 'tokens_per_second': {'audio_input': str(in_tps), 'audio_output': str(out_tps)}, 'usd_user_speech_input': str(audio_cost(USER_SPEECH_MINUTES, in_tps, out_tps, in_rate, out_rate)), 'usd_full_stream_input': str(audio_cost(SESSION_MINUTES, in_tps, out_tps, in_rate, out_rate)), 'source': source})
rows.extend([
    {'model': 'gemini-3.8-live / extended-thinking', 'usd': str(SESSION_MINUTES * D('.005') + ASSISTANT_MINUTES * D('.018')), 'basis': 'vendor approximate minutes; whole-session listening; no history/text/thinking', 'source': 'https://ai.google.dev/gemini-api/docs/pricing'},
    {'model': 'higgs-realtime', 'usd_user_speech_input': str(USER_SPEECH_MINUTES * D('.0023') + ASSISTANT_MINUTES * D('.014')), 'usd_full_stream_input': str(SESSION_MINUTES * D('.0023') + ASSISTANT_MINUTES * D('.014')), 'basis': 'vendor approximate minutes; actual token meter; transcription excluded', 'source': 'https://www.boson.ai/pricing'},
    {'model': 'gpt-realtime-2.1-mini', 'usd': str(audio_cost(USER_SPEECH_MINUTES, 10, 20, 10, 20)), 'basis': 'VAD only commits speech; no history/text/cache effects', 'source': 'https://developers.openai.com/api/docs/pricing'},
    {'model': 'gpt-realtime-2.1', 'usd': str(audio_cost(USER_SPEECH_MINUTES, 10, 20, 32, 64)), 'basis': 'VAD only commits speech; no history/text/cache effects', 'source': 'https://developers.openai.com/api/docs/pricing'},
    {'model': 'gpt-live-1', 'usd': str(SESSION_MINUTES * D('.05')), 'basis': 'active session including silence; backend excluded', 'source': 'https://developers.openai.com/api/docs/pricing'},
    {'model': 'grok-voice-3.0', 'usd': str(SESSION_MINUTES * D('.08')), 'basis': 'server_vad session; text events/tools excluded', 'source': 'https://docs.x.ai/developers/models/speech-to-speech'},
    {'model': 'ElevenAgents Creator', 'usd': str(D(22) + (SESSION_MINUTES - D(275)) * D('.08')), 'basis': 'regular monthly Creator plan, no first-month discount; LLM excluded', 'source': 'https://elevenlabs.io/pricing/agents'},
    {'model': 'Deepgram Voice Agent Standard', 'usd': str(SESSION_MINUTES * D('.075')), 'basis': 'post-2026-09-12 standard tier; configuration restrictions and external charges separate', 'source': 'https://deepgram.com/pricing'},
    {'model': 'stepaudio-3-realtime-preview', 'usd': None, 'basis': 'limited-time free model item; no guaranteed end date or account eligibility; not projected permanent zero', 'source': 'https://platform.stepfun.ai/docs/en/guides/pricing/details'},
])
output = {'date': '2026-10-15', 'currency': 'USD', 'days': 30, 'session_minutes': str(SESSION_MINUTES), 'user_speech_minutes': str(USER_SPEECH_MINUTES), 'assistant_speech_minutes': str(ASSISTANT_MINUTES), 'exclusions': ['history replay', 'text and reasoning', 'transcription', 'tools and backend agents', 'retries and reconnects', 'taxes and network', 'promotional discounts'], 'results': rows}
Path(__file__).with_name('calculations.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
for row in rows:
    print(row['model'], {k:v for k,v in row.items() if k.startswith('usd')})
