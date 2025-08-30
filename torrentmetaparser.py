import re
import json
from typing import Dict, List, Optional, Tuple, Set, Any
from datetime import datetime
import logging

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
        
    def _compile_pre_substitution_regexes(self):
        """Compile regex patterns for pre-processing titles (from ParserCommon.cs)"""
        return [
         # Korean series without season number
         (re.compile(r'\.E(\d{2,4})\.\d{6}\.(.*-NEXT)$', re.IGNORECASE), ".S01E$1.$2"),

         # Chinese anime releases with both English and Chinese titles
         (re.compile(r'^\[(?:(?P<subgroup>[^\]]+?)(?:[\u4E00-\u9FCC]+)?)\]\[(?P<title>[^\]]+?)(?:\s(?P<chinesetitle>[\u4E00-\u9FCC][^\]]*?))\]\[(?:(?:[\u4E00-\u9FCC]+?)?(?P<episode>\d{1,4})(?:[\u4E00-\u9FCC]+?)?)\]', re.IGNORECASE),
         "[${subgroup}] ${title} - ${episode} - "),

         # Chinese LoliHouse/ZERO/Lilith-Raws releases - FIXED: removed duplicate group name
         (re.compile(r'^\[(?P<subgroup>[^\]]*?(?:LoliHouse|ZERO|Lilith-Raws|Skymoon-Raws|orion origin)[^\]]*?)\](?P<title>[^\[\]]+?)(?: - (?P<episode_num>[0-9-]+)\s*|\[第?(?P<episode>[0-9]+(?:-[0-9]+)?)话?(?:END|完)?\])\[', re.IGNORECASE),
         "[${subgroup}][${title}][${episode}][")
        ]
    
    def _compile_reject_hashed_regexes(self):
        """Compile regex patterns to reject hashed releases (from Parser.cs)"""
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
        ]
    
    def _pre_process_title(self, title: str) -> str:
        """Apply pre-processing substitutions to title"""
        processed_title = title
        
        for regex, replacement in self.pre_substitution_regexes:
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

        # FIRST: Convert en dash to regular dash for consistency
        normalized_title = normalized_title.replace('–', '-')

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
        ]

        placeholder_map = {}
        for i, pattern in enumerate(preserved_patterns):
            matches = re.finditer(pattern, normalized_title, re.IGNORECASE)
            for match in matches:
                placeholder = f'__PRESERVED_{i}_{len(placeholder_map)}__'
                normalized_title = normalized_title.replace(match.group(), placeholder)
                placeholder_map[placeholder] = match.group()

        # Replace other punctuation with spaces (more comprehensive)
        # Now en dash is already converted to regular dash, so it won't be replaced
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
            
            # Season number patterns
            ("Season #", re.compile(r'season\s+(\d+)', re.IGNORECASE)),
            ("Season ##", re.compile(r'season\s+(\d{2})', re.IGNORECASE)),
            ("Season #-#", re.compile(r'season\s+(\d+)-(\d+)', re.IGNORECASE)),
            ("Season ##-##", re.compile(r'season\s+(\d{2})-(\d{2})', re.IGNORECASE)),
            ("Season #-Season #", re.compile(r'season\s+(\d+)\s*-\s*season\s+(\d+)', re.IGNORECASE)),
            ("Season ##-Season ##", re.compile(r'season\s+(\d{2})\s*-\s*season\s+(\d{2})', re.IGNORECASE)),
            
            # Short season patterns
            ("S#", re.compile(r's(\d)\b', re.IGNORECASE)),
            ("S##", re.compile(r's(\d{2})', re.IGNORECASE)),
            ("S#-#", re.compile(r's(\d)-(\d)', re.IGNORECASE)),
            ("S##-##", re.compile(r's(\d{2})-(\d{2})', re.IGNORECASE)),
            ("S#-S#", re.compile(r's(\d)\s*-\s*s(\d)', re.IGNORECASE)),
            ("S##-S##", re.compile(r's(\d{2})\s*-\s*s(\d{2})', re.IGNORECASE)),
                    # Keep only the multi-digit version of this pattern:
            ("S#", re.compile(r's(\d+)(?![a-z0-9\-])', re.IGNORECASE)),  # Better negative lookahead
            ("S#xE#", re.compile(r's(\d+)x[e]?(\d+)', re.IGNORECASE)),  # Handles S1xE1, S01xE01, S1xE10
            ("S#xE#-#", re.compile(r's(\d+)x[e]?(\d+)-(\d+)', re.IGNORECASE)),  # Handles S1xE1-10

            
            # Multi-language season patterns
            ("Stagione #", re.compile(r'stagione\s+(\d+)', re.IGNORECASE)),
            ("Stagioni #-#", re.compile(r'stagioni\s+(\d+)-(\d+)', re.IGNORECASE)),
            ("Temporada #", re.compile(r'temporada\s+(\d+)', re.IGNORECASE)),
            ("Temporadas #-#", re.compile(r'temporadas\s+(\d+)-(\d+)', re.IGNORECASE)),
            
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

            ## comma separated season list
            # Add these to your season patterns list:
            #("Season #,#,#", re.compile(r'season\s+(\d+)(?:\s*,\s*(\d+))+', re.IGNORECASE)),
            #("Season # & #", re.compile(r'season\s+(\d+)(?:\s*&\s*(\d+))+', re.IGNORECASE)),
            #("Season # to #", re.compile(r'season\s+(\d+)\s+to\s+(\d+)', re.IGNORECASE)),
            #("S#,#,#", re.compile(r's(\d+)(?:\s*,\s*(\d+))+', re.IGNORECASE)),
            #("S# & #", re.compile(r's(\d+)(?:\s*&\s*(\d+))+', re.IGNORECASE)),
            #("S# to #", re.compile(r's(\d+)\s+to\s+(\d+)', re.IGNORECASE)),
            # Replace the comma-separated patterns with these:
            ("Season list", re.compile(r'season\s+((?:\d+\s*[, &]\s*)+\d+)', re.IGNORECASE)),
            ("S list", re.compile(r's((?:\d+\s*[, &]\s*)+\d+)', re.IGNORECASE)),

            #continues season
            ("S+S+S list", re.compile(r'\b((?:s(?:eason)?\s*\d+\s*[\.\-_,+ ]?\s*){2,})\b', re.IGNORECASE)),

        ]
        return patterns
    
    def _compile_episode_patterns(self) -> List[Tuple[str, re.Pattern]]:
        """Enhanced episode patterns based on Sonarr's parsing"""
        patterns = [
            # Standard episode patterns
            ("EP #", re.compile(r'ep\s+(\d+)', re.IGNORECASE)),
            ("EP ##", re.compile(r'ep\s+(\d{2})', re.IGNORECASE)),
            ("EP #-#", re.compile(r'ep\s+(\d+)-(\d+)', re.IGNORECASE)),
            ("EP ##-##", re.compile(r'ep\s+(\d{2})-(\d{2})', re.IGNORECASE)),
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

            # Replace the single-digit patterns with multi-digit versions:
            ("E#-#", re.compile(r'e(\d+)-(\d+)', re.IGNORECASE)),  # Replaces the old single-digit version
                    # Add negative lookahead to prevent SxEx patterns from being captured as E patterns
            ("E#-#", re.compile(r'(?<!x)e(\d+)-(\d+)', re.IGNORECASE)),  # Negative lookbehind
            ("E##-##", re.compile(r'e(\d{2})-(\d{2})', re.IGNORECASE)),  # Keep this for exact 2-digit matches
            
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
            
            # Special episode types
            ("Complete Episodes", re.compile(r'complete\s+episodes', re.IGNORECASE)),
            ("All Episodes", re.compile(r'all\s+episodes', re.IGNORECASE)),
            ("Full Episode", re.compile(r'full\s+episode', re.IGNORECASE)),
            ("All Episode", re.compile(r'all\s+episode', re.IGNORECASE)),
            ("Special Episode", re.compile(r'special\s+episode', re.IGNORECASE)),
            ("Bonus Episode", re.compile(r'bonus\s+episode', re.IGNORECASE)),
            ("Pilot Episode", re.compile(r'pilot\s+episode', re.IGNORECASE)),
            ("Final Episode", re.compile(r'final\s+episode', re.IGNORECASE)),
            ("Premiere Episode", re.compile(r'premiere\s+episode', re.IGNORECASE)),
            ("Season Finale", re.compile(r'season\s+finale', re.IGNORECASE)),
            ("Series Finale", re.compile(r'series\s+finale', re.IGNORECASE)),
            
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
            
            # Daily episode patterns (from Sonarr)
            ("YYYY-MM-DD", re.compile(r'(19|20)\d{2}[-_. ](0[1-9]|1[0-2])[-_. ](0[1-9]|[12][0-9]|3[01])\b', re.IGNORECASE)),
            ("YYYY.MM.DD", re.compile(r'(19|20)\d{2}\.(0[1-9]|1[0-2])\.(0[1-9]|[12][0-9]|3[01])\b', re.IGNORECASE)),
            ("DD-MM-YYYY", re.compile(r'(0[1-9]|[12][0-9]|3[01])[-_. ](0[1-9]|1[0-2])[-_. ](19|20)\d{2}\b', re.IGNORECASE)),
            ("MM-DD-YYYY", re.compile(r'(0[1-9]|1[0-2])[-_. ](0[1-9]|[12][0-9]|3[01])[-_. ](19|20)\d{2}\b', re.IGNORECASE)),
            
            # 3-digit episode numbers
            ("E###", re.compile(r'e(\d{3})', re.IGNORECASE)),
            ("EP###", re.compile(r'ep(\d{3})', re.IGNORECASE)),

            # Number Episodes
            ("## episodes", re.compile(r'\b(\d{1,3})\s+episodes\b', re.IGNORECASE)),
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

        for pattern_name, pattern in self.episode_patterns:
          matches = pattern.finditer(normalized_title)
          for match in matches:
            if pattern_name in ["Complete Episodes", "All Episodes", "Full Episode", "All Episode",
                              "Special Episode", "Bonus Episode", "Pilot Episode", "Final Episode",
                              "Premiere Episode", "Season Finale", "Series Finale"]:
                episode_matches.append(pattern_name)
            elif pattern_name == "## episodes":  # Handle the new pattern
                episode_count = match.group(1)
                # Check if this number should be excluded
                if episode_count not in exclude_numbers and episode_count.isdigit():
                    count = int(episode_count)
                    if 1 <= count <= 200:  # Reasonable episode limit
                        episode_matches.append(f"E1-E{count}")
            elif len(match.groups()) == 1:
                episode_num = match.group(1)
                # Check if this number should be excluded
                if episode_num not in exclude_numbers:
                    # Additional check: episode numbers should be reasonable
                    if episode_num.isdigit() and int(episode_num) <= 200:
                        episode_matches.append(f"E{episode_num.zfill(2)}")
            elif len(match.groups()) == 2:
                ep1, ep2 = match.group(1), match.group(2)
                # Check if both numbers should be excluded
                if ep1 not in exclude_numbers and ep2 not in exclude_numbers:
                    # Additional check: episode numbers should be reasonable
                    if ep1.isdigit() and ep2.isdigit() and int(ep1) <= 200 and int(ep2) <= 200:
                        episode_matches.append(f"E{ep1.zfill(2)}-E{ep2.zfill(2)}")

            # Add this for 3-group matches (SxEx-# patterns)
            elif len(match.groups()) == 3:
                ep1, ep2 = match.group(2), match.group(3)  # Skip season group (group 1)
                # Check if both numbers should be excluded
                if ep1 not in exclude_numbers and ep2 not in exclude_numbers:
                    # Additional check: episode numbers should be reasonable
                    if ep1.isdigit() and ep2.isdigit() and int(ep1) <= 200 and int(ep2) <= 200:
                        episode_matches.append(f"E{ep1.zfill(2)}-E{ep2.zfill(2)}")

            elif pattern_name.startswith("Absolute"):
                # Handle absolute episode numbers
                abs_num = match.group(1)
                if abs_num not in exclude_numbers and abs_num.isdigit() and int(abs_num) <= 2000:
                    episode_matches.append(f"Abs{abs_num.zfill(3)}")

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

        # First pass: check for complex patterns like s1s2s3
        complex_pattern_ranges = []
        for pattern_name, pattern in self.season_patterns:
            if pattern_name in ["S+S+S list", "Season list", "S list"]:
                matches = pattern.finditer(normalized_title)
                for match in matches:
                    complex_pattern_ranges.append((match.start(), match.end()))  # Store start and end positions

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
                    # Extract all numbers from the comma/ampersand separated list
                    season_text = match.group(1)
                    season_numbers = re.findall(r'\d+', season_text)
                    season_numbers = [int(num) for num in season_numbers if num not in exclude_numbers]

                    if season_numbers:
                        min_season = min(season_numbers)
                        max_season = max(season_numbers)
                        if 1 <= min_season <= 50 and 1 <= max_season <= 50:
                            season_matches.append(f"S{min_season:02d}-S{max_season:02d}")

                elif pattern_name == "S+S+S list":
                    # Handle patterns like s1s2s3, s1-s2-s3, s1_s2_s3, etc.
                    season_text = match.group(1).lower()
                    # Extract all season numbers from the text
                    season_numbers = re.findall(r's(?:eason)?\s*(\d+)', season_text)
                    season_numbers = [int(num) for num in season_numbers if num not in exclude_numbers]

                    if season_numbers:
                        min_season = min(season_numbers)
                        max_season = max(season_numbers)
                        if 1 <= min_season <= 50 and 1 <= max_season <= 50:
                            if len(season_numbers) > 1:
                                # If multiple seasons, create a range
                                season_matches.append(f"S{min_season:02d}-S{max_season:02d}")
                            else:
                                # If only one season, just add it
                                season_matches.append(f"S{min_season:02d}")

                elif pattern_name in ["Season # to #", "S# to #"]:
                    s1, s2 = int(match.group(1)), int(match.group(2))
                    if str(s1) not in exclude_numbers and str(s2) not in exclude_numbers:
                        if 1 <= s1 <= 50 and 1 <= s2 <= 50:
                            min_season, max_season = min(s1, s2), max(s1, s2)
                            season_matches.append(f"S{min_season:02d}-S{max_season:02d}")

                elif len(match.groups()) == 1:
                    season_num = match.group(1)
                    # Check if this number should be excluded (not a year or resolution)
                    if season_num not in exclude_numbers:
                        season_matches.append(f"S{season_num.zfill(2)}")

                elif len(match.groups()) == 2:
                    s1, s2 = match.group(1), match.group(2)
                    # Check if both numbers should be excluded
                    if s1 not in exclude_numbers and s2 not in exclude_numbers:
                        # Additional check: season numbers should be reasonable
                        if int(s1) <= 50 and int(s2) <= 50:
                            season_matches.append(f"S{s1.zfill(2)}-S{s2.zfill(2)}")

        return ", ".join(season_matches) if season_matches else None


    # Enhanced pattern compilation methods based on Sonarr's QualityParser
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
         ("LanguageVariants", re.compile(r'\b(?:flemish|brazilian|latino|portuguese[-_. ]br|spanish[-_. ]la)\b', re.IGNORECASE)),

         # Language tags (but exclude release groups)
         ("LanguageTags", re.compile(r'\b(?!(?:TGx|YTS|RARBG))(?:(?:VOSTFR|SUB|ESub|MSUBS|DUAL|Multi|MULTI|DUBBED|DUB|TrueFrench|VF|VFF|VFI|VFQ|VOST|VO|OV|OMU|SoftSubs|HardSubs|Subtitled))\b', re.IGNORECASE)),

         # Audio tracks (should not be primary language detection)
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
        ]

    def _compile_year_patterns(self) -> List[Tuple[str, re.Pattern]]:
        return [
            ("(####)", re.compile(r'\((\d{4})\)', re.IGNORECASE)),
            ("####", re.compile(r'\b(\d{4})\b', re.IGNORECASE)),
            ("'##", re.compile(r"'(\d{2})\b", re.IGNORECASE)),
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
            ("KnownSites", re.compile(r'\b(?:TamilRockers|kinokopilka|YTS\.MX|RARBG|ETRG|EVO|Tigole|QxR|DDR|CM|TBS|NTb|TLA|FGT|FQM|TrollHD|CtrlHD|EbP|D-Z0N3|decibeL|HDChina|CHD|WiKi|NGB|HDWinG|HDS|HDArea|HDBits|BeyondHD|BLUTONIUM|FraMeSToR|TayTO)\b', re.IGNORECASE)),
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

        for pattern_name, pattern in self.language_patterns:
          matches = pattern.finditer(normalized_title)
          for match in matches:
            if pattern_name in ["ISO639-1", "ISO639-2", "LanguageNames", "LanguageVariants"]:
                # These are valid language patterns
                language = match.group(0)
                if self._is_valid_language(language):
                    languages.append(language)
            elif pattern_name == "LanguageTags":
                # Language tags need additional validation
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
        'extended', 'director', 'cut', 'theatrical', 'unrated', 'uncut', 'limited'
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
        
        for pattern_name, pattern in self.quality_patterns:
            if pattern.search(normalized_title):
                qualities.append(pattern_name)
        
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

        return None

    def parse_website(self, title: str) -> Optional[str]:
        """Parse website from title using more specific patterns"""
        # Use original title for website parsing (not normalized)
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
            'combined', 'surround', 'stereo', 'dolby'  # Added more false positives
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
        if len(website_lower) < 6:  # Increased minimum length
            return True

        # Check if it looks like a random word with TLD (like episodes.combined)
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
        for pattern_name, pattern in self.group_patterns:
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
        }
        
        # Clean up None values
        result = {k: v for k, v in result.items() if v is not None}
        
        return result




def main():
    parser = TorrentParser()

    # Your test titles list
    test_titles = [
"Longmire (2012) Season 1-6 S01-S06 (1080p BluRay x265 HEVC 10bit AAC 5.1 Silence)",
"Black.Mirror.S01-S05.Tutte.Le.Stagioni.ITA.DLMux.x264-UBi",
"Scorpion.S01-04.ITA.ENG.DLMux.XviD-Pir8",
"기황후.The.Empress.Ki.S01-HD",
"Ultimate Force S01-S04 (2002-2006) SD HEVC H265",
"Grimm.S01-04.WEB-DLRip.Generalfilm",
"Ghost.Wisperer.S01-S05.ITA.DVDRIP.x264-mkeagle3",
"Dexter 2006-2013 [S01-S08] [1080p.WEB-DL.HEVC.-FT][ENG-Lektor PL][Alusia]",
"The Ancient Magus Bride S01-E24 Live and let live.mp4",
"I Love.Lucy.1951–1957.S1-S2-S3-S4-S5-S6-S7-S8-S9.1080p.BLURAY.and.REMUX.and.WEB-DL - [iCMAL]",
"Red.Dead.Redemption.2.PS4-DUPLEX",
"Alpine.The.Simulation.Game.Incl.Update.v1.04.PS4-DUPLEX",
"The High Chaparral - S1xE1-10",
"Dr. House - Medical Division S2 E01-24 WEBRip 1080p HEVC AAC ITA ENG SUB ITA ENG - Lullozzo",
"Game of Thrones S01 E01-07  HDTV Xvid",
"Orange Is the New Black S05 E01-13 BluRay [Hindi 5.1 + English 5.1] 720p x264 AAC ESub - mkvCinemas [Telly]",
"Breeders (S01 E01-07 (10)) (2020) WEB-DL 1080p",
"Sorelle Sbagliate - The Better Sister S1 E01-08 WEBRip 1080p HEVC AAC ITA ENG SUB ITA ENG - Lullozzo",
"Blackstar S01 e01-13 mux by thegatto [T7ST]",
"Teen Titans S03 e01-13",
"Timon e Pumbaa S03 e01-26 by thegatto [T7ST]",
"Keizoku 2 SPEC (2010) E01-10 BoxSet",
]

    # Add the post-processing functions here
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

    # Test with your titles
    results = []
    for i, title in enumerate(test_titles):
        #print(f"\n--- Parsing Title {i+1} ---")
        #print(f"Original: {title}")
        result = parser.parse(title)
        #print(f"Raw result: {result}")
        processed_result = post_process_result(result)

        # Print human-readable
        #print("Processed result:")
        #for key, value in processed_result.items():
        #    if value:  # Only show non-empty values
        #        print(f"  {key}: {value}")

        # Add to results list for JSON output
        results.append(processed_result)

    # Output as separate JSON objects
    print("\n" + "="*50)
    #print("JSON OUTPUT:")
    print("="*50)

    for i, result in enumerate(results):
    #    print(f"\n--- JSON Output {i+1} ---")
        print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()

