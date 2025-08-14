import re
from typing import Dict, Any, List, Tuple

from app.schemas import ParsedResult

# --- Constants and Regex Patterns ---
SEPARATORS = re.compile(r'[\._+]+')
BRACKETS = re.compile(r'[\[\](){}]')
YEAR_RE = re.compile(r'\b(19[89]\d|20\d{2})\b')
RESOLUTION_RE = re.compile(r'\b(2160p|1080p|720p|480p|4k)\b', re.I)
QUALITY_RE = re.compile(r'\b(WEB-?DL|BluRay|HDTV|DVDRip|BDRip|Remux|HDRip|CAM|WEBRip)\b', re.I)
VIDEO_CODEC_RE = re.compile(r'\b(x265|x264|HEVC|AVC|H\.?265|H\.?264|VP9|AV1)\b', re.I)
AUDIO_CODEC_RE = re.compile(r'\b(AAC|EAC3|AC-?3|DTS(?:-HD| MA)?|TrueHD|Atmos|Opus|MP3)\b', re.I)
GROUP_RE = re.compile(r'(?:-|\b)([a-zA-Z0-9]+)$|\[([a-zA-Z0-9\.\-]+)\]$')
KNOWN_GROUPS_RE = re.compile(r'\b(YTS|NTb|EVO|FGT|AMZN|NF|RARB|QxR|Tigole|PSA)\b', re.I)
SEASON_EP_RE = re.compile(r'\b(S(\d{1,2}))?[E|Ep|Episode]?(\d{1,3})\b', re.I)
SEASON_RE = re.compile(r'\b(S|Season)[. ]?(\d{1,2})\b', re.I)
EPISODE_RE = re.compile(r'\b(E|Ep|Episode)[. ]?(\d{1,3})\b', re.I)
EPISODE_RANGE_RE = re.compile(r'\bE(\d{1,3})[-–](\d{1,3})\b', re.I)
EPISODE_BRACKET_RANGE_RE = re.compile(r'Ep\[(\d{1,3})-(\d{1,3})\]', re.I)
SIZE_RE = re.compile(r'\b((\d+x)?(\d+(\.\d+)?)\s?(GB|MB|GiB|MiB))\b', re.I)
LANGUAGES_RE = re.compile(r'\[([^\]]*?(?:Tam|Hin|Eng|Tel|Mal|Kan|Mar|Ben)[^\]]*?)\]', re.I)

LANGUAGE_MAP = {
    'tamil': 'tam', 'tam': 'tam',
    'hindi': 'hin', 'hin': 'hin',
    'english': 'eng', 'eng': 'eng',
    'telugu': 'tel', 'tel': 'tel',
    'malayalam': 'mal', 'mal': 'mal',
    'kannada': 'kan', 'kan': 'kan',
    'marathi': 'mar', 'mar': 'mar',
    'bengali': 'ben', 'ben': 'ben',
    'multi': 'multi', 'dubbed': 'multi',
}

def _normalize_token(token: str) -> str:
    # Special cases to prevent incorrect replacements
    if re.match(r'x26[45]|h26[45]', token, re.I):
        return token
    return SEPARATORS.sub(' ', token)

def _clean_title(title: str) -> str:
    # First, replace separators in the whole string
    cleaned_title = SEPARATORS.sub(' ', title)
    # Remove brackets
    cleaned_title = BRACKETS.sub(' ', cleaned_title)
    # Collapse multiple spaces
    return re.sub(r'\s+', ' ', cleaned_title).strip()

def _parse_episodes(title_part: str) -> Tuple[List[int], Optional[str]]:
    episodes = set()
    range_str = None

    # E01-08 pattern
    if match := EPISODE_RANGE_RE.search(title_part):
        start, end = int(match.group(1)), int(match.group(2))
        episodes.update(range(start, end + 1))
        range_str = f"{start}-{end}"

    # Ep[1-8] pattern
    if match := EPISODE_BRACKET_RANGE_RE.search(title_part):
        start, end = int(match.group(1)), int(match.group(2))
        episodes.update(range(start, end + 1))
        range_str = f"{start}-{end}"

    # Individual episodes S01E01, E02 etc.
    for match in EPISODE_RE.finditer(title_part):
        episodes.add(int(match.group(2)))
        
    for match in SEASON_EP_RE.finditer(title_part):
        if match.group(3):
            episodes.add(int(match.group(3)))

    return sorted(list(episodes)), range_str

def _parse_languages(title_part: str) -> List[str]:
    langs = set()
    # Find bracketed language blocks first
    for match in LANGUAGES_RE.finditer(title_part):
        lang_block = match.group(1).lower()
        # Split by common delimiters inside brackets
        tokens = re.split(r'[+\-/,.\s]', lang_block)
        for token in tokens:
            if token in LANGUAGE_MAP:
                langs.add(LANGUAGE_MAP[token])

    # If no bracketed langs found, check for loose tokens
    if not langs:
        tokens = title_part.lower().split()
        for token in tokens:
            if token in LANGUAGE_MAP:
                langs.add(LANGUAGE_MAP[token])
    
    return sorted(list(langs))

def _parse_file_size(size_str: str) -> str:
    match = SIZE_RE.search(size_str)
    if not match:
        return None

    full_match, multiplier, num, _, unit = match.groups()
    total_size = float(num)

    if multiplier:
        total_size *= int(multiplier.replace('x', ''))

    unit = unit.lower()
    if 'gb' in unit or 'gib' in unit:
        return f"{total_size:.2f}GB"
    if 'mb' in unit or 'mib' in unit:
        if total_size >= 1000:
            return f"{total_size/1024:.2f}GB"
        return f"{int(total_size)}MB"
    return full_match

def parse_with_regex(original_title: str) -> Tuple[Dict[str, Any], str]:
    working_title = original_title
    data = {}
    hits = 0

    # Process Year
    if match := YEAR_RE.search(working_title):
        data['year'] = int(match.group(1))
        working_title = working_title.replace(match.group(0), '', 1)
        hits += 1

    # Process Resolution
    if match := RESOLUTION_RE.search(working_title):
        res = match.group(1).lower()
        data['resolution'] = '2160p' if res == '4k' else res
        working_title = working_title.replace(match.group(0), '', 1)
        hits += 1

    # Process Quality
    if match := QUALITY_RE.search(working_title):
        data['quality'] = match.group(1).replace('-', '').upper()
        working_title = working_title.replace(match.group(0), '', 1)
        hits += 1
        if data['quality'] in ['WEBDL', 'WEBRIP']:
            data['source'] = 'web'
        elif data['quality'] in ['BLURAY', 'BDRIP', 'REMUX']:
            data['source'] = 'bluray'
        else:
            data['source'] = 'p2p' # assumption
            
    # Process Codecs
    if match := VIDEO_CODEC_RE.search(working_title):
        codec = match.group(1).upper()
        if '265' in codec: data['video_codec'] = 'x265'
        elif '264' in codec: data['video_codec'] = 'x264'
        else: data['video_codec'] = codec
        working_title = working_title.replace(match.group(0), '', 1)
        hits += 1
        
    if match := AUDIO_CODEC_RE.search(working_title):
        data['audio_codec'] = match.group(1).replace('-', '').upper()
        working_title = working_title.replace(match.group(0), '', 1)
        hits += 1

    # Process Season
    if match := SEASON_RE.search(working_title):
        data['season'] = int(match.group(2))
        working_title = working_title.replace(match.group(0), '', 1)
        hits += 1
        
    # Process Episodes
    episodes, episode_range = _parse_episodes(working_title)
    if episodes:
        data['episodes'] = episodes
        if episode_range:
            data['episode_range'] = episode_range
        hits += 1

    # Process Languages
    languages = _parse_languages(original_title)
    if languages:
        data['audio_languages'] = languages
        hits += 1
    
    # Process File Size
    file_size = _parse_file_size(original_title)
    if file_size:
        data['file_size'] = file_size
        hits += 1

    # Clean the working title from metadata remnants
    cleaned_for_group = _clean_title(working_title)

    # Process Group (last)
    group = None
    if match := GROUP_RE.search(original_title):
        group = next((g for g in match.groups() if g is not None), None)
    if not group:
        if match := KNOWN_GROUPS_RE.search(cleaned_for_group):
            group = match.group(1)
            
    if group:
        data['group'] = group
        # Remove group from cleaned title for final title extraction
        cleaned_for_group = re.sub(r'\b' + re.escape(group) + r'\b', '', cleaned_for_group, flags=re.I)
        hits += 1

    # Final Title cleanup
    # Remove season/episode markers from the title itself
    final_title_str = re.sub(SEASON_RE, '', cleaned_for_group, flags=re.I)
    final_title_str = re.sub(EPISODE_RE, '', final_title_str, flags=re.I)
    final_title_str = re.sub(EPISODE_RANGE_RE, '', final_title_str, flags=re.I)
    final_title_str = re.sub(EPISODE_BRACKET_RANGE_RE, '', final_title_str, flags=re.I)
    final_title_str = re.sub(r'\b(S\d{2})', '', final_title_str, flags=re.I) # S01 from S01E02
    
    # Remove known groups again if they appear at start/middle
    if data.get('group'):
        final_title_str = re.sub(r'\b' + re.escape(data['group']) + r'\b', '', final_title_str, flags=re.I)

    # Final cleanup of separators and spacing
    final_title_str = _clean_title(final_title_str).strip()
    
    # Confidence score from regex hits (max ~8-10 hits, normalize to ~0.7)
    confidence = min(hits / 8.0, 0.7)
    
    result = {"confidence": confidence, **data}
    return result, final_title_str
