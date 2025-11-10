#!/usr/bin/env python3
"""
Test script for ComicInfo.xml extraction
"""
import sys
from pathlib import Path

# Add the src directory to path
sys.path.insert(0, str(Path(__file__).parent / "yaclib-enhanced" / "src"))

from scanner.comic_loader import ComicInfo

# Create a sample ComicInfo.xml with all fields
sample_xml = b"""<?xml version="1.0"?>
<ComicInfo xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <Title>The Amazing Test Comic</Title>
  <Series>Test Series</Series>
  <Number>42</Number>
  <Count>100</Count>
  <Volume>3</Volume>
  <Summary>An amazing test comic with all metadata fields</Summary>
  <Notes>These are some notes</Notes>
  <Year>2024</Year>
  <Month>11</Month>
  <Day>9</Day>
  <Writer>John Writer</Writer>
  <Penciller>Jane Penciller</Penciller>
  <Inker>Bob Inker</Inker>
  <Colorist>Alice Colorist</Colorist>
  <Letterer>Charlie Letterer</Letterer>
  <CoverArtist>Dave Artist</CoverArtist>
  <Editor>Eve Editor</Editor>
  <Publisher>Test Publishers Inc.</Publisher>
  <Imprint>Test Imprint</Imprint>
  <Genre>Superhero, Action</Genre>
  <Web>https://example.com/comic</Web>
  <StoryArc>The Great Story Arc</StoryArc>
  <StoryArcNumber>5</StoryArcNumber>
  <SeriesGroup>Test Universe</SeriesGroup>
  <AlternateSeries>Alternate Test</AlternateSeries>
  <AlternateNumber>10</AlternateNumber>
  <AlternateCount>50</AlternateCount>
  <AgeRating>Teen</AgeRating>
  <CommunityRating>4.5</CommunityRating>
  <Characters>Hero, Villain, Sidekick</Characters>
  <Teams>Justice Squad, Legion of Doom</Teams>
  <Locations>Metropolis, Gotham City</Locations>
  <PageCount>24</PageCount>
  <LanguageISO>en</LanguageISO>
  <Format>Series</Format>
  <BlackAndWhite>No</BlackAndWhite>
  <Manga>No</Manga>
  <GTIN>9781234567890</GTIN>
</ComicInfo>
"""

print("Testing ComicInfo.xml parsing...")
print("=" * 60)

info = ComicInfo.from_xml(sample_xml)

# Display all extracted fields
fields = [
    ("Title", info.title),
    ("Series", info.series),
    ("Number", info.number),
    ("Count", info.count),
    ("Volume", info.volume),
    ("Summary", info.summary[:50] + "..." if info.summary and len(info.summary) > 50 else info.summary),
    ("Notes", info.notes),
    ("Year", info.year),
    ("Month", info.month),
    ("Day", info.day),
    ("Writer", info.writer),
    ("Penciller", info.penciller),
    ("Inker", info.inker),
    ("Colorist", info.colorist),
    ("Letterer", info.letterer),
    ("Cover Artist", info.cover_artist),
    ("Editor", info.editor),
    ("Publisher", info.publisher),
    ("Imprint", info.imprint),
    ("Genre", info.genre),
    ("Web", info.web),
    ("Story Arc", info.story_arc),
    ("Story Arc Number", info.story_arc_number),
    ("Series Group", info.series_group),
    ("Alternate Series", info.alternate_series),
    ("Alternate Number", info.alternate_number),
    ("Alternate Count", info.alternate_count),
    ("Age Rating", info.age_rating),
    ("Community Rating", info.community_rating),
    ("Characters", info.characters),
    ("Teams", info.teams),
    ("Locations", info.locations),
    ("Page Count", info.page_count),
    ("Language ISO", info.language_iso),
    ("Format", info.format),
    ("Black and White", info.black_and_white),
    ("Manga", info.manga),
    ("GTIN", info.gtin),
]

extracted_count = 0
for field_name, field_value in fields:
    if field_value is not None:
        print(f"✓ {field_name:20s}: {field_value}")
        extracted_count += 1
    else:
        print(f"✗ {field_name:20s}: None")

print("=" * 60)
print(f"Extracted {extracted_count}/{len(fields)} fields successfully!")

if extracted_count == len(fields):
    print("✓ All fields extracted successfully!")
    sys.exit(0)
else:
    print(f"✗ {len(fields) - extracted_count} fields were not extracted")
    sys.exit(1)
