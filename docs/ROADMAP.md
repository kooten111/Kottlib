# Kottlib Roadmap

This document outlines planned features and improvements for Kottlib.

## Completed Phases

✅ **Phase 1: Foundation** - Core functionality, database, API server
✅ **Phase 2: Mobile UX** - Folder-first sorting, reading progress
✅ **Phase 3: Service Layer** - Business logic extraction
✅ **Phase 4: Code Quality** - Type hints, documentation, testing

---

## Future Enhancements

### High Priority

#### Metadata & Search
- [ ] Add Jikan scanner as fallback for AniList
- [ ] Implement metadata result caching to reduce API calls
- [ ] Add batch metadata processing API
- [ ] Web UI for manual metadata review and selection
- [ ] Enhanced full-text search with better ranking

#### Performance
- [ ] Redis caching layer for frequently accessed data
- [ ] Background job queue for long-running tasks
- [ ] CDN support for cover images
- [ ] Database query optimization and indexing
- [ ] Lazy loading for large series lists

#### User Experience
- [ ] User preferences and settings management
- [ ] Custom reading lists with ordering
- [ ] Collections/tags management UI
- [ ] Series-level reading progress
- [ ] Recommendations based on reading history

### Medium Priority

#### API & Integration
- [ ] GraphQL API alongside REST
- [ ] Webhook support for external integrations
- [ ] Export/import library metadata
- [ ] OPDS feed improvements
- [ ] Komga compatibility layer

#### Scanner Improvements
- [ ] Resume interrupted library scans
- [ ] Incremental scanning (only changed files)
- [ ] Parallel library scanning
- [ ] Scanner plugin hot-reload
- [ ] Scanner rate limiting improvements

#### Content Management
- [ ] Duplicate detection and management
- [ ] Bulk metadata editing
- [ ] Automated series grouping improvements
- [ ] Multi-language metadata support
- [ ] Series tracking (reading status, favorites)

### Low Priority

#### Developer Experience
- [ ] OpenAPI schema validation in tests
- [ ] Performance benchmarking suite
- [ ] Integration test improvements
- [ ] Developer documentation expansion
- [ ] Contribution guidelines

#### Platform Support
- [ ] Docker Compose with services
- [ ] Kubernetes deployment guide
- [ ] Windows service installer
- [ ] macOS app bundle
- [ ] ARM64 optimizations

#### Advanced Features
- [ ] Machine learning for cover detection
- [ ] Automatic chapter splitting for long files
- [ ] Reading statistics and analytics
- [ ] Social features (sharing, reviews)
- [ ] Multi-user administration

---

## Code Improvements

### Refactoring Opportunities

#### API Routers
Some routers are still quite large and could benefit from further splitting:
- `src/api/routers/v2/series.py` (31 KB) - Could split into query, update, and metadata endpoints
- `src/api/routers/v2/comics.py` (28 KB) - Could split by concern (CRUD, search, metadata)
- `src/api/routers/v2/folders.py` (24 KB) - Could extract nested operations

#### Service Layer Expansion
Additional services could be extracted:
- **LibraryService** - Centralize library management logic
- **ScanService** - Centralize scanning orchestration
- **SearchService** - Centralize search logic
- **CoverService** - Centralize cover management
- **ReadingService** - Centralize reading progress logic

#### Utility Organization
Create focused utility modules:
- `src/utils/paths.py` - Path manipulation utilities
- `src/utils/hashing.py` - File hashing utilities
- `src/utils/exceptions.py` - Custom exception classes
- `src/utils/validators.py` - Input validation helpers

### Testing Gaps
- [ ] API integration tests for all v2 endpoints
- [ ] Scanner plugin testing framework
- [ ] Database migration testing
- [ ] Performance regression tests
- [ ] WebUI component tests

### Documentation Needs
- [ ] API usage examples and tutorials
- [ ] Scanner development guide with examples
- [ ] Deployment guide for various platforms
- [ ] Troubleshooting guide
- [ ] FAQ document

---

## Community & Contribution

### Wanted Contributions
- New metadata scanner implementations
- Additional archive format support
- UI/UX improvements
- Documentation improvements
- Translation/i18n support
- Bug reports and fixes

### Plugin Ecosystem Ideas
- Custom scanner plugins marketplace
- Custom cover provider plugins
- Custom thumbnail generator plugins
- Reader themes and layouts

---

## Version Planning

### v1.0 (Current)
- Core functionality complete
- Service layer refactored
- Type hints added
- Documentation consolidated

### v1.1 (Next)
- Performance improvements
- Enhanced metadata caching
- Additional scanner plugins
- UI polish

### v1.2
- GraphQL API
- Advanced search features
- Collections management
- Reading statistics

### v2.0 (Future)
- Multi-user enhancements
- Advanced social features
- Plugin marketplace
- Cloud sync support

---

## Contributing

See issues on GitHub for specific tasks that need help. Label filters:
- `good-first-issue` - Great for new contributors
- `enhancement` - Feature requests
- `bug` - Bug reports
- `help-wanted` - Looking for contributors
- `documentation` - Documentation improvements

---

**Last Updated:** December 2024
