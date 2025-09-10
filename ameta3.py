import requests

def get_iana_tlds():
    """Fetch IANA TLDs from the official source"""
    try:
        response = requests.get('https://data.iana.org/TLD/tlds-alpha-by-domain.txt', timeout=10)
        if response.status_code == 200:
            # Parse the response, skip comments and empty lines
            tlds = [line.strip().lower() for line in response.text.splitlines()
                    if line.strip() and not line.startswith('#')]
            return set(tlds)
    except:
        # Fallback to common TLDs if fetch fails
        return {'com', 'org', 'net', 'to', 'ws', 'tax', 'mu', 'by', 'online', 'pro'}
    return {'com', 'org', 'net', 'to', 'ws', 'tax', 'mu', 'by', 'online', 'pro'}

def tokenize(filename):
    s = filename
    tokens = []
    current = []
    i = 0

    # Get IANA TLDs
    TLDS = get_iana_tlds()

    while i < len(s):
        c = s[i]
        if c.isalnum():
            current.append(c)
            i += 1
        elif c == '.':
            if current and ''.join(current).lower().startswith('www'):
                current.append(c)
                i += 1
            elif i+1 < len(s) and s[i+1].isdigit() and current and current[-1].isdigit():
                current.append(c)
                i += 1
            else:
                if current:
                    tokens.append(''.join(current))
                    current = []
                i += 1
        elif c == '-':
            if i+1 < len(s) and s[i+1].isdigit() and current and current[-1].isdigit():
                current.append(c)
                i += 1
            else:
                if current:
                    tokens.append(''.join(current))
                    current = []
                i += 1
        else:
            if current:
                tokens.append(''.join(current))
                current = []
            i += 1
    if current:
        tokens.append(''.join(current))
    return tokens

# ========== ADD THE CATEGORIZATION MODULE BELOW ==========

def categorize_tokens(tokens):
    categorized = []
    n = len(tokens)

    # Get IANA TLDs
    TLDS = get_iana_tlds()

    # Expanded known values - all converted to lowercase for case-insensitive matching
    RESOLUTIONS = {r.lower() for r in {
        '240p','360p','480p','540p','576p',
        '720p','1080p','1440p','2160p','4320p',
        '2K','2k','4K','8K','2k','3K',
        'SD','HD','FHD','UHD',
        'HDR','HDR10','HDR10+','DolbyVision','DV','SDTV','HDTV'
    }}

    QUALITIES = {q.lower() for q in {
        'CAM','CAMRip','TS','TELESYNC','TC','SCR','DVDScr','R5','PDVD',
        'DVDRip','DVD','DVD5','DVD9','HDRip','HDCAM','HDTS',
        'WEB-DL','WEBDL','WEB_DL','WEBRip','WEB','WEBRIP','TVRip'
        'BDRip','BRRip','BluRay','Blu-ray','BD25','BD50','BD',
        'Remux','REMUX','Remux','PROPER','REPACK',
        'LIMITED','UNRATED','EXTENDED','INTERNAL','SCREENER','WORKPRINT','WP'
    }}

    VIDEO_CODECS = {v.lower() for v in {
        'x264','x265','h264','h265','H.264','H.265',
        'HEVC','AVC','AV1','VP9','MPEG2','MPEG-2','MPEG4',
        'DivX','XviD','ProRes','VVC','H266'
    }}

    AUDIO_CODECS = {a.lower() for a in {
        'AAC','AAC2.0','AAC5.1','AC3','DD','DD2.0','DD5.1',
        'E-AC3','EAC3','DDP','DDP5.1','DTS','DTS-HD','DTS-HD MA','DTS:X',
        'TrueHD','Dolby TrueHD','Atmos','FLAC','OPUS','MP3','WAV','PCM','ALAC',
        '2.0','5.1','7.1','Stereo','Mono'
    }}

    SOURCES = {s.lower() for s in {
        'AMZN','Amazon','iTunes','ITUNES','NF','NETFLIX','Netflix',
        'DSNP','Disney+','DisneyPlus','HMAX','HBO','HBO Max','HULU','Hulu',
        'AppleTV','AppleTV+','Prime','PrimeVideo','GooglePlay','GPLAY',
        'Peacock','Paramount+','Paramount','BBC','ITV','CBS','NBC','FOX',
        'CRUNCHYROLL','CR','Ullu','Originals','Jio','Hotstar','SonyLiv'
    }}

    # Language sets - separate two-letter codes for context-aware processing
    LANGUAGES_FULL = {l.lower() for l in {
        # Global
        'ENG','English','SPA','Spanish','FRE','French','FRENCH',
        'ITA','Italian','DEU','German','GER','PT','Portuguese','RUS','Russian',
        'JP','JPN','Japanese','KOR','Korean','CHN','Chinese','AR','Arabic',

        # Major Indian languages
        'HIN','Hindi','TAM','Tamil','TEL','Telugu','MAL','Malayalam','KAN','Kannada',
        'Bengali','MAR','Marathi','PUN','Punjabi','GUJ','Gujarati','ORI','Odia','ASM','Assamese'
    }}

    # Two-letter language codes that need context-aware processing
    LANGUAGES_TWO_LETTER = {l.lower() for l in {
        'EN', 'ES', 'FR', 'IT', 'DE', 'PT', 'RU', 'JP', 'KO', 'CN', 'AR',
        'HI', 'TA', 'TE', 'ML', 'KN', 'BN', 'MR', 'PA', 'GU', 'OR', 'AS'
    }}

    SUBTITLES = {s.lower() for s in {
        'SUB','SUBS','SUBBED','Subs','EngSubs','engsubs','ESubs','VOST','VOSTFR','VOSTEN',
        'MULTiSUB','MULTiSUBS','Multi-Subs','MSubs','HardSub','Hardsub','SoftSubs','ForcedSub','Forced-Sub','CC','ClosedCaptions','sub'
    }}

    FILE_EXTENSIONS = {f.lower() for f in {
        'mkv','mp4','avi','iso','mpeg','mpg','ts','m2ts','mov','wmv','flv','3gp','vob','m4v','webm','mka'
    }}

    SEASON_INDICATORS = {s.lower() for s in {'season','seasons','s','S','Series','SERIES'}}
    EPISODE_INDICATORS = {e.lower() for e in {'episode','episodes','ep','eps','e','E','Part','Chapter','pt','Pt','ch'}}

    COMPLETE_INDICATORS = {c.lower() for c in {
        'complete', 'COMPLETE', 'full', 'full season', 'season pack',
        'collection', 'collections', 'COLLECTION', 'COLLECTIONS',
        'boxset', 'BOXSET', 'set', 'SET', 'anthology', 'compilation', 'omnibus',
        'series', 'SERIES', 'tvpack', 'tv-pack', 'tv pack', 'seasonal pack',
        'franchise', 'saga', 'universe',
        'duology', 'trilogy', 'tetralogy', 'quadrilogy', 'pentalogy', 'pentology',
        'hexalogy', 'hexology', 'heptalogy', 'septology', 'octalogy', 'nonalogy', 'ennealogy',
        'decalogy', 'decology', 'multilogy',
        'tri-pack', 'quad-pack', 'penta-pack', 'mega-pack', 'gigapack', 'ultrapack',
        '全集', 'completo', 'complète', 'complet', 'komplett', 'coleccion', 'collezione'
    }}

    # First pass: Identify all metadata with high confidence
    metadata_map = {}
    for i, token in enumerate(tokens):
        lower_token = token.lower()

        # Website detection
        if ('.' in token and (token.lower().startswith('www.') or
            any('.' + tld in token.lower() for tld in TLDS))):
            metadata_map[i] = ('website', token)
            continue

        # Year detection
        if (len(token) == 4 and token.isdigit() and 1900 <= int(token) <= 2030):
            metadata_map[i] = ('year', token)
            continue

        # Year range detection
        if ('-' in token and all(part.isdigit() and len(part) == 4 for part in token.split('-'))):
            metadata_map[i] = ('year_range', token)
            continue

        # Resolution detection
        if (lower_token in RESOLUTIONS or
            (token.endswith('p') and token[:-1].isdigit()) or
            (token.endswith('P') and token[:-1].isdigit())):
            metadata_map[i] = ('resolution', token)
            continue

        # Quality detection
        if lower_token in QUALITIES:
            metadata_map[i] = ('quality', token)
            continue

        # Video codec detection
        if lower_token in VIDEO_CODECS:
            metadata_map[i] = ('video_codec', token)
            continue

        # Audio codec detection
        if lower_token in AUDIO_CODECS:
            metadata_map[i] = ('audio_codec', token)
            continue

        # Source detection
        if lower_token in SOURCES:
            metadata_map[i] = ('source', token)
            continue

        # Language detection - full language names first
        if lower_token in LANGUAGES_FULL:
            metadata_map[i] = ('language', token)
            continue

        # Subtitles detection
        if lower_token in SUBTITLES:
            metadata_map[i] = ('subtitles', token)
            continue

        # File extension detection
        if lower_token in FILE_EXTENSIONS:
            metadata_map[i] = ('file_extension', token)
            continue

        # File size detection
        if (token.endswith(('GB', 'MB')) and token[:-2].replace('.', '').isdigit()):
            metadata_map[i] = ('file_size', token)
            continue

    # Second pass: Title detection with contextual awareness
    # Find the first non-website token as potential title start
    title_start = 0
    for i in range(n):
        if i in metadata_map and metadata_map[i][0] == 'website':
            title_start = i + 1
        else:
            break

    # Find title end (before any metadata)
    title_end = title_start
    for i in range(title_start, n):
        if i in metadata_map:
            title_end = i
            break
    else:
        title_end = n

    # New pass: Context-aware language detection for two-letter codes
    # Only tag two-letter codes as language if they're near metadata
    for i, token in enumerate(tokens):
        lower_token = token.lower()

        # Skip if already categorized or not a two-letter language code
        if i in metadata_map or lower_token not in LANGUAGES_TWO_LETTER:
            continue

        # Check if this token is near metadata (not in the middle of title)
        is_near_metadata = False

        # Check previous tokens (up to 3 tokens back)
        for j in range(max(0, i-3), i):
            if j in metadata_map and metadata_map[j][0] in ('resolution', 'quality', 'video_codec',
                                                          'audio_codec', 'source', 'file_size',
                                                          'year', 'year_range'):
                is_near_metadata = True
                break

        # Check next tokens (up to 3 tokens forward)
        if not is_near_metadata:
            for j in range(i+1, min(n, i+4)):
                if j in metadata_map and metadata_map[j][0] in ('resolution', 'quality', 'video_codec',
                                                              'audio_codec', 'source', 'file_size',
                                                              'year', 'year_range'):
                    is_near_metadata = True
                    break

        # Also check if it's part of a language list pattern (e.g., "ENG ITA SPA")
        if not is_near_metadata and i > 0 and i < n-1:
            prev_lower = tokens[i-1].lower()
            next_lower = tokens[i+1].lower()

            if (prev_lower in LANGUAGES_FULL or prev_lower in LANGUAGES_TWO_LETTER or
                next_lower in LANGUAGES_FULL or next_lower in LANGUAGES_TWO_LETTER):
                is_near_metadata = True

        # Tag as language only if near metadata or part of language list
        if is_near_metadata:
            metadata_map[i] = ('language', token)

    # Third pass: Season and episode detection with context awareness
    i = 0
    while i < n:
        if i in metadata_map:
            i += 1
            continue

        token = tokens[i]
        lower_token = token.lower()

        # Combined season-episode patterns (highest priority)
        if ('e' in lower_token and lower_token.startswith('s') and
            any(c.isdigit() for c in token) and len(token) > 3):
            # Handle S01E02 pattern
            if lower_token[0] == 's' and 'e' in lower_token:
                s_part, e_part = lower_token.split('e', 1)
                if s_part[1:].isdigit() and e_part.isdigit():
                    metadata_map[i] = ('season_episode', token)
                    i += 1
                    continue

        # Season patterns
        if (lower_token.startswith('s') and len(token) > 1 and
            (token[1:].isdigit() or ('.' in token[1:] and token[1:].split('.')[0].isdigit()))):
            metadata_map[i] = ('season', token)
            i += 1
            continue

        # Episode patterns
        if (lower_token.startswith('e') and len(token) > 1 and
            (token[1:].isdigit() or ('.' in token[1:] and token[1:].split('.')[0].isdigit()))):
            metadata_map[i] = ('episode', token)
            i += 1
            continue

        # Season indicators with context
        if lower_token in SEASON_INDICATORS and i+1 < n:
            metadata_map[i] = ('season_indicator', token)
            # Check if next token is a season number
            next_token = tokens[i+1]
            if (next_token.isdigit() or
                (next_token.startswith(('s', 'S')) and any(c.isdigit() for c in next_token)) or
                ('-' in next_token and any(c.isdigit() for c in next_token))):
                if i+1 not in metadata_map:
                    metadata_map[i+1] = ('season_number', next_token)
                i += 2
                continue
            i += 1
            continue

        # Episode indicators with context
        if lower_token in EPISODE_INDICATORS and i+1 < n:
            metadata_map[i] = ('episode_indicator', token)
            # Check if next token is an episode number
            next_token = tokens[i+1]
            if (next_token.isdigit() or
                (next_token.startswith(('e', 'E')) and any(c.isdigit() for c in next_token)) or
                ('-' in next_token and any(c.isdigit() for c in next_token))):
                if i+1 not in metadata_map:
                    metadata_map[i+1] = ('episode_number', next_token)
                i += 2
                continue
            i += 1
            continue

        i += 1

    # Fourth pass: Backward-looking for episode and season numbers
    # Handle cases like "11 episodes" where the number comes before the indicator
    for i in range(n):
        if i in metadata_map:
            continue

        token = tokens[i]
        lower_token = token.lower()

        # Check for episode indicators that might have a number before them
        if lower_token in EPISODE_INDICATORS and i > 0:
            prev_token = tokens[i-1]
            # If previous token is a number and not already categorized as something else
            if (prev_token.isdigit() and
                (i-1 not in metadata_map or metadata_map[i-1][0] == 'title')):
                metadata_map[i-1] = ('episode_number', prev_token)
                metadata_map[i] = ('episode_indicator', token)

        # Check for season indicators that might have a number before them
        if lower_token in SEASON_INDICATORS and i > 0:
            prev_token = tokens[i-1]
            # If previous token is a number and not already categorized as something else
            if (prev_token.isdigit() and
                (i-1 not in metadata_map or metadata_map[i-1][0] == 'title')):
                metadata_map[i-1] = ('season_number', prev_token)
                metadata_map[i] = ('season_indicator', token)

    # Fifth pass: Complete indicator detection with context awareness
    # Only mark as complete indicator if it's surrounded by metadata on both sides
    for i in range(n):
        if i in metadata_map:
            continue

        token = tokens[i]
        lower_token = token.lower()

        if lower_token in COMPLETE_INDICATORS:
            # Check if it's surrounded by metadata
            has_metadata_before = False
            has_metadata_after = False

            # Check before
            for j in range(i-1, -1, -1):
                if j in metadata_map:
                    has_metadata_before = True
                    break
                if j < title_end:  # Stop if we reach title section
                    break

            # Check after
            for j in range(i+1, n):
                if j in metadata_map:
                    has_metadata_after = True
                    break
                if j < title_end:  # Stop if we reach title section
                    break

            # Only mark as complete indicator if it's surrounded by metadata
            if has_metadata_before and has_metadata_after:
                metadata_map[i] = ('complete_indicator', token)

    # Sixth pass: Enhanced validation for episode/season numbers
    # Ensure numbers following episode/season indicators are properly categorized
    for i in range(n):
        if i in metadata_map:
            continue

        token = tokens[i]

        # Check if this is a number that should be part of episode/season
        if token.isdigit() or ('-' in token and any(c.isdigit() for c in token)):
            # Look for nearby episode or season indicators
            has_nearby_indicator = False

            # Check previous tokens
            for j in range(max(0, i-3), i):
                if j in metadata_map and metadata_map[j][0] in ('episode_indicator', 'season_indicator', 'episode', 'season'):
                    has_nearby_indicator = True
                    break

            # Check next tokens
            if not has_nearby_indicator:
                for j in range(i+1, min(n, i+4)):
                    if j in metadata_map and metadata_map[j][0] in ('episode_indicator', 'season_indicator', 'episode', 'season'):
                        has_nearby_indicator = True
                        break

            if has_nearby_indicator:
                # Determine if it's episode or season number based on context
                is_episode = False
                is_season = False

                # Check previous tokens
                for j in range(max(0, i-3), i):
                    if j in metadata_map:
                        if metadata_map[j][0] in ('episode_indicator', 'episode'):
                            is_episode = True
                        elif metadata_map[j][0] in ('season_indicator', 'season'):
                            is_season = True

                # Check next tokens
                for j in range(i+1, min(n, i+4)):
                    if j in metadata_map:
                        if metadata_map[j][0] in ('episode_indicator', 'episode'):
                            is_episode = True
                        elif metadata_map[j][0] in ('season_indicator', 'season'):
                            is_season = True

                if is_episode:
                    metadata_map[i] = ('episode_number', token)
                elif is_season:
                    metadata_map[i] = ('season_number', token)

    # Seventh pass: Episode name detection with validation
    # Episode name can only exist if we have a title
    episode_start = title_end
    episode_end = title_end

    if title_end < n:
        # Skip year if it's right after title
        if (title_end in metadata_map and
            metadata_map[title_end][0] in ('year', 'year_range')):
            episode_start = title_end + 1
        else:
            episode_start = title_end

        # Find episode end (before technical metadata)
        for i in range(episode_start, n):
            if (i in metadata_map and
                metadata_map[i][0] in ('resolution', 'quality', 'video_codec',
                                      'audio_codec', 'source', 'file_size')):
                episode_end = i
                break
        else:
            episode_end = n

    # Eighth pass: Group detection (at the end, after technical metadata)
    group_candidates = []
    tech_metadata_start = n

    # Find where technical metadata starts
    for i in range(n):
        if (i in metadata_map and
            metadata_map[i][0] in ('resolution', 'quality', 'video_codec',
                                  'audio_codec', 'source', 'file_size')):
            tech_metadata_start = i
            break

    # Group candidates are at the end, after technical metadata
    for i in range(n-1, tech_metadata_start-1, -1):
        if i in metadata_map:
            if metadata_map[i][0] not in ('website', 'file_extension'):
                break
        else:
            # Group candidates are typically alphanumeric without being pure numbers
            if (tokens[i].isalpha() or
                (any(c.isalpha() for c in tokens[i]) and not tokens[i].isdigit())):
                group_candidates.append(i)
            else:
                break

    # Mark groups
    for i in group_candidates:
        metadata_map[i] = ('group', tokens[i])

    # Ninth pass: Enhanced validation for metadata
    # Check for misclassified tokens and correct them
    for i in range(n):
        if i in metadata_map:
            continue

        token = tokens[i]
        lower_token = token.lower()

        # Check for resolution patterns that might have been missed
        if (token.endswith('P') and token[:-1].isdigit() and
            token not in metadata_map.values()):
            metadata_map[i] = ('resolution', token)
            continue

        # Check for video codec patterns that might have been split
        if (i < n-1 and token in {'H', 'x'} and
            tokens[i+1].isdigit() and tokens[i+1] not in metadata_map):
            # Handle cases like "H 264" which should be "H.264"
            combined = token + '.' + tokens[i+1]
            if combined.lower() in VIDEO_CODECS:
                metadata_map[i] = ('video_codec', combined)
                metadata_map[i+1] = ('ignore', tokens[i+1])  # Mark next token to be ignored
                continue

    # Tenth pass: Strict title boundary enforcement
    # Once metadata starts, no more title should be tagged
    final_metadata_map = metadata_map.copy()
    strict_title_end = title_end

    # Ensure no title tags beyond the first metadata
    for i in range(title_end, n):
        if i in final_metadata_map and final_metadata_map[i][0] != 'website':
            strict_title_end = i
            break

    # Eleventh pass: Compile final categorization with validation
    for i in range(n):
        if i in final_metadata_map:
            # Skip ignored tokens
            if final_metadata_map[i][0] == 'ignore':
                continue
            categorized.append(final_metadata_map[i])
        elif i < strict_title_end:
            # Title section
            categorized.append(('title', tokens[i]))
        elif i < episode_end:
            # Episode name section with validation
            # Episode name shouldn't be a language, resolution, or pure number
            if (tokens[i].lower() not in LANGUAGES_FULL and
                tokens[i].lower() not in LANGUAGES_TWO_LETTER and
                not tokens[i].isdigit() and
                not (tokens[i].endswith('GB') or tokens[i].endswith('MB')) and
                tokens[i].lower() not in RESOLUTIONS):
                categorized.append(('episode_name', tokens[i]))
            else:
                categorized.append(('other', tokens[i]))
        else:
            # Remaining tokens that weren't categorized
            if tokens[i].isdigit():
                categorized.append(('unknown_digit', tokens[i]))
            else:
                categorized.append(('other', tokens[i]))

    return categorized

# ========== MODIFIED MAIN FUNCTION ==========

if __name__ == '__main__':
    test_cases = [
        "[Judas] Saikyou no Shienshoku Wajutsushi de Aru Ore wa Sekai Saikyou Clan wo Shitagaeru (Season 1) (Season 01) [1080p][HEVC x265 10bit][Multi-Subs]",
        "Suits (Season 07 Episode 05)(www.kinokopilka.pro)",
        "Suits (Season 07 Episode 08)(www.kinokopilka.pro)",
        "Senke nad Balkanom (2017) (S01.ep 7.8-10) 1080p",
        "Mr. Robot [WEB-DL-1080p] (Season 03 Episode 03) (www.kinokopilka.pro)",
        "Game Of Thrones (Season 06 Episode 06)(www.kinokopilka.pro)",
        "Elementary (Season 06 Episodes 03-04)(www.kinokopilka.pro)",
        "Borcy.za.svobodu.Luch (S1-2_EP1-12) (2017-2018)WEB-DLRip",
        "Justin T & Rihanna @ Alan Carr. Chatty Man. 27Sep2013 (S11E05. 100th episode Special)",
        "Senke nad Balkanom (2017) (S01.ep 9.10-10) 1080p",
        "Goldrake.U(S01 EP 09-13)[1080P H264 ITA AAC JP AAC WEBDL RAI NotSmirco]",
        "Borgen (Danish TV Series) (Complete) (S1-3) (2010-2013) 1080p H.264 (moviesbyrizzo) engsubs",
        "Supernatural (S10)(2014)(WebDl)(FHD)(1080p)(AVC)(Multi 6 lang)(MultiSUB) PHDTeam",
        "The Simpsons (S16)(2004)(Complete)(HD)(720p)(WebDl)(x264)(AAC 2.0-Multi 8 lang)(MultiSub) PHDTeam",
        "Harry Potter 1. (Y la piedra filosofal).(2001).(HDRip.Esp)",
        "Black Bullet (Season 1) (BD 1080p)(HEVC x265 10bit)(Dual-Audio)(Eng-Subs)-Judas[TGx]",
        "The Simpsons (S07)(1995)(Complete)(HD)(720p)(WebDl)(x264)(AAC 2.0-Multi 8 lang)(MultiSub) PHDTeam",
        "Kyokou Suiri (In-Spectre) (Season 1) (1080p)(HEVC x265 10bit)(Multi-Subs)-Judas[TGx]",
        "Ghosts (US) (2021) Season 3 S03 (1080p AMZN WEB-DL x265 HEVC 10bit EAC3 5.1 Silence)",
        "Outer Range (S01E01)(2022)(FHD)(1080p)(x264)(WebDL)(Multi 9 Lang)(MultiSUB) PHDTeam",
        "The Simpsons (S14)(2002)(Complete)(HD)(720p)(WebDl)(x264)(AAC 2.0-Multi 8 lang)(MultiSub) PHDTeam",
        "The Expanse (S03)(2018)(Hevc)(1080p)(WebDL)(14 lang AAC- 2.0) PHDTeam",
        "Greatness Code (2020) S01 Season 1 (DOCU)(1080p 4KWEBRip x265 HEVC E-AC3-AAC 5.1)[Cømpact-cTurtle]",
        "Invincible (S02E03)(2023)(Hevc)(1080p)(WebDL)(28 lang EAC3 5.1)(MultiSUB) PHDTeam",
        "Агасси - Куэртен (1-2 Los Angeles - 2001); Агасси - Сампрас (финал Los Angeles - 2001)",
        "Trashopolis (11 episodes) (2010-2011) SATRip [Hurtom]",
        "Dhanbad Blues (2018) (Season 1 All Episodes - Ep 01-09) [720p WEB-DL x264] [Bengali AAC] (Suryadipta1)",
        "[AnimeRG] One Piece (Season 19) Whole Cake Island (Episodes 783-891) [1080p] [Multi-Sub] [HEVC] [x265] [pseudo]",
        "Ultimate Spider-Man vs the Sinister 6 [Season 4](Episodes 17 - 21)(WebRip-H264-AAC){Shon}[WWRG]",
        "Endless.Night.S01.COMPLETE.FRENCH.720p.NF.WEBRip.x264-GalaxyTV[TGx]",
        "Whiskey.Cavalier.S01.COMPLETE.720p.AMZN.WEBRip.x264-GalaxyTV[TGx]",
        "Centennial 1978 Season 1 Complete TVRip x264 [i_c]",
        "A Complete Unknown (Un completo desconocido) (2024) sub.mp4",
        "Guardian.2018.Complete.4K.WEB-DL.H265.AAC-TJUPT",
        "Southland (2009) Complete Series Uncensored + Bonus Features DVD Rip 1080p AI Uspcaled",
        "Tekwar The Series 1994 Season 1 Complete DVDRip x264 [i_c]",
        "Naked and Afraid Season 8 Complete 720p HDTV x264 [i_c]",
        "Griselda.S01.COMPLETE.1080p.ENG.ITA.HINDI.LATINO.Multi.Sub.DDP5.1.Atmos.MKV-BEN.THE.MEN",
        "[OCN] Doctor.Frost.2014.COMPLETE.720p.HDTV.x264.Film.iVTC.AAC-SODiHD",
        "www.TamilRockers.to - Apharan (2018) Hind - Season 1 Complete - 720p HDRip x264 - 2GB.mkv",
        "www.TamilMv.tax - Naga Chaitanya - Telugu Complete Collections (2009 - 2017) - 13 Movies [ 720p - HDRip - x264 - 16GB ]",
        "www.TamilRockers.ws - Sacred Games (2019) Season 02 - Complete - 1080p TRUE HD - [Hindi + English] - x264 - DDP 5.1 - 11.4GB - MSubs",
        "www.TamilRockers.to - Selection Day Season 1 Complete  (2018) Hindi 1080p HD AVC [Hindi + Eng] - x264 6GB ESubs(Multi)",
        "www.TamilMv.tax - Nani Telugu Complete Collections (2008 - 2017) - 20 Movies [ 720p - HDRip - x264 - 27GB ]",
        "www.TamilRockers.mu - Karenjit Kaur (2018) Complete Season 2 [1080p HD AVC - [Tamil + Hindi + Malayalam] - x264 - 3GB - ESubs]",
        "www.TamilRockers.mu - Karenjit Kaur (2018) Complete Season 2 [HDRip - [Tamil + Hindi + Malayalam] - x264 - 450MB - ESubs].mkv",
        "www.TamilRockers.by - The Haunting of Hill House  (2018) [English - Season 1 - Complete (EP 01 - 10) - 720p HDRip - x264 - 5.1 - ESubs - 3.3GB]",
        "www.TamilRockers.by - The Haunting of Hill House  (2018) [English - Season 1 - Complete (EP 01 - 10) - 1080p HDRip - x264 - AC3 5.1 - ESubs - 6.1GB]",
        "TamilVaathi.online - Money Heist (2017) Season 01 Complete 720p HDRip x265 AAC Spanish+ English 3.3GB Esub",
        "Below.Deck.Mediterranean.S04E13.Its.Ben.a.Long.Time.720p.HDTV.x264-CRiMSON[eztv].mkv"
    ]

    for filename in test_cases:
        tokens = tokenize(filename)
        categorized = categorize_tokens(tokens)

        print(f"Filename: {filename}")
        print(f"Tokens: {tokens}")
        print("Categorized:")
        for category, value in categorized:
            print(f"  {category}: {value}")
        print("-" * 80)
