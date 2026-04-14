"""
Structured Document Parser

Extracts API constraints from documentation with source tracking.
Targets 90%+ extraction accuracy for API parameter constraints using regex and heuristic rules.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set, Tuple
import re
from bs4 import BeautifulSoup, Tag
import logging

logger = logging.getLogger(__name__)


@dataclass
class APIConstraint:
    """Represents a single API parameter constraint extracted from documentation."""

    parameter: str
    value: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[str]] = None
    description: Optional[str] = None
    source_url: Optional[str] = None
    section: Optional[str] = None
    constraint_type: Optional[str] = None  # 'range', 'enum', 'pattern', etc.

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format, excluding None values."""
        result = {
            'parameter': self.parameter,
        }
        if self.value is not None:
            result['value'] = self.value
        if self.min_value is not None:
            result['min_value'] = self.min_value
        if self.max_value is not None:
            result['max_value'] = self.max_value
        if self.allowed_values is not None:
            result['allowed_values'] = self.allowed_values
        if self.description is not None:
            result['description'] = self.description
        if self.source_url is not None:
            result['source_url'] = self.source_url
        if self.section is not None:
            result['section'] = self.section
        if self.constraint_type is not None:
            result['constraint_type'] = self.constraint_type
        return result


class StructuredDocParser:
    """
    Parser for extracting structured API constraints from documentation.

    Handles various documentation formats (HTML, Text) and extracts parameter constraints
    using regex patterns for common API parameters like dimension, metric, top_k, etc.
    """

    # Parameter name patterns for common API parameters
    PARAM_PATTERNS = {
        'dimension': re.compile(
            r'\b(dimension|dimensions?|dim|dims?|vector_dimension|vec_dim)\b',
            re.IGNORECASE
        ),
        'metric': re.compile(
            r'\b(metrics?|distance|similarity|distance_metric|similarity_metric)\b',
            re.IGNORECASE
        ),
        'top_k': re.compile(
            r'\b(top[kk_]?\s*\(?k\)?|topk|limit|k\s*\(\s*\d+\s*\))\b',
            re.IGNORECASE
        ),
        'collection_name': re.compile(
            r'\b(collection[_-]?name|table[_-]?name|index[_-]?name)\b',
            re.IGNORECASE
        ),
        'payload_size': re.compile(
            r'\b(payload[_-]?size?|batch[_-]?size|page[_-]?size|max[_-]?size)\b',
            re.IGNORECASE
        ),
        'index_type': re.compile(
            r'\b(index[_-]?type|index[_-]?method|index_type)\b',
            re.IGNORECASE
        ),
        'nlist': re.compile(
            r'\b(nlist|n_list|centroid_count)\b',
            re.IGNORECASE
        ),
        'nprobe': re.compile(
            r'\b(nprobe|n_probe|search_param)\b',
            re.IGNORECASE
        ),
        'ef': re.compile(
            r'\b(ef[_-]?construction|ef[_-]?search|hni?w[_-]?ef)\b',
            re.IGNORECASE
        ),
        'm': re.compile(
            r'\b(\bm\b|max_connections|neighbors)\b',
            re.IGNORECASE
        ),
    }

    # Section patterns that indicate API reference sections
    API_SECTION_PATTERNS = [
        re.compile(r'\bAPI\s+Reference\b', re.IGNORECASE),
        re.compile(r'\bREST\s+API\b', re.IGNORECASE),
        re.compile(r'\bHTTP\s+API\b', re.IGNORECASE),
        re.compile(r'\bAPI\s+Documentation\b', re.IGNORECASE),
        re.compile(r'\bParameters?\b', re.IGNORECASE),
        re.compile(r'\bRequest\s+Body\b', re.IGNORECASE),
        re.compile(r'\bQuery\s+Parameters?\b', re.IGNORECASE),
        re.compile(r'\bRequest\s+Parameters?\b', re.IGNORECASE),
        re.compile(r'\bSchema\b', re.IGNORECASE),
    ]

    # Value constraint patterns
    RANGE_PATTERN = re.compile(
        r'(?:value|must|should|range|between|from)?\s*[:=]\s*'
        r'(\d+(?:\.\d+)?)\s*(?:to|-|~|through)\s*(\d+(?:\.\d+)?)',
        re.IGNORECASE
    )

    MAX_VALUE_PATTERN = re.compile(
        r'(?:maximum|max|up\s+to|at\s+most|less\s+than\s+or\s+equal\s+to|limit)\s*[:=]?\s*(\d+(?:\.\d+)?)',
        re.IGNORECASE
    )

    MIN_VALUE_PATTERN = re.compile(
        r'(?:minimum|min|at\s+least|greater\s+than\s+or\s+equal\s+to)\s*[:=]?\s*(\d+(?:\.\d+)?)',
        re.IGNORECASE
    )

    ENUM_PATTERN = re.compile(
        r'(?:must|should|value|options?|choices?|supported|metrics?)\s*(?:be)?\s*(?:one\s+of|:)?\s*'
        r'(?:\[([^\]]+)\]|(?:\((?:[^)]+)\))(?:\s*(?:or|,)\s*\(?:[^)]+\))*|([\w\s,|-]+))',
        re.IGNORECASE
    )

    DEFAULT_VALUE_PATTERN = re.compile(
        r'(?:default|defaults?\s*(?:to|:|=))\s*'
        r'(["\']?)(\w+(?:\s*\(\s*\d+\s*\))?)(?:\1|(?:,|\.|\s|$))',
        re.IGNORECASE
    )

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize the parser.

        Args:
            base_url: Base URL for resolving relative links
        """
        self.base_url = base_url
        self.constraints: List[APIConstraint] = []

    def parse(
        self,
        content: str,
        source_url: Optional[str] = None
    ) -> List[APIConstraint]:
        """
        Generic parse method that detects content type and extracts constraints.

        Args:
            content: Raw documentation content (HTML or Text)
            source_url: Optional URL source for the content

        Returns:
            List of extracted APIConstraint objects
        """
        if not content:
            return []

        # Check if it looks like HTML
        if '<html' in content.lower() or '<body' in content.lower() or '<div' in content.lower():
            return self.parse_html_content(content, source_url)
        else:
            return self.parse_text_content(content, source_url)

    def parse_html_content(
        self,
        html_content: str,
        source_url: Optional[str] = None
    ) -> List[APIConstraint]:
        """Parse HTML content and extract API constraints."""
        soup = BeautifulSoup(html_content, 'html.parser')
        self.constraints = []

        # Find API sections first
        api_sections = self._find_api_sections(soup)

        # Extract constraints from API sections
        for section_elem, section_name in api_sections:
            self._extract_constraints_from_section(
                section_elem,
                section_name,
                source_url
            )

        # Also scan entire document for parameter mentions
        self._extract_constraints_global(soup, source_url)

        # Deduplicate constraints
        self.constraints = self._deduplicate_constraints(self.constraints)
        return self.constraints

    def parse_text_content(
        self,
        text_content: str,
        source_url: Optional[str] = None
    ) -> List[APIConstraint]:
        """Parse plain text content and extract API constraints."""
        self.constraints = []
        
        # Scan text for parameter mentions and extract context
        for param_name, pattern in self.PARAM_PATTERNS.items():
            matches = pattern.finditer(text_content)
            for match in matches:
                # Get context around the match
                start = max(0, match.start() - 250)
                end = min(len(text_content), match.end() + 250)
                context = text_content[start:end]

                self._extract_constraints_from_text(
                    context,
                    match.group(),
                    source_url
                )
        
        # Deduplicate constraints
        self.constraints = self._deduplicate_constraints(self.constraints)
        return self.constraints

    def _find_api_sections(self, soup: BeautifulSoup) -> List[Tuple[Tag, str]]:
        """Identify sections that likely contain API documentation."""
        sections = []
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            for heading in soup.find_all(tag):
                text = heading.get_text(strip=True)
                if any(pattern.search(text) for pattern in self.API_SECTION_PATTERNS):
                    section_content = self._get_section_content(heading, tag)
                    sections.append((section_content, text))
        return sections

    def _get_section_content(self, heading: Tag, heading_tag: str) -> Tag:
        """Get all content between this heading and the next heading of same or higher level."""
        level = int(heading_tag[1])
        content = []
        for sibling in heading.find_next_siblings():
            if sibling.name and sibling.name.startswith('h'):
                try:
                    sibling_level = int(sibling.name[1])
                    if sibling_level <= level:
                        break
                except (ValueError, IndexError):
                    pass
            content.append(sibling)

        container_soup = BeautifulSoup('<div></div>', 'html.parser')
        container = container_soup.find('div')
        for elem in content:
            container.append(elem.__copy__())
        return container

    def _extract_constraints_from_section(
        self,
        section: Tag,
        section_name: str,
        source_url: Optional[str]
    ) -> None:
        """Extract constraints from a specific section."""
        # Look for parameter tables
        tables = section.find_all('table')
        for table in tables:
            self._extract_from_table(table, section_name, source_url)

        # Look for parameter lists
        for list_type in ['dl', 'ul', 'ol']:
            lists = section.find_all(list_type)
            for lst in lists:
                self._extract_from_list(lst, section_name, source_url)

        # Look for code blocks
        code_blocks = section.find_all(['pre', 'code'])
        for code in code_blocks:
            self._extract_from_code_block(code, section_name, source_url)

        # Look for paragraphs with parameter mentions
        paragraphs = section.find_all('p')
        for p in paragraphs:
            text = p.get_text(strip=True)
            if self._find_parameter_in_text(text):
                self._extract_constraints_from_text(text, None, source_url, section_name)

    def _extract_from_table(self, table: Tag, section_name: str, source_url: Optional[str]) -> None:
        rows = table.find_all('tr')
        if not rows: return
        
        headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(['th', 'td'])]
        data_rows = rows[1:]

        param_col = self._find_header_column(headers, ['parameter', 'param', 'name', 'field'])
        desc_col = self._find_header_column(headers, ['description', 'desc', 'detail', 'meaning'])

        for row in data_rows:
            cells = row.find_all(['td', 'th'])
            if not cells: continue
            
            param_name = cells[param_col].get_text(strip=True) if param_col is not None and param_col < len(cells) else None
            if not param_name:
                for cell in cells:
                    text = cell.get_text(strip=True)
                    if self._is_parameter_name(text):
                        param_name = text
                        break
            
            if param_name:
                description = cells[desc_col].get_text(strip=True) if desc_col is not None and desc_col < len(cells) else None
                self._extract_and_add_constraint(param_name, description, section_name, source_url)

    def _extract_from_list(self, lst: Tag, section_name: str, source_url: Optional[str]) -> None:
        if lst.name == 'dl':
            terms = lst.find_all('dt')
            for term in terms:
                param_name = term.get_text(strip=True)
                if self._is_parameter_name(param_name):
                    desc_elem = term.find_next_sibling('dd')
                    description = desc_elem.get_text(strip=True) if desc_elem else None
                    self._extract_and_add_constraint(param_name, description, section_name, source_url)
        else:
            items = lst.find_all('li', recursive=False)
            for item in items:
                text = item.get_text(strip=True)
                match = re.match(r'^(\w+)\s*[:=]\s*(.+)$', text)
                if match:
                    param_name, description = match.groups()
                    if self._is_parameter_name(param_name):
                        self._extract_and_add_constraint(param_name, description, section_name, source_url)

    def _extract_from_code_block(self, code: Tag, section_name: str, source_url: Optional[str]) -> None:
        code_text = code.get_text(strip=True)
        try:
            import json
            data = json.loads(code_text)
            self._extract_from_json_schema(data, section_name, source_url)
        except Exception as e:
            logger.debug(
                "[StructuredDocParser] Code block is not valid JSON in section='%s', fallback to text extraction: %s",
                section_name,
                e
            )
            self._extract_constraints_from_text(code_text, None, source_url, section_name)

    def _extract_from_json_schema(self, data: Any, section_name: str, source_url: Optional[str]) -> None:
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict) and self._is_parameter_name(key):
                    constraint = APIConstraint(parameter=key, source_url=source_url, section=section_name)
                    if 'enum' in value and isinstance(value['enum'], list):
                        constraint.allowed_values = value['enum']
                        constraint.constraint_type = 'enum'
                    if 'minimum' in value:
                        constraint.min_value = float(value['minimum'])
                        constraint.constraint_type = 'range'
                    if 'maximum' in value:
                        constraint.max_value = float(value['maximum'])
                        constraint.constraint_type = 'range'
                    if 'default' in value:
                        constraint.value = str(value['default'])
                    if any([constraint.allowed_values, constraint.min_value is not None, 
                           constraint.max_value is not None, constraint.value]):
                        self.constraints.append(constraint)

    def _extract_constraints_global(self, soup: BeautifulSoup, source_url: Optional[str]) -> None:
        text = soup.get_text()
        self.parse_text_content(text, source_url)

    def _extract_constraints_from_text(
        self,
        text: str,
        param_hint: Optional[str] = None,
        source_url: Optional[str] = None,
        section: Optional[str] = None
    ) -> None:
        """Extract constraints from free-form text using regex."""
        # Find the parameter name in the text
        param = self._find_parameter_in_text(text) or param_hint
        if not param:
            return

        found = False
        # Look for range patterns
        range_match = self.RANGE_PATTERN.search(text)
        if range_match:
            constraint = APIConstraint(
                parameter=param,
                min_value=float(range_match.group(1)),
                max_value=float(range_match.group(2)),
                constraint_type='range',
                source_url=source_url,
                section=section
            )
            self.constraints.append(constraint)
            found = True

        # Look for max value patterns
        max_match = self.MAX_VALUE_PATTERN.search(text)
        if max_match and not range_match:
            constraint = APIConstraint(
                parameter=param,
                max_value=float(max_match.group(1)),
                constraint_type='range',
                source_url=source_url,
                section=section
            )
            self.constraints.append(constraint)
            found = True

        # Look for min value patterns
        min_match = self.MIN_VALUE_PATTERN.search(text)
        if min_match and not range_match:
            constraint = APIConstraint(
                parameter=param,
                min_value=float(min_match.group(1)),
                constraint_type='range',
                source_url=source_url,
                section=section
            )
            self.constraints.append(constraint)
            found = True

        # Look for enum patterns
        enum_match = self.ENUM_PATTERN.search(text)
        if enum_match:
            values_str = enum_match.group(1) or enum_match.group(2) or enum_match.group(0)
            values = [v.strip().strip('"\'') for v in re.split(r'[,|]', values_str)]
            values = [v for v in values if v and len(v) < 50 and not v.lower() in ['supported', 'metrics']]

            if values:
                constraint = APIConstraint(
                    parameter=param,
                    allowed_values=values,
                    constraint_type='enum',
                    source_url=source_url,
                    section=section
                )
                self.constraints.append(constraint)
                found = True

        # Look for default value
        default_match = self.DEFAULT_VALUE_PATTERN.search(text)
        if default_match:
            constraint = APIConstraint(
                parameter=param,
                value=default_match.group(2),
                source_url=source_url,
                section=section
            )
            self.constraints.append(constraint)
            found = True

    def _extract_and_add_constraint(
        self,
        param_name: str,
        description: Optional[str],
        section_name: str,
        source_url: Optional[str]
    ) -> None:
        if not description:
            self.constraints.append(APIConstraint(parameter=param_name, source_url=source_url, section=section_name))
            return

        self._extract_constraints_from_text(description, param_name, source_url, section_name)

    def _find_parameter_in_text(self, text: str) -> Optional[str]:
        for param_name, pattern in self.PARAM_PATTERNS.items():
            if pattern.search(text):
                return param_name
        return None

    def _is_parameter_name(self, text: str) -> bool:
        for pattern in self.PARAM_PATTERNS.values():
            if pattern.match(text):
                return True
        param_indicators = ['_name', '_type', '_size', '_count', '_id', 'limit', 'k']
        return any(indicator in text.lower() for indicator in param_indicators)

    def _find_header_column(self, headers: List[str], keywords: List[str]) -> Optional[int]:
        for keyword in keywords:
            for i, header in enumerate(headers):
                if keyword in header.lower():
                    return i
        return None

    def _deduplicate_constraints(self, constraints: List[APIConstraint]) -> List[APIConstraint]:
        seen: Dict[str, APIConstraint] = {}
        for constraint in constraints:
            key = constraint.parameter.lower()
            existing = seen.get(key)
            if existing is None:
                seen[key] = constraint
            else:
                existing_score = sum(1 for v in [existing.value, existing.min_value, existing.max_value, existing.allowed_values] if v is not None)
                new_score = sum(1 for v in [constraint.value, constraint.min_value, constraint.max_value, constraint.allowed_values] if v is not None)
                if new_score > existing_score:
                    seen[key] = constraint
        return list(seen.values())
