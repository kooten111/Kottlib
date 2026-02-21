"""
Test comic loader functionality for archive reading.
"""
import pytest
from pathlib import Path
import zipfile
import tempfile
import shutil

from src.scanner.comic_loader import (
    ComicPage,
    ComicInfo,
    ComicArchive,
    CBZArchive,
    detect_archive_format,
    open_comic,
    is_comic_file,
)


class TestComicPage:
    """Test ComicPage dataclass"""
    
    def test_create_comic_page(self):
        """Test creating a ComicPage"""
        page = ComicPage(
            filename="page001.jpg",
            index=0,
            size=12345
        )
        
        assert page.filename == "page001.jpg"
        assert page.index == 0
        assert page.size == 12345
    
    def test_is_image_jpg(self):
        """Test is_image property for JPG"""
        page = ComicPage(filename="page.jpg", index=0, size=100)
        assert page.is_image is True
    
    def test_is_image_png(self):
        """Test is_image property for PNG"""
        page = ComicPage(filename="page.png", index=0, size=100)
        assert page.is_image is True
    
    def test_is_image_not_image(self):
        """Test is_image property for non-image files"""
        page = ComicPage(filename="metadata.xml", index=0, size=100)
        assert page.is_image is False


class TestComicInfo:
    """Test ComicInfo parsing"""
    
    def test_parse_basic_comic_info(self):
        """Test parsing basic ComicInfo.xml"""
        xml_data = b"""<?xml version="1.0"?>
        <ComicInfo>
            <Title>Test Comic</Title>
            <Series>Test Series</Series>
            <Number>1</Number>
            <Year>2024</Year>
            <Publisher>Test Publisher</Publisher>
        </ComicInfo>
        """
        
        comic_info = ComicInfo.from_xml(xml_data)
        
        assert comic_info.title == "Test Comic"
        assert comic_info.series == "Test Series"
        assert comic_info.number == "1"
        assert comic_info.year == 2024
        assert comic_info.publisher == "Test Publisher"
    
    def test_parse_comic_info_with_creators(self):
        """Test parsing ComicInfo with creator fields"""
        xml_data = b"""<?xml version="1.0"?>
        <ComicInfo>
            <Title>Test</Title>
            <Writer>John Doe</Writer>
            <Penciller>Jane Smith</Penciller>
            <Colorist>Bob Johnson</Colorist>
        </ComicInfo>
        """
        
        comic_info = ComicInfo.from_xml(xml_data)
        
        assert comic_info.writer == "John Doe"
        assert comic_info.penciller == "Jane Smith"
        assert comic_info.colorist == "Bob Johnson"
    
    def test_parse_invalid_xml(self):
        """Test parsing invalid XML returns empty ComicInfo"""
        xml_data = b"Not valid XML"
        
        comic_info = ComicInfo.from_xml(xml_data)
        
        # Should return empty ComicInfo without crashing
        assert comic_info is not None


class TestDetectArchiveFormat:
    """Test archive format detection"""
    
    def test_detect_zip_format(self, test_data_dir):
        """Test detecting ZIP format"""
        # Create a test ZIP file
        zip_path = test_data_dir / "test.cbz"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("page001.jpg", b"fake image data")
        
        format_type = detect_archive_format(zip_path)
        assert format_type == "zip"
    
    def test_detect_unknown_format(self, test_data_dir):
        """Test detecting unknown format"""
        # Create a file that's not an archive
        unknown_path = test_data_dir / "test.txt"
        unknown_path.write_bytes(b"Just text")
        
        format_type = detect_archive_format(unknown_path)
        assert format_type is None


class TestIsComicFile:
    """Test comic file detection"""
    
    def test_is_comic_file_cbz(self):
        """Test CBZ file is recognized"""
        assert is_comic_file(Path("comic.cbz")) is True
    
    def test_is_comic_file_cbr(self):
        """Test CBR file is recognized"""
        assert is_comic_file(Path("comic.cbr")) is True
    
    def test_is_comic_file_cb7(self):
        """Test CB7 file is recognized"""
        assert is_comic_file(Path("comic.cb7")) is True
    
    def test_is_comic_file_zip(self):
        """Test ZIP file is recognized"""
        assert is_comic_file(Path("comic.zip")) is True
    
    def test_is_not_comic_file(self):
        """Test non-comic file is not recognized"""
        assert is_comic_file(Path("document.pdf")) is False
        assert is_comic_file(Path("image.jpg")) is False
        assert is_comic_file(Path("text.txt")) is False


class TestCBZArchive:
    """Test CBZ (ZIP) archive handling"""
    
    @pytest.fixture
    def cbz_file(self, test_data_dir):
        """Create a test CBZ file"""
        cbz_path = test_data_dir / "test_comic.cbz"
        
        with zipfile.ZipFile(cbz_path, 'w') as zf:
            # Add some image pages
            zf.writestr("page001.jpg", b"fake jpg data 1")
            zf.writestr("page002.jpg", b"fake jpg data 2")
            zf.writestr("page003.png", b"fake png data 3")
            
            # Add ComicInfo.xml
            comic_info_xml = b"""<?xml version="1.0"?>
            <ComicInfo>
                <Title>Test CBZ Comic</Title>
                <Series>Test Series</Series>
                <Number>1</Number>
            </ComicInfo>
            """
            zf.writestr("ComicInfo.xml", comic_info_xml)
        
        return cbz_path
    
    def test_open_cbz_archive(self, cbz_file):
        """Test opening a CBZ archive"""
        archive = CBZArchive(cbz_file)
        
        assert archive is not None
        assert cbz_file.exists()
    
    def test_cbz_page_count(self, cbz_file):
        """Test getting page count from CBZ"""
        with CBZArchive(cbz_file) as archive:
            # Should have 3 image pages
            assert archive.page_count == 3
    
    def test_cbz_get_pages(self, cbz_file):
        """Test getting pages list from CBZ"""
        with CBZArchive(cbz_file) as archive:
            pages = archive.pages
            
            assert len(pages) == 3
            assert all(page.is_image for page in pages)
            assert pages[0].index == 0
            assert pages[1].index == 1

    def test_cbz_natural_page_ordering(self, test_data_dir):
        """Test CBZ pages are ordered naturally (1, 2, 10)."""
        cbz_path = test_data_dir / "natural_order.cbz"

        with zipfile.ZipFile(cbz_path, 'w') as zf:
            zf.writestr("10.jpg", b"page-10")
            zf.writestr("2.jpg", b"page-2")
            zf.writestr("1.jpg", b"page-1")

        with CBZArchive(cbz_path) as archive:
            page_names = [Path(page.filename).name for page in archive.pages]

            assert page_names == ["1.jpg", "2.jpg", "10.jpg"]
    
    def test_cbz_get_page_data(self, cbz_file):
        """Test getting page data from CBZ"""
        with CBZArchive(cbz_file) as archive:
            page_data = archive.get_page(0)
            
            assert page_data is not None
            assert len(page_data) > 0
    
    def test_cbz_get_cover(self, cbz_file):
        """Test getting cover (first page) from CBZ"""
        with CBZArchive(cbz_file) as archive:
            cover_data = archive.get_cover()
            
            assert cover_data is not None
            assert len(cover_data) > 0
    
    def test_cbz_parse_comic_info(self, cbz_file):
        """Test parsing ComicInfo.xml from CBZ"""
        with CBZArchive(cbz_file) as archive:
            comic_info = archive.comic_info
            
            assert comic_info is not None
            assert comic_info.title == "Test CBZ Comic"
            assert comic_info.series == "Test Series"
            assert comic_info.number == "1"
    
    def test_cbz_get_file_by_name(self, cbz_file):
        """Test getting file by name from CBZ"""
        with CBZArchive(cbz_file) as archive:
            file_data = archive.get_file("page001.jpg")
            
            assert file_data is not None
            assert file_data == b"fake jpg data 1"
    
    def test_cbz_get_nonexistent_file(self, cbz_file):
        """Test getting nonexistent file returns None"""
        with CBZArchive(cbz_file) as archive:
            file_data = archive.get_file("nonexistent.jpg")
            
            assert file_data is None


class TestOpenComic:
    """Test open_comic convenience function"""
    
    def test_open_comic_cbz(self, test_data_dir):
        """Test opening CBZ with open_comic function"""
        cbz_path = test_data_dir / "test.cbz"
        
        with zipfile.ZipFile(cbz_path, 'w') as zf:
            zf.writestr("page001.jpg", b"fake data")
        
        comic = open_comic(cbz_path)
        
        assert comic is not None
        assert isinstance(comic, CBZArchive)
        comic.close()
    
    def test_open_comic_context_manager(self, test_data_dir):
        """Test using open_comic with context manager"""
        cbz_path = test_data_dir / "test.cbz"
        
        with zipfile.ZipFile(cbz_path, 'w') as zf:
            zf.writestr("page001.jpg", b"fake data")
        
        with open_comic(cbz_path) as comic:
            assert comic is not None
            assert comic.page_count > 0
    
    def test_open_comic_nonexistent(self, test_data_dir):
        """Test opening nonexistent file returns None"""
        comic = open_comic(test_data_dir / "nonexistent.cbz")
        
        assert comic is None


class TestComicArchiveEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_archive(self, test_data_dir):
        """Test handling empty archive"""
        cbz_path = test_data_dir / "empty.cbz"
        
        with zipfile.ZipFile(cbz_path, 'w') as zf:
            pass  # Create empty archive
        
        with CBZArchive(cbz_path) as archive:
            assert archive.page_count == 0
            assert len(archive.pages) == 0
    
    def test_archive_with_only_metadata(self, test_data_dir):
        """Test archive with only ComicInfo.xml"""
        cbz_path = test_data_dir / "metadata_only.cbz"
        
        with zipfile.ZipFile(cbz_path, 'w') as zf:
            zf.writestr("ComicInfo.xml", b"<ComicInfo><Title>Test</Title></ComicInfo>")
        
        with CBZArchive(cbz_path) as archive:
            assert archive.page_count == 0
            assert archive.comic_info is not None
            assert archive.comic_info.title == "Test"
    
    def test_get_invalid_page_index(self, test_data_dir):
        """Test getting page with invalid index"""
        cbz_path = test_data_dir / "test.cbz"
        
        with zipfile.ZipFile(cbz_path, 'w') as zf:
            zf.writestr("page001.jpg", b"data")
        
        with CBZArchive(cbz_path) as archive:
            # Try to get page beyond available pages
            page_data = archive.get_page(999)
            assert page_data is None
