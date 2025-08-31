import re
import json
from typing import Dict, List, Optional, Tuple, Set, Any, Union
from datetime import datetime
import logging
from collections import Counter
import unicodedata

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TorrentParser:
    def __init__(self):
        self.season_patterns = self._compile_season_patterns()
        self.episode_patterns = self._compile_episode_patterns()
        self.resolution_patterns = self._compile_resolution_patterns()
        self.video_codec_patterns = self._compile_video_codec_patterns()
        self.audio_codec_patterns = self._compile_audio_codec_patterns()
        self.language_patterns = self._compile_language_patterns()
        self.filesize_patterns = self._compile_filesize_patterns()
        self.filetype_patterns = self._compile_filetype_patterns()
        self.quality_patterns = self._compile_quality_patterns()
        self.year_patterns = self._compile_year_patterns()
        self.website_patterns = self._compile_website_patterns()
        self.encoder_patterns = self._compile_encoder_patterns()
        self.group_patterns = self._compile_group_patterns()
        self.reject_hashed_regexes = self._compile_reject_hashed_regexes()
        self.pre_substitution_regexes = self._compile_pre_substitution_regexes()
        self.anime_patterns = self._compile_anime_patterns()
        self.special_episode_patterns = self._compile_special_episode_patterns()

    def _compile_pre_substitution_regexes(self):
        """Compile regex patterns for pre-processing titles"""
        return [
            # Korean series without season number
            (re.compile(r'\.E(\d{2,4})\.\d{6}\.(.*-NEXT)$', re.IGNORECASE), ".S01E$1.$2"),

            # Chinese anime releases with both English and Chinese titles
            (re.compile(r'^\[(?:(?P<subgroup>[^\]]+?)(?:[\u4E00-\u9FCC]+)?)\]\[(?P<title>[^\]]+?)(?:\s(?P<chinesetitle>[\u4E00-\u9FCC][^\]]*?))\]\[(?:(?:[\u4E00-\u9FCC]+?)?(?P<episode>\d{1,4})(?:[\u4E00-\u9FCC]+?)?)\]', re.IGNORECASE),
            "[${subgroup}] ${title} - ${episode} - "),

            # Chinese LoliHouse/ZERO/Lilith-Raws releases
            (re.compile(r'^\[(?P<subgroup>[^\]]*?(?:LoliHouse|ZERO|Lilith-Raws|Skymoon-Raws|orion origin)[^\]]*?)\](?P<title>[^\[\]]+?)(?: - (?P<episode_num>[0-9-]+)\s*|\[第?(?P<episode>[0-9]+(?:-[0-9]+)?)话?(?:END|完)?\])\[', re.IGNORECASE),
            "[${subgroup}][${title}][${episode}]["),

            # Additional Chinese patterns from C# - FIXED Python named group syntax
            (re.compile(r'^\[(?P<subgroup>[^\]]+)\](?:(?P<chinesubgroup>\[(?=[^\]]*?[\u4E00-\u9FCC])[^\]]*\])+)\[(?P<title>[^\]]+?)\](?P<junk>\[[^\]]+\])*\[(?P<episode>[0-9]+(?:-[0-9]+)?)( END| Fin)?\]', re.IGNORECASE),
            "[${subgroup}] ${title} - ${episode} "),

            # Spanish releases with information in brackets - FIXED Python named group syntax
            (re.compile(r'^(?P<title>.+?(?=[ ._-]\()).+?\((?P<year>\d{4})\/(?P<info>S[^\/]+)', re.IGNORECASE),
            "${title} (${year}) - ${info} "),
        ]

    def _compile_reject_hashed_regexes(self):
        """Compile regex patterns to reject hashed releases"""
        return [
            re.compile(r'^[0-9a-zA-Z]{32}', re.IGNORECASE),
            re.compile(r'^[a-z0-9]{24}$', re.IGNORECASE),
            re.compile(r'^[A-Z]{11}\d{3}$', re.IGNORECASE),
            re.compile(r'^[a-z]{12}\d{3}$', re.IGNORECASE),
            re.compile(r'^Backup_\d{5,}S\d{2}-\d{2}$', re.IGNORECASE),
            re.compile(r'^123$', re.IGNORECASE),
            re.compile(r'^abc$', re.IGNORECASE),
            re.compile(r'^abc[-_. ]xyz', re.IGNORECASE),
            re.compile(r'^b00bs$', re.IGNORECASE),
            re.compile(r'^\d{6}_\d{2}$', re.IGNORECASE),
            re.compile(r'^[0-9a-zA-Z]{30}', re.IGNORECASE),
            re.compile(r'^[0-9a-zA-Z]{26}', re.IGNORECASE),
            re.compile(r'^[0-9a-zA-Z]{39}', re.IGNORECASE),
            re.compile(r'^[0-9a-zA-Z]{24}', re.IGNORECASE),
            re.compile(r'^Season[ ._-]*\d+$', re.IGNORECASE),
            re.compile(r'^Specials$', re.IGNORECASE),
        ]

    def _compile_anime_patterns(self):
        """Compile anime-specific patterns"""
        return [
            # Anime absolute episode patterns
            (re.compile(r'^(?:\[(?P<subgroup>.+?)\](?:_|-|\s|\.)?)(?P<title>.+?)[-_. ]+(?P<absoluteepisode>\d{2,3}(\.\d{1,2})?(?!\d+))(?:[-_. ])+\((?:S(?P<season>\d{1,2}(?!\d+))(?:(?:[ex]|\W[ex]){1,2}(?P<episode>\d{2}(?!\d+))))(?:v\d+)?(?:\)(?!\d+)).*?(?P<hash>[(\[]\w{8}[)\]])?$', re.IGNORECASE), None),
            (re.compile(r'^(?:\[(?P<subgroup>.+?)\](?:_|-|\s|\.)?)(?P<title>.+?)[-_. ]+(?P<absoluteepisode>\d{2,3}(\.\d{1,2})?(?!\d+))(?:[-_. ](?<![()\[!]))+(?:S(?P<season>\d{1,2}(?!\d+))(?:(?:[ex]|\W[ex]){1,2}(?P<episode>\d{2}(?!\d+))))(?:v\d+)?(?:[_. ](?!\d+)).*?(?P<hash>[(\[]\w{8}[)\]])?$', re.IGNORECASE), None),
            (re.compile(r'^(?:\[(?P<subgroup>.+?)\](?:_|-|\s|\.)?)(?P<title>.+?)(?:[-_\W](?<![()\[!]))+(?:S?(?P<season>\d{1,2}(?!\d+))(?:(?:[ex]|\W[ex]){1,2}(?P<episode>\d{2}(?!\d+)))+)(?:v\d+)?(?:[_. ](?!\d+)).*?(?P<hash>[(\[]\w{8}[)\]])?$', re.IGNORECASE), None),
            (re.compile(r'^(?:\[(?P<subgroup>.+?)\][-_. ]?)(?P<title>.+?)[-_. ]+?(?:Episode)(?:[-_. ]+(?P<absoluteepisode>\d{2,3}(\.\d{1,2})?(?!\d+)))+.*?(?P<hash>[(\[]\w{8}[)\]])?$', re.IGNORECASE), None),
            # Fixed: Removed problematic lookbehind with alternation
            (re.compile(r'^\[(?P<subgroup>.+?)\][-_. ]?(?P<title>[^-]+?)(?: - )[-_. ]?(?P<absoluteepisode1>\d{2,3}(\.\d{1,2})?(?!\d+))\s?~\s?(?P<absoluteepisode2>\d{2,3}(\.\d{1,2})?(?!\d+))(?:[-_. ]+(?P<special>special|ova|ovd))?.*?(?P<hash>[(\[]\w{8}[)\]])?(?:$|\.mkv)', re.IGNORECASE), None),
        ]

    def _compile_special_episode_patterns(self):
        """Compile special episode patterns"""
        return [
            # Fixed: Changed (?<episodetitle> to (?P<episodetitle>
            (re.compile(r'\.S\d+E00\.(?P<episodetitle>.+?)(?:\.(?:720p|1080p|2160p|HDTV|WEB|WEBRip|WEB-DL)\.|$)', re.IGNORECASE), None),
            (re.compile(r'\.S\d+\.Special\.(?P<episodetitle>.+?)(?:\.(?:720p|1080p|2160p|HDTV|WEB|WEBRip|WEB-DL)\.|$)', re.IGNORECASE), None),
            (re.compile(r'\b(?:special|ova|ovd|oav|bonus|extra|speciale)\b', re.IGNORECASE), None),
        ]

    def _pre_process_title(self, title: str) -> str:
        """Apply pre-processing substitutions to title"""
        processed_title = title

        for regex, replacement in self.pre_substitution_regexes:
            if replacement:
                processed_title = regex.sub(replacement, processed_title)

        return processed_title

    def _is_valid_title(self, title: str) -> bool:
        """Check if title is valid for parsing (not hashed release)"""
        if 'password' in title.lower() and 'yenc' in title.lower():
            return False

        if not any(c.isalnum() for c in title):
            return False

        # Remove file extension for checking
        title_without_ext = re.sub(r'\.[a-z0-9]{2,4}$', '', title, flags=re.IGNORECASE)

        # Check against reject patterns
        for reject_regex in self.reject_hashed_regexes:
            if reject_regex.match(title_without_ext):
                logger.debug(f"Rejected hashed release title: {title}")
                return False

        return True

    def _normalize_title(self, title: str) -> str:
        """Enhanced normalization based on Sonarr's parsing logic"""
        if not self._is_valid_title(title):
            return title

        # Apply pre-processing
        normalized_title = self._pre_process_title(title)

        # Convert en dash to regular dash for consistency
        normalized_title = normalized_title.replace('–', '-')
        normalized_title = normalized_title.replace('【', '[').replace('】', ']')

        preserved_patterns = [
            r'\d+\.?\d*[GMK]B',  # File sizes
            r'\d+\.\d+',         # Audio codecs like 5.1
            r'WEB[-.]DL', r'HD[-.]Rip', r'BD[-.]Rip', r'DVD[-.]Rip', r'WEB[-.]Rip',
            r'HDTV', r'BluRay', r'Blu[-.]Ray', r'Telecine', r'TS', r'TC',
            r'DDP\d+\.?\d*', r'AAC\d*\.?\d*', r'AC\d+\.?\d*', r'DD\d*\.?\d*',
            r'EAC\d*', r'DTS', r'TrueHD', r'Atmos', r'MP\d+',
            r'HEVC', r'AVC', r'AV1', r'XviD', r'DivX',
            r'x\d+', r'H\d+', r'H\.\d+',
            r'\d+p', r'\d+i', r'\d+x\d+',  # Resolutions
            r'\[[^]]+\]',                   # Keep bracket content (for groups/tags)
            r'\(\s*(?:19|20)\d{2}\s*\)',   # Only preserve years in parentheses: (2019)
            r'S\d+E\d+', r'S\d+', r'Season\s+\d+',  # Season/episode patterns
            r'\b(?:19|20)\d{2}\b',  # Years (without parentheses)
            r'\b(?:19|20)\d{2}-(?:19|20)\d{2}\b',  # Year ranges: 1951-1957
            r'\b(?:special|ova|ovd|oav|bonus|extra)\b',  # Special episodes
            r'\b(?:part|pt)\s*\d+\b',  # Part indicators
            r'\b(?:multi|dual)\b',  # Language indicators
        ]

        placeholder_map = {}
        for i, pattern in enumerate(preserved_patterns):
            matches = re.finditer(pattern, normalized_title, re.IGNORECASE)
            for match in matches:
                placeholder = f'__PRESERVED_{i}_{len(placeholder_map)}__'
                normalized_title = normalized_title.replace(match.group(), placeholder)
                placeholder_map[placeholder] = match.group()

        # Replace other punctuation with spaces
        normalized_title = re.sub(r'[^\w\s-]', ' ', normalized_title)
        normalized_title = re.sub(r'\s+', ' ', normalized_title).strip()

        # Restore preserved patterns
        for placeholder, original in placeholder_map.items():
            normalized_title = normalized_title.replace(placeholder, original)

        return normalized_title

    def _compile_season_patterns(self) -> List[Tuple[str, re.Pattern]]:
        """Enhanced season patterns based on Sonarr's parsing"""
        patterns = [
            # Complete season patterns
            ("Complete Season", re.compile(r'complete\s+season', re.IGNORECASE)),
            ("Complete Seasons", re.compile(r'complete\s+seasons', re.IGNORECASE)),
            ("Full Season", re.compile(r'full\s+season', re.IGNORECASE)),
            ("Season Pack", re.compile(r'season\s+pack', re.IGNORECASE)),
            ("All Seasons", re.compile(r'all\s+seasons', re.IGNORECASE)),
            ("All Season", re.compile(r'all\s+season', re.IGNORECASE)),

              # Season number patterns - ENHANCED WITH HYPHEN SUPPORT
            ("Season #", re.compile(r'season[-_. ]+(\d+)', re.IGNORECASE)),  # Changed from \s to [-_. ]
            ("Season ##", re.compile(r'season[-_. ]+(\d{2})', re.IGNORECASE)),
            ("Season #-#", re.compile(r'season[-_. ]+(\d+)-(\d+)', re.IGNORECASE)),
            ("Season ##-##", re.compile(r'season[-_. ]+(\d{2})-(\d{2})', re.IGNORECASE)),
            ("Season #-Season #", re.compile(r'season[-_. ]+(\d+)\s*-\s*season[-_. ]+(\d+)', re.IGNORECASE)),
            ("Season ##-Season ##", re.compile(r'season[-_. ]+(\d{2})\s*-\s*season[-_. ]+(\d{2})', re.IGNORECASE)),

            # Short season patterns
            ("S#", re.compile(r's(\d)\b', re.IGNORECASE)),
            ("S##", re.compile(r's(\d{2})', re.IGNORECASE)),
            ("S#-#", re.compile(r's(\d)-(\d)', re.IGNORECASE)),
            ("S##-##", re.compile(r's(\d{2})-(\d{2})', re.IGNORECASE)),
            ("S#-S#", re.compile(r's(\d)\s*-\s*s(\d)', re.IGNORECASE)),
            ("S##-S##", re.compile(r's(\d{2})\s*-\s*s(\d{2})', re.IGNORECASE)),
            ("S#", re.compile(r's(\d+)(?![a-z0-9\-])', re.IGNORECASE)),
            ("S#xE#", re.compile(r's(\d+)x[e]?(\d+)', re.IGNORECASE)),
            ("S#xE#-#", re.compile(r's(\d+)x[e]?(\d+)-(\d+)', re.IGNORECASE)),

            # Multi-language season patterns
            ("Stagione #", re.compile(r'stagione\s+(\d+)', re.IGNORECASE)),
            ("Stagioni #-#", re.compile(r'stagioni\s+(\d+)-(\d+)', re.IGNORECASE)),
            ("Temporada #", re.compile(r'temporada\s+(\d+)', re.IGNORECASE)),
            ("Temporadas #-#", re.compile(r'temporadas\s+(\d+)-(\d+)', re.IGNORECASE)),
            ("Saison #", re.compile(r'saison\s+(\d+)', re.IGNORECASE)),

            # Complete short season patterns
            ("Complete S#", re.compile(r'complete\s+s(\d)', re.IGNORECASE)),
            ("Complete S##", re.compile(r'complete\s+s(\d{2})', re.IGNORECASE)),
            ("Complete S#-S#", re.compile(r'complete\s+s(\d)\s*-\s*s(\d)', re.IGNORECASE)),
            ("Complete S##-S##", re.compile(r'complete\s+s(\d{2})\s*-\s*s(\d{2})', re.IGNORECASE)),

            # Season with complete
            ("Season # Complete", re.compile(r'season\s+(\d+)\s+complete', re.IGNORECASE)),
            ("Season ## Complete", re.compile(r'season\s+(\d{2})\s+complete', re.IGNORECASE)),
            ("S# Complete", re.compile(r's(\d)\s+complete', re.IGNORECASE)),
            ("S## Complete", re.compile(r's(\d{2})\s+complete', re.IGNORECASE)),

            # Full short season
            ("Full S#", re.compile(r'full\s+s(\d)', re.IGNORECASE)),
            ("Full S##", re.compile(r'full\s+s(\d{2})', re.IGNORECASE)),

            # 4-digit season numbers
            ("S####", re.compile(r's(\d{4})', re.IGNORECASE)),

            # Season only with year
            ("Season # (####)", re.compile(r'season\s+(\d+)\s+\(\d{4}\)', re.IGNORECASE)),

            # Partial season packs
            ("Season # Part #", re.compile(r'season\s+(\d+)\s+part\s+(\d+)', re.IGNORECASE)),
            ("S# Part #", re.compile(r's(\d)\s+part\s+(\d+)', re.IGNORECASE)),
            ("Season # Vol #", re.compile(r'season\s+(\d+)\s+vol\s+(\d+)', re.IGNORECASE)),

            # Season ranges with "to"
            ("Season # to #", re.compile(r'season\s+(\d+)\s+to\s+(\d+)', re.IGNORECASE)),
            ("S# to #", re.compile(r's(\d+)\s+to\s+(\d+)', re.IGNORECASE)),

            # Multi-season patterns
            ("Season list", re.compile(r'season\s+((?:\d+\s*[, &]\s*)+\d+)', re.IGNORECASE)),
            ("S list", re.compile(r's((?:\d+\s*[, &]\s*)+\d+)', re.IGNORECASE)),
            ("S+S+S list", re.compile(r'\b((?:s(?:eason)?\s*\d+\s*[\.\-_,+ ]?\s*){2,})\b', re.IGNORECASE)),

            # Roman numeral seasons
            ("Season Roman", re.compile(r'season\s+([IVXLCDM]+)', re.IGNORECASE)),
            ("S Roman", re.compile(r's([IVXLCDM]+)', re.IGNORECASE)),

            # 3-digit season numbers
            ("S###", re.compile(r's(\d{3})', re.IGNORECASE)),
        ]
        return patterns

    def _compile_episode_patterns(self) -> List[Tuple[str, re.Pattern]]:
        """Enhanced episode patterns based on Sonarr's parsing"""
        patterns = [
            # Standard episode patterns
            ("EP #", re.compile(r'ep\s+(\d+)', re.IGNORECASE)),
            ("EP ##", re.compile(r'ep\s+(\d{2})', re.IGNORECASE)),
            ("EP #-#", re.compile(r'ep\s+(\d+)-(\d+)', re.IGNORECASE)),
            ("EP ##-##", re.compile(r'ep\s+(\d{2})\s*-\s*(\d{2})', re.IGNORECASE)),
            ("EP (##)", re.compile(r'ep\s*\((\d{2})\)', re.IGNORECASE)),
            ("EP (##-##)", re.compile(r'ep\s*\((\d{2})-(\d{2})\)', re.IGNORECASE)),

            # Short episode patterns
            ("EP#", re.compile(r'ep(\d+)', re.IGNORECASE)),
            ("EP##", re.compile(r'ep(\d{2})', re.IGNORECASE)),
            ("EP#-#", re.compile(r'ep(\d+)-(\d+)', re.IGNORECASE)),
            ("EP##-##", re.compile(r'ep(\d{2})-(\d{2})', re.IGNORECASE)),

            # Very short episode patterns
            ("E#", re.compile(r'e(\d)\b', re.IGNORECASE)),
            ("E##", re.compile(r'e(\d{2})', re.IGNORECASE)),
            ("E#-#", re.compile(r'e(\d)-(\d)', re.IGNORECASE)),
            ("E##-##", re.compile(r'e(\d{2})-(\d{2})', re.IGNORECASE)),
            ("E#E#", re.compile(r'e(\d)e(\d)', re.IGNORECASE)),
            ("E##E##", re.compile(r'e(\d{2})e(\d{2})', re.IGNORECASE)),
            ("S#xE#", re.compile(r's(\d+)x[e]?(\d+)', re.IGNORECASE)),

            # Multi-digit episode patterns
            ("E#-#", re.compile(r'e(\d+)-(\d+)', re.IGNORECASE)),
            ("E#-#", re.compile(r'(?<!x)e(\d+)-(\d+)', re.IGNORECASE)),
            ("E##-##", re.compile(r'e(\d{2})-(\d{2})', re.IGNORECASE)),

            # Full word episode patterns
            ("Episode #", re.compile(r'episode\s+(\d+)', re.IGNORECASE)),
            ("Episode ##", re.compile(r'episode\s+(\d{2})', re.IGNORECASE)),
            ("Episode #-#", re.compile(r'episode\s+(\d+)-(\d+)', re.IGNORECASE)),
            ("Episode # - #", re.compile(r'episode\s+(\d+)\s*-\s*(\d+)', re.IGNORECASE)),
            ("Episode ## - ##", re.compile(r'episode\s+(\d{2})\s*-\s*(\d{2})', re.IGNORECASE)),
            ("Episode ##-##", re.compile(r'episode\s+(\d{2})-(\d{2})', re.IGNORECASE)),

            # Multi-episode patterns
            ("Episodes # - #", re.compile(r'episodes\s+(\d+)\s*-\s*(\d+)', re.IGNORECASE)),
            ("Episodes ## - ##", re.compile(r'episodes\s+(\d{2})\s*-\s*(\d{2})', re.IGNORECASE)),
            ("Episodes #-#", re.compile(r'episodes\s+(\d+)-(\d+)', re.IGNORECASE)),
            ("Episodes ##-##", re.compile(r'episodes\s+(\d{2})-(\d{2})', re.IGNORECASE)),
            ("Episodes # to #", re.compile(r'episodes\s+(\d+)\s+to\s+(\d+)', re.IGNORECASE)),
            ("Episodes ## to ##", re.compile(r'episodes\s+(\d{2})\s+to\s+(\d{2})', re.IGNORECASE)),

            # Short multi-episode patterns
            ("Ep # to #", re.compile(r'ep\s+(\d+)\s+to\s+(\d+)', re.IGNORECASE)),
            ("Ep ## to ##", re.compile(r'ep\s+(\d{2})\s+to\s+(\d{2})', re.IGNORECASE)),
            ("E# to E#", re.compile(r'e(\d)\s+to\s+e(\d)', re.IGNORECASE)),
            ("E## to E##", re.compile(r'e(\d{2})\s+to\s+e(\d{2})', re.IGNORECASE)),

            # Special episode types - FIXED PATTERN
            ("Complete Episodes", re.compile(r'complete[-_. ]+episodes', re.IGNORECASE)),
            ("All Episodes", re.compile(r'all[-_. ]+episodes', re.IGNORECASE)),  # Changed from \s to [-_. ]
            ("Full Episode", re.compile(r'full[-_. ]+episode', re.IGNORECASE)),
            ("All Episode", re.compile(r'all[-_. ]+episode', re.IGNORECASE)),
            ("Special Episode", re.compile(r'special[-_. ]+episode', re.IGNORECASE)),
            ("Bonus Episode", re.compile(r'bonus[-_. ]+episode', re.IGNORECASE)),
            ("Pilot Episode", re.compile(r'pilot[-_. ]+episode', re.IGNORECASE)),
            ("Final Episode", re.compile(r'final[-_. ]+episode', re.IGNORECASE)),
            ("Premiere Episode", re.compile(r'premiere[-_. ]+episode', re.IGNORECASE)),
            ("Season Finale", re.compile(r'season[-_. ]+finale', re.IGNORECASE)),
            ("Series Finale", re.compile(r'series[-_. ]+finale', re.IGNORECASE)),

            # Part patterns
            ("Part #", re.compile(r'part\s+(\d+)', re.IGNORECASE)),
            ("Part ##", re.compile(r'part\s+(\d{2})', re.IGNORECASE)),
            ("Part # & #", re.compile(r'part\s+(\d+)\s*&\s*(\d+)', re.IGNORECASE)),
            ("Part ## & ##", re.compile(r'part\s+(\d{2})\s*&\s*(\d{2})', re.IGNORECASE)),

            # Chapter patterns
            ("Chapters #-#", re.compile(r'chapters\s+(\d+)-(\d+)', re.IGNORECASE)),
            ("Chapters ##-##", re.compile(r'chapters\s+(\d{2})-(\d{2})', re.IGNORECASE)),

            # Anime absolute episode patterns
            ("Absolute ##", re.compile(r'\b(\d{2,3})\b(?!\s*(?:p|i|gb|mb|kbps|Mbps))', re.IGNORECASE)),
            ("Absolute ###", re.compile(r'\b(\d{3,4})\b(?!\s*(?:p|i|gb|mb|kbps|Mbps))', re.IGNORECASE)),

            # Daily episode patterns
            ("YYYY-MM-DD", re.compile(r'(19|20)\d{2}[-_. ](0[1-9]|1[0-2])[-_. ](0[1-9]|[12][0-9]|3[01])\b', re.IGNORECASE)),
            ("YYYY.MM.DD", re.compile(r'(19|20)\d{2}\.(0[1-9]|1[0-2])\.(0[1-9]|[12][0-9]|3[01])\b', re.IGNORECASE)),
            ("DD-MM-YYYY", re.compile(r'(0[1-9]|[12][0-9]|3[01])[-_. ](0[1-9]|1[0-2])[-_. ](19|20)\d{2}\b', re.IGNORECASE)),
            ("MM-DD-YYYY", re.compile(r'(0[1-9]|1[0-2])[-_. ](0[1-9]|[12][0-9]|3[01])[-_. ](19|20)\d{2}\b', re.IGNORECASE)),
            ("YYYYMMDD", re.compile(r'(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])\b', re.IGNORECASE)),

            # 3-digit episode numbers
            ("E###", re.compile(r'e(\d{3})', re.IGNORECASE)),
            ("EP###", re.compile(r'ep(\d{3})', re.IGNORECASE)),

            # Number Episodes
            ("## episodes", re.compile(r'\b(\d{1,3})\s+episodes\b', re.IGNORECASE)),

            # Split episodes
            ("Split E#", re.compile(r'e(\d+)([a-d])', re.IGNORECASE)),

            # Mini-series patterns
            ("Part One", re.compile(r'part\s+(one|two|three|four|five|six|seven|eight|nine)', re.IGNORECASE)),
            ("XofY", re.compile(r'(\d+)\s*of\s*\d+', re.IGNORECASE)),

            # 4-digit episode numbers
            ("E####", re.compile(r'e(\d{4})', re.IGNORECASE)),
            ("EP####", re.compile(r'ep(\d{4})', re.IGNORECASE)),

            # Turkish episode patterns
            ("Bolum #", re.compile(r'bolum\s+(\d+)', re.IGNORECASE)),
            ("BLM #", re.compile(r'blm\s+(\d+)', re.IGNORECASE)),

            # Single digit episodes
            ("Single E#", re.compile(r'(?<![\dx])(?:e|ep)(\d{1})(?!\d)', re.IGNORECASE)),
        ]
        return patterns

    def parse_episode(self, title: str) -> Optional[str]:
        """Enhanced episode parsing with better exclusion logic"""
        normalized_title = self._normalize_title(title)
        episode_matches = []

        # Extract potential false positives to exclude
        years = re.findall(r'\b(19|20)\d{2}\b', normalized_title)
        resolutions = re.findall(r'\b(360|480|720|1080|1440|2160|4K)p?\b', normalized_title, re.IGNORECASE)
        file_sizes = re.findall(r'\b\d+\.?\d*[GMK]B\b', normalized_title, re.IGNORECASE)
        video_codecs = re.findall(r'\b(HEVC|AVC|AV1|XviD|DivX|VP9|h264|h265)\b', normalized_title, re.IGNORECASE)

        exclude_numbers = set()
        exclude_numbers.update(years)
        exclude_numbers.update(resolutions)

        for size in file_sizes:
            num_match = re.search(r'(\d+\.?\d*)', size)
            if num_match:
                exclude_numbers.add(num_match.group(1))

        for codec in video_codecs:
            num_match = re.search(r'(\d+)', codec)
            if num_match:
                exclude_numbers.add(num_match.group(1))

        # Check for special episodes first
        for pattern_name, pattern in self.special_episode_patterns:
            if pattern and pattern.search(normalized_title):
                episode_matches.append("Special")

        # FIRST: Check for "All Episodes" and similar complete season patterns
        complete_patterns = [
            "Complete Episodes", "All Episodes", "Full Episode", "All Episode",
            "Special Episode", "Bonus Episode", "Pilot Episode", "Final Episode",
            "Premiere Episode", "Season Finale", "Series Finale"
        ]

        found_complete_pattern = False
        for pattern_name, pattern in self.episode_patterns:
            if pattern_name in complete_patterns:
                if pattern.search(normalized_title):
                    episode_matches.append(pattern_name)
                    found_complete_pattern = True

        # If we found a complete pattern, skip individual episode parsing
        if found_complete_pattern:
            return ", ".join(episode_matches) if episode_matches else None

        # SECOND: Parse individual episodes only if no complete pattern was found
        for pattern_name, pattern in self.episode_patterns:
            # Skip complete patterns since we already checked them
            if pattern_name in complete_patterns:
                continue

            matches = pattern.finditer(normalized_title)
            for match in matches:
                if pattern_name == "## episodes":
                    episode_count = match.group(1)
                    if episode_count not in exclude_numbers and episode_count.isdigit():
                        count = int(episode_count)
                        if 1 <= count <= 200:
                            episode_matches.append(f"E1-E{count}")
                elif pattern_name == "Split E#":
                    episode_num = match.group(1)
                    split_char = match.group(2)
                    if episode_num not in exclude_numbers:
                        episode_matches.append(f"E{episode_num}{split_char}")
                elif pattern_name == "Part One":
                    part_name = match.group(1).lower()
                    part_map = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                            "six": 6, "seven": 7, "eight": 8, "nine": 9}
                    if part_name in part_map:
                        episode_matches.append(f"Part{part_map[part_name]}")
                elif pattern_name == "XofY":
                    episode_num = match.group(1)
                    if episode_num not in exclude_numbers:
                        episode_matches.append(f"E{episode_num}")
                elif len(match.groups()) == 1:
                    episode_num = match.group(1)
                    if episode_num not in exclude_numbers and episode_num.isdigit():
                        if int(episode_num) <= 200:
                            episode_matches.append(f"E{episode_num.zfill(2)}")
                elif len(match.groups()) == 2:
                    ep1, ep2 = match.group(1), match.group(2)
                    if ep1 not in exclude_numbers and ep2 not in exclude_numbers:
                        if ep1.isdigit() and ep2.isdigit() and int(ep1) <= 200 and int(ep2) <= 200:
                            episode_matches.append(f"E{ep1.zfill(2)}-E{ep2.zfill(2)}")
                elif len(match.groups()) == 3:
                    ep1, ep2 = match.group(2), match.group(3)
                    if ep1 not in exclude_numbers and ep2 not in exclude_numbers:
                        if ep1.isdigit() and ep2.isdigit() and int(ep1) <= 200 and int(ep2) <= 200:
                            episode_matches.append(f"E{ep1.zfill(2)}-E{ep2.zfill(2)}")
                elif pattern_name.startswith("Absolute"):
                    abs_num = match.group(1)
                    if abs_num not in exclude_numbers and abs_num.isdigit() and int(abs_num) <= 2000:
                        episode_matches.append(f"Abs{abs_num.zfill(3)}")

        # Check for date-based episodes
        date_patterns = [
            r'(19|20)\d{2}[-_. ](0[1-9]|1[0-2])[-_. ](0[1-9]|[12][0-9]|3[01])',
            r'(0[1-9]|[12][0-9]|3[01])[-_. ](0[1-9]|1[0-2])[-_. ](19|20)\d{2}',
            r'(0[1-9]|1[0-2])[-_. ](0[1-9]|[12][0-9]|3[01])[-_. ](19|20)\d{2}',
        ]

        for date_pattern in date_patterns:
            date_matches = re.findall(date_pattern, normalized_title, re.IGNORECASE)
            for match in date_matches:
                if len(match) == 3:
                    episode_matches.append(f"Date:{match[0]}-{match[1]}-{match[2]}")

        return ", ".join(episode_matches) if episode_matches else None

    def parse_season(self, title: str) -> Optional[str]:
        """Enhanced season parsing with better exclusion logic"""
        normalized_title = self._normalize_title(title)
        season_matches = []

        # Extract potential years to exclude from season parsing
        years = re.findall(r'\b(19|20)\d{2}\b', normalized_title)
        resolutions = re.findall(r'\b(360|480|720|1080|1440|2160|4K)p?\b', normalized_title, re.IGNORECASE)

        exclude_numbers = set(years)
        exclude_numbers.update(resolutions)

        # First pass: check for complex patterns
        complex_pattern_ranges = []
        for pattern_name, pattern in self.season_patterns:
            if pattern_name in ["S+S+S list", "Season list", "S list"]:
                matches = pattern.finditer(normalized_title)
                for match in matches:
                    complex_pattern_ranges.append((match.start(), match.end()))

        # Second pass: parse all patterns
        for pattern_name, pattern in self.season_patterns:
            matches = pattern.finditer(normalized_title)
            for match in matches:
                # Skip simple patterns if they overlap with complex patterns
                match_start, match_end = match.start(), match.end()
                if (pattern_name not in ["S+S+S list", "Season list", "S list"] and
                    any(start <= match_start < end for start, end in complex_pattern_ranges)):
                    continue

                if pattern_name in ["Complete Season", "Complete Seasons", "Full Season", "Season Pack",
                                "All Seasons", "All Season"]:
                    season_matches.append(pattern_name)

                elif pattern_name in ["Season list", "S list"]:
                    season_text = match.group(1)
                    season_numbers = re.findall(r'\d+', season_text)
                    season_numbers = [int(num) for num in season_numbers if num not in exclude_numbers]

                    if season_numbers:
                        min_season = min(season_numbers)
                        max_season = max(season_numbers)
                        if 1 <= min_season <= 50 and 1 <= max_season <= 50:
                            season_matches.append(f"S{min_season:02d}-S{max_season:02d}")

                elif pattern_name == "S+S+S list":
                    season_text = match.group(1).lower()
                    season_numbers = re.findall(r's(?:eason)?\s*(\d+)', season_text)
                    season_numbers = [int(num) for num in season_numbers if num not in exclude_numbers]

                    if season_numbers:
                        min_season = min(season_numbers)
                        max_season = max(season_numbers)
                        if 1 <= min_season <= 50 and 1 <= max_season <= 50:
                            if len(season_numbers) > 1:
                                season_matches.append(f"S{min_season:02d}-S{max_season:02d}")
                            else:
                                season_matches.append(f"S{min_season:02d}")

                elif pattern_name in ["Season # to #", "S# to #"]:
                    s1, s2 = int(match.group(1)), int(match.group(2))
                    if str(s1) not in exclude_numbers and str(s2) not in exclude_numbers:
                        if 1 <= s1 <= 50 and 1 <= s2 <= 50:
                            min_season, max_season = min(s1, s2), max(s1, s2)
                            season_matches.append(f"S{min_season:02d}-S{max_season:02d}")

                elif pattern_name == "Season Roman":
                    roman_num = match.group(1)
                    try:
                        season_num = self._roman_to_int(roman_num)
                        if 1 <= season_num <= 50:
                            season_matches.append(f"S{season_num:02d}")
                    except ValueError:
                        pass

                elif pattern_name == "S Roman":
                    roman_num = match.group(1)
                    try:
                        season_num = self._roman_to_int(roman_num)
                        if 1 <= season_num <= 50:
                            season_matches.append(f"S{season_num:02d}")
                    except ValueError:
                        pass

                elif len(match.groups()) == 1:
                    season_num = match.group(1)
                    if season_num not in exclude_numbers:
                        season_matches.append(f"S{season_num.zfill(2)}")

                elif len(match.groups()) == 2:
                    s1, s2 = match.group(1), match.group(2)
                    if s1 not in exclude_numbers and s2 not in exclude_numbers:
                        if int(s1) <= 50 and int(s2) <= 50:
                            season_matches.append(f"S{s1.zfill(2)}-S{s2.zfill(2)}")

        return ", ".join(season_matches) if season_matches else None

    def _roman_to_int(self, s: str) -> int:
        """Convert Roman numeral to integer"""
        roman_map = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
        result = 0
        prev_value = 0

        for char in reversed(s.upper()):
            value = roman_map.get(char, 0)
            if value < prev_value:
                result -= value
            else:
                result += value
            prev_value = value

        return result

    # Enhanced pattern compilation methods
    def _compile_resolution_patterns(self) -> List[Tuple[str, re.Pattern]]:
        return [
            ("###p", re.compile(r'\b(\d{3,4})p\b', re.IGNORECASE)),
            ("###i", re.compile(r'\b(\d{3,4})i\b', re.IGNORECASE)),
            ("####x###", re.compile(r'\b(\d{3,4})x(\d{3,4})\b', re.IGNORECASE)),
            ("4K", re.compile(r'\b4K\b', re.IGNORECASE)),
            ("SD", re.compile(r'\bSD\b', re.IGNORECASE)),
            ("HD", re.compile(r'\bHD\b', re.IGNORECASE)),
            ("FHD", re.compile(r'\bFHD\b', re.IGNORECASE)),
            ("UHD", re.compile(r'\bUHD\b', re.IGNORECASE)),
            ("QHD", re.compile(r'\bQHD\b', re.IGNORECASE)),
            ("WQHD", re.compile(r'\bWQHD\b', re.IGNORECASE)),
            ("RawHD", re.compile(r'\bRaw[-_. ]?HD\b', re.IGNORECASE)),
        ]

    def _compile_video_codec_patterns(self) -> List[Tuple[str, re.Pattern]]:
        return [
            ("x###", re.compile(r'\bx(\d+)\b', re.IGNORECASE)),
            ("H###", re.compile(r'\bH(\d+)\b', re.IGNORECASE)),
            ("H.###", re.compile(r'\bH\.(\d+)\b', re.IGNORECASE)),
            ("HEVC", re.compile(r'\bHEVC\b', re.IGNORECASE)),
            ("AVC", re.compile(r'\bAVC\b', re.IGNORECASE)),
            ("AV1", re.compile(r'\bAV1\b', re.IGNORECASE)),
            ("XviD", re.compile(r'\bXviD\b', re.IGNORECASE)),
            ("DivX", re.compile(r'\bDivX\b', re.IGNORECASE)),
            ("VP9", re.compile(r'\bVP9\b', re.IGNORECASE)),
            ("h264", re.compile(r'\bh264\b', re.IGNORECASE)),
            ("h265", re.compile(r'\bh265\b', re.IGNORECASE)),
            ("MPEG2", re.compile(r'\bMPEG[-_. ]?2\b', re.IGNORECASE)),
            ("VC-1", re.compile(r'\bVC[-_. ]?1\b', re.IGNORECASE)),
        ]

    def _compile_audio_codec_patterns(self) -> List[Tuple[str, re.Pattern]]:
        return [
            ("AAC", re.compile(r'\bAAC\b', re.IGNORECASE)),
            ("AAC#.#", re.compile(r'\bAAC(\d+\.?\d*)\b', re.IGNORECASE)),
            ("DDP#.#", re.compile(r'\bDDP?(\d+\.?\d*)\b', re.IGNORECASE)),
            ("AC#", re.compile(r'\bAC(\d+)\b', re.IGNORECASE)),
            ("AC#.#", re.compile(r'\bAC(\d+\.?\d*)\b', re.IGNORECASE)),
            ("DD#.#", re.compile(r'\bDD(\d+\.?\d*)\b', re.IGNORECASE)),
            ("DD+", re.compile(r'\bDD\+\b', re.IGNORECASE)),
            ("EAC#", re.compile(r'\bEAC(\d+)\b', re.IGNORECASE)),
            ("DTS", re.compile(r'\bDTS\b', re.IGNORECASE)),
            ("DLMux", re.compile(r'\bDLMux\b', re.IGNORECASE)),
            ("DTS-HD", re.compile(r'\bDTS[-.]HD\b', re.IGNORECASE)),
            ("DTS-X", re.compile(r'\bDTS[-.]X\b', re.IGNORECASE)),
            ("TrueHD", re.compile(r'\bTrueHD\b', re.IGNORECASE)),
            ("Atmos", re.compile(r'\bAtmos\b', re.IGNORECASE)),
            ("MP#", re.compile(r'\bMP(\d+)\b', re.IGNORECASE)),
            ("FLAC", re.compile(r'\bFLAC\b', re.IGNORECASE)),
            ("Opus", re.compile(r'\bOpus\b', re.IGNORECASE)),
            ("PCM", re.compile(r'\bPCM\b', re.IGNORECASE)),
            ("5.1", re.compile(r'\b5.1\b', re.IGNORECASE)),
            ("7.1", re.compile(r'\b7.1\b', re.IGNORECASE)),
            ("2.0", re.compile(r'\b2.0\b', re.IGNORECASE)),
            ("Vorbis", re.compile(r'\bVorbis\b', re.IGNORECASE)),
        ]

    def _compile_language_patterns(self) -> List[Tuple[str, re.Pattern]]:
        """Enhanced language patterns based on Sonarr's LanguageParser"""
        return [
            # Language codes (ISO 639-1 and ISO 639-2)
            ("ISO639-1", re.compile(r'\b(?:en|fr|es|de|it|da|nl|ja|is|zh|ru|pl|vi|sv|no|nb|fi|tr|pt|el|ko|hu|he|lt|cs|ar|hi|bg|ml|uk|sk|th|ro|lv|fa|ca|hr|sr|bs|et|ta|id|mk|sl|az|uz|ms|ur|rm)\b', re.IGNORECASE)),
            ("ISO639-2", re.compile(r'\b(?:eng|fra|spa|deu|ita|dan|nld|jpn|isl|zho|rus|pol|vie|swe|nor|nob|fin|tur|por|ell|kor|hun|heb|lit|ces|ara|hin|bul|mal|ukr|slk|tha|ron|lav|fas|cat|hrv|srp|bos|est|tam|tel|kan|ind|mkd|slv|aze|uzb|msa|urd|roh)\b', re.IGNORECASE)),

            # Full language names
            ("LanguageNames", re.compile(r'\b(?:english|french|spanish|german|italian|danish|dutch|japanese|icelandic|chinese|russian|polish|vietnamese|swedish|norwegian|finnish|turkish|portuguese|greek|korean|hungarian|hebrew|lithuanian|czech|arabic|hindi|bulgarian|malayalam|ukrainian|slovak|thai|romanian|latvian|persian|catalan|croatian|serbian|bosnian|estonian|tamil|telugu|kannada|indonesian|macedonian|slovenian|azerbaijani|uzbek|malay|urdu|romansh)\b', re.IGNORECASE)),

            # Language variants and country codes
            ("LanguageVariants", re.compile(r'\b(?:flemish|brazilian|latino|portuguese[-_. ]br|spanish[-_. ]la|spanish[-_. ]latino)\b', re.IGNORECASE)),

            # Language tags
            ("LanguageTags", re.compile(r'\b(?!(?:TGx|YTS|RARBG))(?:(?:VOSTFR|SUB|ESub|MSUBS|DUAL|Multi|MULTI|DUBBED|DUB|TrueFrench|VF|VFF|VFI|VFQ|VOST|VO|OV|OMU|SoftSubs|HardSubs|Subtitled))\b', re.IGNORECASE)),

            # Multi-language indicators
            ("MultiLanguage", re.compile(r'\b(?:DL|ML|DUAL[-_. ]AUDIO|MULTI[-_. ]AUDIO)\b', re.IGNORECASE)),

            # Audio tracks
            ("AudioTracks", re.compile(r'\b(?:2\.0|5\.1|7\.1|DTS[-_. ]?X|Atmos|DD5\.1|AC3|DDP5\.1|AAC5\.1)\b', re.IGNORECASE)),
        ]

    def _compile_filesize_patterns(self) -> List[Tuple[str, re.Pattern]]:
        return [
            ("###MB", re.compile(r'\b(\d+)MB\b', re.IGNORECASE)),
            ("###GB", re.compile(r'\b(\d+)GB\b', re.IGNORECASE)),
            ("###.#GB", re.compile(r'\b(\d+\.\d+)GB\b', re.IGNORECASE)),
            ("###.#MB", re.compile(r'\b(\d+\.\d+)MB\b', re.IGNORECASE)),
            ("###KB", re.compile(r'\b(\d+)KB\b', re.IGNORECASE)),
            ("###TB", re.compile(r'\b(\d+)TB\b', re.IGNORECASE)),
            ("###.#TB", re.compile(r'\b(\d+\.\d+)TB\b', re.IGNORECASE)),
        ]

    def _compile_filetype_patterns(self) -> List[Tuple[str, re.Pattern]]:
        return [
            (".mkv", re.compile(r'\.mkv\b', re.IGNORECASE)),
            (".mp4", re.compile(r'\.mp4\b', re.IGNORECASE)),
            (".avi", re.compile(r'\.avi\b', re.IGNORECASE)),
            (".m4v", re.compile(r'\.m4v\b', re.IGNORECASE)),
            (".mpg", re.compile(r'\.mpg\b', re.IGNORECASE)),
            (".mpeg", re.compile(r'\.mpeg\b', re.IGNORECASE)),
            (".ass", re.compile(r'\.ass\b', re.IGNORECASE)),
            (".ssa", re.compile(r'\.ssa\b', re.IGNORECASE)),
            (".srt", re.compile(r'\.srt\b', re.IGNORECASE)),
            (".sub", re.compile(r'\.sub\b', re.IGNORECASE)),
            (".idx", re.compile(r'\.idx\b', re.IGNORECASE)),
            (".iso", re.compile(r'\.iso\b', re.IGNORECASE)),
            (".ts", re.compile(r'\.ts\b', re.IGNORECASE)),
            (".m2ts", re.compile(r'\.m2ts\b', re.IGNORECASE)),
            (".vob", re.compile(r'\.vob\b', re.IGNORECASE)),
            (".rar", re.compile(r'\.rar\b', re.IGNORECASE)),
            (".zip", re.compile(r'\.zip\b', re.IGNORECASE)),
            (".7z", re.compile(r'\.7z\b', re.IGNORECASE)),
        ]

    def _compile_quality_patterns(self) -> List[Tuple[str, re.Pattern]]:
        """Enhanced quality patterns based on Sonarr's QualityParser"""
        return [
            # Source types
            ("WEB-DL", re.compile(r'\bWEB[-_. ]?DL\b', re.IGNORECASE)),
            ("WEBRip", re.compile(r'\bWEB[-_. ]?Rip\b', re.IGNORECASE)),
            ("HDTV", re.compile(r'\bHDTV\b', re.IGNORECASE)),
            ("BluRay", re.compile(r'\bBlu[-_. ]?Ray\b', re.IGNORECASE)),
            ("BD-Rip", re.compile(r'\bBD[-_. ]?Rip\b', re.IGNORECASE)),
            ("DVD-Rip", re.compile(r'\bDVD[-_. ]?Rip\b', re.IGNORECASE)),
            ("HD-Rip", re.compile(r'\bHD[-_. ]Rip\b', re.IGNORECASE)),
            ("Telecine", re.compile(r'\bTelecine\b', re.IGNORECASE)),
            ("HDTS", re.compile(r'\bHDTS\b', re.IGNORECASE)),
            ("TS", re.compile(r'\bTS\b', re.IGNORECASE)),
            ("TC", re.compile(r'\bTC\b', re.IGNORECASE)),
            ("CAM", re.compile(r'\bCAM\b', re.IGNORECASE)),
            ("R5", re.compile(r'\bR5\b', re.IGNORECASE)),
            ("SCR", re.compile(r'\bSCR\b', re.IGNORECASE)),
            ("DVD", re.compile(r'\bDVD\b', re.IGNORECASE)),
            ("VHS", re.compile(r'\bVHS\b', re.IGNORECASE)),
            ("PDTV", re.compile(r'\bPDTV\b', re.IGNORECASE)),
            ("DSR", re.compile(r'\bDSR\b', re.IGNORECASE)),
            ("TVRip", re.compile(r'\bTV[-_. ]Rip\b', re.IGNORECASE)),
            ("SATRip", re.compile(r'\bSAT[-_. ]Rip\b', re.IGNORECASE)),
            ("DVDR", re.compile(r'\bDVDR\b', re.IGNORECASE)),
            ("MD", re.compile(r'\bMD\b', re.IGNORECASE)),
            ("Remux", re.compile(r'\bRemux\b', re.IGNORECASE)),
            ("RawHD", re.compile(r'\bRaw[-_. ]?HD\b', re.IGNORECASE)),

            # Quality modifiers
            ("Proper", re.compile(r'\bProper\b', re.IGNORECASE)),
            ("Repack", re.compile(r'\bRepack\b', re.IGNORECASE)),
            ("Real", re.compile(r'\bReal\b', re.IGNORECASE)),
            ("Final", re.compile(r'\bFinal\b', re.IGNORECASE)),
            ("Director's Cut", re.compile(r'\bDirector[\'’]s\s+Cut\b', re.IGNORECASE)),
            ("Extended", re.compile(r'\bExtended\b', re.IGNORECASE)),
            ("Uncut", re.compile(r'\bUncut\b', re.IGNORECASE)),
            ("Unrated", re.compile(r'\bUnrated\b', re.IGNORECASE)),
            ("Theatrical", re.compile(r'\bTheatrical\b', re.IGNORECASE)),
            ("Ultimate", re.compile(r'\bUltimate\b', re.IGNORECASE)),
            ("Collector's Edition", re.compile(r'\bCollector[\'’]s\s+Edition\b', re.IGNORECASE)),
        ("Special Edition", re.compile(r'\bSpecial\s+Edition\b', re.IGNORECASE)),
        ("Limited", re.compile(r'\bLimited\b', re.IGNORECASE)),
        ("IMAX", re.compile(r'\bIMAX\b', re.IGNORECASE)),
        ("3D", re.compile(r'\b3D\b', re.IGNORECASE)),
        ("4K Remaster", re.compile(r'\b4K\s+Remaster\b', re.IGNORECASE)),
        ("Remastered", re.compile(r'\bRemastered\b', re.IGNORECASE)),
        ("Restored", re.compile(r'\bRestored\b', re.IGNORECASE)),
        ("Criterion", re.compile(r'\bCriterion\b', re.IGNORECASE)),
        ("Criterion Collection", re.compile(r'\bCriterion\s+Collection\b', re.IGNORECASE)),
        ("Anniversary Edition", re.compile(r'\bAnniversary\s+Edition\b', re.IGNORECASE)),
        ("Version", re.compile(r'\bv(\d+)\b', re.IGNORECASE)),
    ]

    def _compile_year_patterns(self) -> List[Tuple[str, re.Pattern]]:
        return [
            ("(####)", re.compile(r'\((\d{4})\)', re.IGNORECASE)),
            ("####", re.compile(r'\b(\d{4})\b', re.IGNORECASE)),
            ("'##", re.compile(r"'(\d{2})\b", re.IGNORECASE)),
            ("####-####", re.compile(r'\b(\d{4})-(\d{4})\b', re.IGNORECASE)),
            ("(####-####)", re.compile(r'\((\d{4})-(\d{4})\)', re.IGNORECASE)),
        ]

    def _compile_website_patterns(self) -> List[Tuple[str, re.Pattern]]:
        """More specific website patterns"""
        return [
            # Match website prefixes (must have proper domain format)
            ("WebsitePrefix", re.compile(r'^(?:www\.)?([a-z0-9-]{2,}\.(?:com|org|net|ws|info|biz|tv|cc|io|me|us|uk|de|fr|fi|es|it|ru|ca|au|nz|jp|cn|in|br|mx|lv|pro|xyz|site|online|tech|club|fun|store|shop|blog|app|dev|edu|gov|mil)[a-z0-9.-]*)', re.IGNORECASE)),

            # Match website names in parentheses (must have proper TLD)
            ("(WEBSITE)", re.compile(r'\((?:www\.)?([a-z0-9-]{2,}\.(?:com|org|net|info|ws|biz|tv|cc|io|me|us|uk|de|fr|fi|es|it|ru|ca|au|nz|jp|cn|in|br|mx|lv|pro|xyz|site|online|tech|club|fun|store|shop|blog|app|dev|edu|gov|mil)[a-z0-9.-]*)\)', re.IGNORECASE)),

            # Match website names in brackets (must have proper TLD)
            ("[WEBSITE]", re.compile(r'\[(?:www\.)?([a-z0-9-]{2,}\.(?:com|org|net|info|ws|biz|tv|cc|io|me|us|uk|de|fr|fi|es|it|ru|ca|au|nz|jp|cn|in|br|mx|lv|pro|xyz|site|online|tech|club|fun|store|shop|blog|app|dev|edu|gov|mil)[a-z0-9.-]*)\]', re.IGNORECASE)),

            # Match website anywhere (must have proper TLD and not be part of episode patterns)
            ("WebsiteAnywhere", re.compile(r'\b(?:www\.)?([a-z0-9-]{2,}\.(?:com|org|net|info|ws|biz|tv|cc|io|me|us|uk|de|fr|fi|es|it|ru|ca|au|nz|jp|cn|in|br|mx|lv|pro|xyz|site|online|tech|club|fun|store|shop|blog|app|dev|edu|gov|mil)(?:\/[^\s]*)?\b)', re.IGNORECASE)),

            # Known torrent sites (specific sites only)
            ("KnownSites", re.compile(r'\b(?:TamilRockers|kinokopilka|YTS\.MX|RARBG|ETRG|EVO|Tigole|QxR|DDR|CM|TBS|NTb|TLA|FGT|FQM|TrollHD|CtrlHD|EbP|D-Z0N3|decibeL|HDChina|CHD|WiKi|NGB|HDWinG|HDS|HDArea|HDBits|BeyondHD|BLUTONIUM|FraMeSToR|TayTO|TGx|NZBGeek)\b', re.IGNORECASE)),
        ]

    def _compile_encoder_patterns(self) -> List[Tuple[str, re.Pattern]]:
        """More specific encoder patterns based on Sonarr's parsing"""
        return [
            # Match encoder at the end of the title (after quality/resolution)
            ("-ENCODER", re.compile(r'-(?P<encoder>[A-Za-z]{2,})(?=\.[a-z]{2,4}$|$)', re.IGNORECASE)),
            # Match encoder in brackets but not quality terms or years
            ("[ENCODER]", re.compile(r'\[(?!\d+p|\d{4}|WEBRip|WEB-DL|HDTV|BluRay)(?P<encoder>[A-Za-z0-9]{2,})\]', re.IGNORECASE)),
            # Match encoder in parentheses but not quality terms or years
            ("(ENCODER)", re.compile(r'\((?!\d+p|\d{4}|WEBRip|WEB-DL|HDTV|BluRay)(?P<encoder>[A-Za-z0-9]{2,})\)', re.IGNORECASE)),
        ]

    def _compile_group_patterns(self) -> List[Tuple[str, re.Pattern]]:
        """More specific group patterns based on Sonarr's ReleaseGroupParser"""
        return [
            # Match group at the very end (after a dash) - reject pure numbers
            ("-GROUP", re.compile(r'-(?P<group>(?![0-9]+$)[A-Za-z0-9]{2,})(?=\.[a-z]{2,4}$|$)', re.IGNORECASE)),

            # Match group in brackets at the end - reject pure numbers
            ("[GROUP]", re.compile(r'\[(?P<group>(?![0-9]+$)[A-Za-z0-9]{2,})\](?=\.[a-z]{2,4}$|$)', re.IGNORECASE)),

            # Match group in parentheses at the end - reject pure numbers
            ("(GROUP)", re.compile(r'\((?P<group>(?![0-9]+$)[A-Za-z0-9]{2,})\)(?=\.[a-z]{2,4}$|$)', re.IGNORECASE)),

            # Match known group patterns that don't follow the standard
            ("ExceptionGroup", re.compile(r'\b(?:D\-Z0N3|Fight\-BB|VARYG|E\.N\.D|KRaLiMaRKo|BluDragon|DarQ|KCRT|BEN[_. ]THE[_. ]MEN|TAoE|QxR|Joy|ImE|UTR|t3nzin|Anime Time|Project Angel|Hakata Ramen|HONE|Vyndros|SEV|Garshasp|Kappa|Natty|RCVR|SAMPA|YOGI|r00t|EDGE2020)\b', re.IGNORECASE)),

            # Anime subgroup patterns
            ("AnimeSubgroup", re.compile(r'^\[(?P<subgroup>[^\]]+?)\](?:_|-|\s|\.)', re.IGNORECASE)),
        ]

    def parse_resolution(self, title: str) -> Optional[str]:
        """Parse resolution from title"""
        normalized_title = self._normalize_title(title)
        for pattern_name, pattern in self.resolution_patterns:
            match = pattern.search(normalized_title)
            if match:
                if pattern_name == "###p":
                    return f"{match.group(1)}p"
                elif pattern_name == "###i":
                    return f"{match.group(1)}i"
                elif pattern_name == "####x###":
                    return f"{match.group(1)}x{match.group(2)}"
                else:
                    return pattern_name
        return None

    def parse_video_codec(self, title: str) -> Optional[str]:
        """Parse video codec from title"""
        normalized_title = self._normalize_title(title)
        for pattern_name, pattern in self.video_codec_patterns:
            match = pattern.search(normalized_title)
            if match:
                if pattern_name in ["x###", "H###", "H.###"]:
                    return f"{pattern_name[:1]}{match.group(1)}"
                else:
                    return pattern_name
        return None

    def parse_audio_codec(self, title: str) -> Optional[str]:
        """Parse audio codec from title"""
        normalized_title = self._normalize_title(title)
        for pattern_name, pattern in self.audio_codec_patterns:
            match = pattern.search(normalized_title)
            if match:
                if pattern_name in ["AAC#.#", "DDP#.#", "AC#", "AC#.#", "DD#.#", "EAC#", "MP#"]:
                    return f"{pattern_name[:3]}{match.group(1)}"
                else:
                    return pattern_name
        return None

    def parse_language(self, title: str) -> Optional[str]:
        """Parse language from title using Sonarr's logic"""
        normalized_title = self._normalize_title(title)
        languages = []

        # Check for multi-language indicators first
        multi_match = re.search(r'\b(?:DL|ML|DUAL|MULTI)\b', normalized_title, re.IGNORECASE)
        if multi_match:
            languages.append("Multi")

        for pattern_name, pattern in self.language_patterns:
            matches = pattern.finditer(normalized_title)
            for match in matches:
                if pattern_name in ["ISO639-1", "ISO639-2", "LanguageNames", "LanguageVariants"]:
                    language = match.group(0)
                    if self._is_valid_language(language):
                        languages.append(language)
                elif pattern_name == "LanguageTags":
                    tag = match.group(0)
                    if self._is_valid_language_tag(tag):
                        languages.append(tag)

        return ", ".join(sorted(set(languages))) if languages else None

    def _is_valid_language(self, text: str) -> bool:
        """Check if text is a valid language (not a quality term or release group)"""
        text_lower = text.lower()

        # Common non-language terms that might be matched
        invalid_terms = {
            'webrip', 'web-dl', 'webdl', 'hdtv', 'bluray', 'blu-ray', 'remux',
            '5.1', '7.1', '2.0', 'dts', 'atmos', 'ddp', 'aac', 'ac3', 'x264', 'x265',
            'hevc', 'avc', '1080p', '720p', '2160p', '4k', 'repack', 'proper', 'final',
            'extended', 'director', 'cut', 'theatrical', 'unrated', 'uncut', 'limited',
            'dl', 'ml', 'dual', 'multi'
        }

        # Known release groups (should not be treated as languages)
        release_groups = {
            'tgx', 'yts', 'rarbg', 'evo', 'tigole', 'qxr', 'ddr', 'cm', 'tbs', 'ntb',
            'tla', 'fgt', 'fqm', 'trollhd', 'ctrlhd', 'ebp', 'd-z0n3', 'decibel',
            'hdchina', 'chd', 'wiki', 'ngb', 'hdwing', 'hds', 'hdarea', 'hdbits',
            'beyondhd', 'blutonium', 'framestor', 'tayto', 'galaxyrg'
        }

        return (text_lower not in invalid_terms and
                text_lower not in release_groups and
                len(text) >= 2 and
                not text.isdigit())

    def _is_valid_language_tag(self, tag: str) -> bool:
        """Check if a language tag is valid"""
        tag_lower = tag.lower()

        # Valid language tags
        valid_tags = {
            'vostfr', 'sub', 'esub', 'msubs', 'dual', 'multi', 'dubbed', 'dub',
            'truefrench', 'vf', 'vff', 'vfi', 'vfq', 'vost', 'vo', 'ov', 'omu',
            'softsubs', 'hardsubs', 'subtitled'
        }

        return tag_lower in valid_tags

    def parse_filesize(self, title: str) -> Optional[str]:
        """Parse file size from title"""
        normalized_title = self._normalize_title(title)
        for pattern_name, pattern in self.filesize_patterns:
            match = pattern.search(normalized_title)
            if match:
                if pattern_name == "###MB":
                    return f"{match.group(1)}MB"
                elif pattern_name == "###GB":
                    return f"{match.group(1)}GB"
                elif pattern_name == "###.#GB":
                    return f"{match.group(1)}GB"
                elif pattern_name == "###.#MB":
                    return f"{match.group(1)}MB"
                elif pattern_name == "###KB":
                    return f"{match.group(1)}KB"
                elif pattern_name == "###TB":
                    return f"{match.group(1)}TB"
                elif pattern_name == "###.#TB":
                    return f"{match.group(1)}TB"
        return None

    def parse_filetype(self, title: str) -> Optional[str]:
        """Parse file type from title"""
        normalized_title = self._normalize_title(title)
        for pattern_name, pattern in self.filetype_patterns:
            if pattern.search(normalized_title):
                return pattern_name
        return None

    def parse_quality(self, title: str) -> Optional[str]:
        """Parse quality from title"""
        normalized_title = self._normalize_title(title)
        qualities = []

        # Check for quality modifiers first
        quality_modifiers = []
        modifier_patterns = [
            r'\bProper\b', r'\bRepack\b', r'\bReal\b', r'\bFinal\b',
            r'\bExtended\b', r'\bUncut\b', r'\bUnrated\b', r'\bRemastered\b',
            r'\bRestored\b', r'\bDirector\'s Cut\b', r'\bSpecial Edition\b',
            r'\bCollector\'s Edition\b', r'\bAnniversary Edition\b', r'\bLimited\b',
            r'\bIMAX\b', r'\b3D\b', r'\b4K Remaster\b', r'\bCriterion\b',
            r'\bCriterion Collection\b', r'\bUltimate\b', r'\bTheatrical\b'
        ]

        for pattern in modifier_patterns:
            if re.search(pattern, normalized_title, re.IGNORECASE):
                quality_modifiers.append(re.search(pattern, normalized_title, re.IGNORECASE).group(0))

        # Check for version numbers
        version_match = re.search(r'\bv(\d+)\b', normalized_title, re.IGNORECASE)
        if version_match:
            quality_modifiers.append(f"v{version_match.group(1)}")

        # Parse main quality patterns
        for pattern_name, pattern in self.quality_patterns:
            if pattern.search(normalized_title):
                qualities.append(pattern_name)

        # Add modifiers to quality string
        if quality_modifiers:
            qualities.extend(quality_modifiers)

        return ", ".join(qualities) if qualities else None

    def parse_year(self, title: str) -> Optional[str]:
        """Parse year from title"""
        normalized_title = self._normalize_title(title)

        # Check for year ranges first
        year_range_pattern = re.compile(r'\b((19|20)\d{2})-((19|20)\d{2})\b')
        year_range_match = year_range_pattern.search(normalized_title)

        if year_range_match:
            start_year, end_year = year_range_match.group(1), year_range_match.group(3)
            if (1900 <= int(start_year) <= datetime.now().year + 1 and
                1900 <= int(end_year) <= datetime.now().year + 1):
                return f"{start_year}-{end_year}"

        # Then check for single years
        for pattern_name, pattern in self.year_patterns:
            match = pattern.search(normalized_title)
            if match:
                if pattern_name == "(####)":
                    return match.group(1)
                elif pattern_name == "####":
                    year = match.group(1)
                    if 1900 <= int(year) <= datetime.now().year + 1:
                        return year
                elif pattern_name == "'##":
                    year = f"20{match.group(1)}" if int(match.group(1)) < 50 else f"19{match.group(1)}"
                    return year
                elif pattern_name == "####-####":
                    start_year, end_year = match.group(1), match.group(2)
                    if (1900 <= int(start_year) <= datetime.now().year + 1 and
                        1900 <= int(end_year) <= datetime.now().year + 1):
                        return f"{start_year}-{end_year}"

        return None

    def parse_website(self, title: str) -> Optional[str]:
        """Parse website from title using more specific patterns"""
        websites = []
        seen = set()

        for pattern_name, pattern in self.website_patterns:
            matches = pattern.finditer(title)
            for match in matches:
                website = None
                if pattern_name == "WebsitePrefix":
                    website = match.group(1)
                elif pattern_name in ["[WEBSITE]", "(WEBSITE)", "WebsiteAnywhere"]:
                    website = match.group(1)
                elif pattern_name == "KnownSites":
                    website = match.group(0)

                # Add to results if not already seen and not a false positive
                if (website and website not in seen and
                    not self._is_false_positive_website(website)):
                    websites.append(website)
                    seen.add(website)

        return ", ".join(websites) if websites else None

    def _is_false_positive_website(self, website: str) -> bool:
        """Check if a detected website is likely a false positive"""
        website_lower = website.lower()

        # Common false positives
        false_positives = {
            'season', 'episode', 'episodes', 'complete', 'full', 'part',
            'webrip', 'web-dl', 'hdtv', 'bluray', 'blu-ray', 'remux',
            '720p', '1080p', '2160p', '4k', 'repack', 'proper', 'final',
            'extended', 'director', 'cut', 'theatrical', 'unrated', 'uncut',
            'combined', 'surround', 'stereo', 'dolby', 'multi', 'dual'
        }

        # Check if any part of the website matches false positives
        website_parts = website_lower.split('.')
        for part in website_parts:
            if part in false_positives:
                return True

        # Check if website contains common file extensions
        if any(ext in website_lower for ext in ['.mkv', '.mp4', '.avi', '.m4v', '.mpg', '.mpeg', '.srt', '.sub']):
            return True

        # Check if website is too short to be a real domain
        if len(website_lower) < 6:
            return True

        # Check if it looks like a random word with TLD
        if len(website_parts) > 1 and any(len(part) < 3 for part in website_parts[:-1]):
            return True

        return False

    def parse_encoder(self, title: str) -> Optional[str]:
        """Parse encoder from title using more specific patterns"""
        normalized_title = self._normalize_title(title)
        for pattern_name, pattern in self.encoder_patterns:
            match = pattern.search(normalized_title)
            if match:
                # Use named group if available, otherwise group 1
                if 'encoder' in pattern.groupindex:
                    return match.group('encoder')
                else:
                    return match.group(1)
        return None

    def parse_group(self, title: str) -> Optional[str]:
        """Parse release group from title using more specific patterns"""
        normalized_title = self._normalize_title(title)

        # Check for anime subgroups first
        for pattern_name, pattern in self.group_patterns:
            if pattern_name == "AnimeSubgroup":
                match = pattern.match(normalized_title)
                if match:
                    return match.group('subgroup')

        # Check for other group patterns
        for pattern_name, pattern in self.group_patterns:
            if pattern_name != "AnimeSubgroup":
                match = pattern.search(normalized_title)
                if match:
                    # Use named group if available
                    if 'group' in pattern.groupindex:
                        return match.group('group')
                    # For ExceptionGroup pattern (no capture groups), return the entire match
                    elif pattern_name == "ExceptionGroup":
                        return match.group(0)
                    # For other patterns with capture groups
                    elif match.groups():
                        return match.group(1)
        return None

    def parse_anime_info(self, title: str) -> Optional[Dict[str, Any]]:
        """Parse anime-specific information with better exclusion logic"""
        normalized_title = self._normalize_title(title)
        anime_info = {}

        # Extract potential false positives to exclude
        years = re.findall(r'\b(19|20)\d{2}\b', normalized_title)
        resolutions = re.findall(r'\b(360|480|720|1080|1440|2160|4K)p?\b', normalized_title, re.IGNORECASE)
        file_sizes = re.findall(r'\b\d+\.?\d*[GMK]B\b', normalized_title, re.IGNORECASE)
        video_codecs = re.findall(r'\b(HEVC|AVC|AV1|XviD|DivX|VP9|h264|h265)\b', normalized_title, re.IGNORECASE)
        season_numbers = re.findall(r'\bS(\d+)\b', normalized_title, re.IGNORECASE)

        # Also exclude numbers from preserved patterns (like __PRESERVED_30_0__)
        preserved_pattern_numbers = re.findall(r'__PRESERVED_(\d+)_\d+__', normalized_title)

        exclude_numbers = set()
        exclude_numbers.update(years)
        exclude_numbers.update(resolutions)
        exclude_numbers.update(season_numbers)
        exclude_numbers.update(preserved_pattern_numbers)

        for size in file_sizes:
            num_match = re.search(r'(\d+\.?\d*)', size)
            if num_match:
                exclude_numbers.add(num_match.group(1))

        for codec in video_codecs:
            num_match = re.search(r'(\d+)', codec)
            if num_match:
                exclude_numbers.add(num_match.group(1))

        # Additional exclusion: numbers that are part of codec patterns (H.264, x264, etc.)
        codec_numbers = re.findall(r'(?:[Hx]\.?|HEVC|AVC|AV1|h)(\d{2,3})\b', normalized_title, re.IGNORECASE)
        exclude_numbers.update(codec_numbers)

        # Improved absolute episode patterns with better context
        absolute_patterns = [
            # Standalone 2-4 digit numbers that are likely episodes
            r'(?<!\d)(\d{2,4})(?![a-z\d]|p|i|x\d|\.\d)',
            # Absolute episodes in brackets or parentheses (but not codec brackets)
            r'(?<![Hx]\.?)\[(\d{2,4})\]|\((\d{2,4})\)',
            # Absolute episodes with episode indicators
            r'(?:episode|ep|abs|absolute)[-_. ]+?(\d{2,4})',
            # Absolute episodes in anime format (##v# or ###v#)
            r'\b(\d{2,3})v\d\b',
        ]

        absolute_matches = []
        for pattern in absolute_patterns:
            try:
                matches = re.finditer(pattern, normalized_title, re.IGNORECASE)
                for match in matches:
                    # Extract the episode number from different capture groups
                    episode_num = None
                    for i in range(1, len(match.groups()) + 1):
                        if match.group(i) and not episode_num:
                            episode_num = match.group(i)
                            break

                    if episode_num and episode_num not in exclude_numbers:
                        # Additional context validation
                        # Don't capture numbers that are part of season/episode patterns
                        if re.search(rf'S{episode_num}E|E{episode_num}|S\d+E{episode_num}', normalized_title):
                            continue

                        # Don't capture numbers that are immediately after codec indicators
                        if re.search(rf'(?:[Hx]\.?|HEVC|AVC|AV1|h){episode_num}\b', normalized_title, re.IGNORECASE):
                            continue

                        # Additional validation: episode numbers should be reasonable
                        try:
                            episode_int = int(episode_num)
                            if 1 <= episode_int <= 2000:  # Reasonable upper limit for episodes
                                absolute_matches.append(episode_num)
                        except ValueError:
                            continue
            except re.error:
                # Skip patterns that cause regex errors
                continue

        # Remove duplicates while preserving order
        seen = set()
        unique_absolute_matches = []
        for ep in absolute_matches:
            if ep not in seen:
                seen.add(ep)
                unique_absolute_matches.append(ep)

        if unique_absolute_matches:
            anime_info['absolute_episodes'] = unique_absolute_matches

        # Check for special episodes
        special_matches = re.findall(r'\b(?:ova|ovd|oav|special|bonus|extra)\b', normalized_title, re.IGNORECASE)
        if special_matches:
            anime_info['special'] = True

        # Check for batch releases
        if re.search(r'\b\d{2,4}\s*[-~]\s*\d{2,4}\b', normalized_title):
            anime_info['batch'] = True

        return anime_info if anime_info else None

    def parse(self, title: str) -> Dict[str, Any]:
        """Parse all components from torrent title"""
        if not self._is_valid_title(title):
            return {"error": "Invalid title (likely hashed release)"}

        result = {
            "original_title": title,
            "normalized_title": self._normalize_title(title),
            "season": self.parse_season(title),
            "episode": self.parse_episode(title),
            "resolution": self.parse_resolution(title),
            "video_codec": self.parse_video_codec(title),
            "audio_codec": self.parse_audio_codec(title),
            "language": self.parse_language(title),
            "filesize": self.parse_filesize(title),
            "filetype": self.parse_filetype(title),
            "quality": self.parse_quality(title),
            "year": self.parse_year(title),
            "website": self.parse_website(title),
            "encoder": self.parse_encoder(title),
            "group": self.parse_group(title),
            "anime_info": self.parse_anime_info(title),
        }

        # Clean up None values
        result = {k: v for k, v in result.items() if v is not None}

        return result

    def parse_batch(self, titles: List[str]) -> List[Dict[str, Any]]:
        """Parse multiple titles at once"""
        return [self.parse(title) for title in titles]


def post_process_result(result):
    """Post-process the result to deduplicate and keep highest ranges"""
    processed = {
    "INPUT": result.get("original_title", ""),
    "normalized_title": result.get("normalized_title", ""),
    "season": None,
    "episode": None
    }

    # Process season field
    if "season" in result:
        season_value = result["season"]
        if season_value:
            processed["season"] = _process_season_episode_field(season_value)

    # Process episode field
    if "episode" in result:
        episode_value = result["episode"]
        if episode_value:
            processed["episode"] = _process_season_episode_field(episode_value)

    # Add other fields if they exist
    for key, value in result.items():
        if key not in ["INPUT", "normalized_title", "season", "episode", "original_title"]:
            processed[key] = value

    return processed


def _process_season_episode_field(field_value):
    """Process season/episode field to prioritize meaningful ranges"""
    if not field_value:
        return None

    # Split by comma and strip whitespace
    values = [v.strip() for v in field_value.split(",")]

    from collections import Counter
    value_counts = Counter(values)

    # Separate singles and ranges
    singles = []
    ranges = []

    for value in values:
        if '-' in value:
            ranges.append(value)
        else:
            singles.append(value)

    # PRIORITY 1: If we have ranges, pick the one with widest span
    if ranges:
        best_range = None
        max_span = -1

        for range_val in set(ranges):  # Check unique ranges only
            # Calculate the span of this range
            if range_val.count('-') == 1:
                parts = range_val.split('-')
                if len(parts) == 2 and parts[0].startswith('E') and parts[1].startswith('E'):
                    try:
                        start = int(parts[0][1:])  # Extract number after 'E'
                        end = int(parts[1][1:])    # Extract number after 'E'
                        span = end - start

                        # Prefer ranges with meaningful spans (not E01-E01)
                        if span > max_span:
                            max_span = span
                            best_range = range_val
                    except ValueError:
                        continue

        # If we found a range with meaningful span, return it
        if best_range and max_span > 0:
            return best_range

        # If all ranges are zero-span (like E01-E01), fall back to frequency
        return max(set(ranges), key=lambda x: value_counts[x])

    # PRIORITY 2: If no ranges, use most frequent single value
    if singles:
        return max(set(singles), key=lambda x: value_counts[x])

    return None


def main():
    parser = TorrentParser()

    # Test titles covering various patterns
    test_titles = [
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
"[Judas] Saikyou no Shienshoku Wajutsushi de Aru Ore wa Sekai Saikyou Clan wo Shitagaeru (Season 1) (Season 01) [1080p][HEVC x265 10bit][Multi-Subs]",
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
    ]

    # Test with your titles
    results = []
    for i, title in enumerate(test_titles):
        print(f"\n--- Parsing Title {i+1} ---")
        print(f"Original: {title}")
        result = parser.parse(title)
        processed_result = post_process_result(result)

        # Print human-readable
        print("Parsed result:")
        for key, value in processed_result.items():
            if value:  # Only show non-empty values
                print(f"  {key}: {value}")

        # Add to results list for JSON output
        results.append(processed_result)

    # Output as separate JSON objects
    print("\n" + "="*50)
    print("JSON OUTPUT:")
    print("="*50)

    for i, result in enumerate(results):
        print(f"\n--- JSON Output {i+1} ---")
        print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
