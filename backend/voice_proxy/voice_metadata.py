import json
import ast
import re
from typing import Any, Dict, Optional, Mapping


def _safe_parse_json(s: str) -> Any:
    if not isinstance(s, str):
        return s
    s_str = s.strip()
    try:
        return json.loads(s_str)
    except Exception:
        pass
    if '}{' in s_str:
        try:
            return json.loads('[' + s_str.replace('}{', '},{') + ']')
        except Exception:
            pass
    start = s_str.find('{')
    end = s_str.rfind('}')
    if start != -1 and end > start:
        try:
            return json.loads(s_str[start:end + 1])
        except Exception:
            pass
    try:
        return ast.literal_eval(s_str)
    except Exception:
        pass
    return s


def _stitch_chunks(data, prefix):
    pattern = re.compile(re.escape(prefix) + r'_chunk_(\d+)$')
    parts = []
    for k in sorted(data.keys()):
        m = pattern.match(k)
        if m:
            parts.append((int(m.group(1)), str(data[k])))
    if not parts:
        return None
    parts.sort(key=lambda x: x[0])
    return ''.join(p for _, p in parts)


def _flatten_dict(d, parent_key='', sep='.'):
    items = {}
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, Mapping):
            items.update(_flatten_dict(v, new_key, sep=sep))
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, Mapping):
                    items.update(_flatten_dict(item, f"{new_key}[{i}]", sep=sep))
                else:
                    items[f"{new_key}[{i}]"] = item
        else:
            items[new_key] = v
    return items


def parse_voice_live_metadata(data):
    raw = None
    if 'voiceLiveConfig' in data:
        raw = data['voiceLiveConfig']
    else:
        stitched = _stitch_chunks(data, 'voiceLiveConfig')
        if stitched:
            raw = stitched
        else:
            raw = data.get('voiceLiveConfig_meta')
    if raw is None:
        return {}
    parsed = _safe_parse_json(raw)
    if isinstance(parsed, list) and len(parsed) == 1:
        parsed = parsed[0]
    if not isinstance(parsed, dict):
        return {}
    candidate = parsed.get('config') if isinstance(parsed.get('config'), dict) else parsed
    return _flatten_dict(candidate)


def extract_selected_fields(flat):
    def first_of(keys):
        for key in keys:
            if key in flat:
                return flat[key]
        return None
    return {
        'language': first_of(['speech.language', 'language']),
        'shortName': first_of(['speech.voice.shortName', 'shortName']),
        'voiceType': first_of(['speech.voice.voiceType', 'voiceType']),
        'voiceActivityDetection': first_of(['speech.voiceActivityDetection', 'voiceActivityDetection']),
        'noiseSuppression': first_of(['speech.noiseSuppression', 'noiseSuppression']),
        'echoCancellation': first_of(['speech.echoCancellation', 'echoCancellation']),
        'avatarName': first_of(['avatar.selectedAvatar.avatarName', 'avatarName']),
    }
