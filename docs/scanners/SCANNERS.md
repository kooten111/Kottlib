
Definitive Architectural Analysis: ComicInfo.xml Metadata Sourcing


Executive Summary: The Architect's View

This report provides a comprehensive architectural analysis of metadata sources for populating the ComicInfo.xml schema for a digital media scanner. It concludes that a single-source API solution is architecturally non-viable for a mixed-media library composed of both Western Comics and Japanese Manga. The data models, creator role definitions, and publication hierarchies are fundamentally divergent between these domains.
A hybrid, two-pronged architectural strategy is the only robust and scalable solution.
For Western Comics: The Comic Vine API is the designated source. It is the only API analyzed with the correct domain focus, structuring data by issues, volumes, and series that conceptually map to the ComicInfo.xml standard.1 However, this API possesses significant, known data voids—most notably, the Format, PageCount, and Genre fields, which are missing from its responses.2
For Manga: The AniList GraphQL API is demonstrably the superior and more stable primary source. Its modern GraphQL implementation allows for rich, efficient, single-call data retrieval (e.g., media, staff, and relations).3 It provides live, real-time data from a primary database, which is a critical advantage for data freshness.
This analysis identifies a key paradox: the manga-focused APIs (AniList and Jikan) are paradoxically better at populating certain ComicInfo.xml fields (such as Format and Genre) than the Western-focused Comic Vine API, which fails to provide this data.2
This report strongly advises against using the Jikan API for a production-grade system. While functionally capable, its status as an unofficial scraper of MyAnimeList introduces unacceptable long-term architectural risks.6 Its 24-hour server-side caching policy guarantees stale data 7, and the entire service is subject to cascading failure should MyAnimeList alter its website structure. AniList, as an official, stable API, represents a far sounder long-term investment.
Finally, a critical data gap exists. The ComicInfo.xml Pages element 8 is a file-level manifest (detailing page types, image dimensions, and file sizes). No external bibliographic API (AniList, Comic Vine, or Jikan) provides this information. This data must be generated locally by the scanner application itself.

Part 1: The Target Schema - ComicInfo.xml Specification Analysis


1.1 Origins, Governance, and Purpose

The ComicInfo.xml metadata standard originated from the once-popular but now-defunct Windows application, ComicRack.9 Despite the application's discontinuation, the XML file itself was adopted as a de facto standard for embedding metadata within digital comic archives (e.g., .cbz, .cbr).
Today, the standard's documentation, evolution, and governance are managed by The Anansi Project.9 This community-driven initiative aims to centralize the schema's documentation, clarify the intended use of each field, and provide a stable target for the many applications that have come to rely on it.10 This provides a critical, centralized authority for the schema, ensuring its long-term viability as a metadata target.

1.2 Deconstruction of the ComicInfo Schema (Core Fields)

The most unambiguous definition of the ComicInfo.xml schema is provided by the Go language struct in the go-comicinfo library, which is built to parse and generate these files.8 This provides a machine-readable definition of all top-level fields.
Core Bibliographic Fields: Title (string), Series (string), Number (string), Count (int), Volume (int).8 The Number field is a string to accommodate non-integer issue numbers (e.g., "0", "1/2", or "FCBD").
Date Fields: Year (int), Month (int), Day (int). These are typically used for the issue's release or cover date.8
Descriptive Fields: Summary (string), Notes (string), Genre (string), Characters (string), Teams (string), Locations (string), StoryArc (string), and SeriesGroup (string).8
Technical & Publication Fields: PageCount (int), LanguageISO (string), Format (string), and BlackAndWhite (a YesNo enum).8
The documentation notes that for fields intended to hold multiple values, such as Genre or Characters, the accepted usage is a single string with values separated by commas.11

1.3 Analysis of Creator Roles and Publication Data

The ComicInfo.xml schema's design center is unambiguously the production line of the American (US) comic book industry. This "Western bias" is most evident in its highly specific creator role fields 8:
Writer
Penciller
Inker
Colorist
Letterer
CoverArtist
Editor
This discrete breakdown of the art process (pencil, ink, color) is not a universal model and, as will be discussed, creates a significant data-mapping challenge for media like manga.
Furthermore, the schema documentation for the Volume field explicitly states this US-centric bias: "Volume is a notion that is specific to US Comics, where the same series can have multiple volumes. Volumes can be referenced by number (1, 2, 3...) or by year (2018, 2020...)".11
The schema does, however, include a Manga field.8 This field, likely an enum (e.g., "Yes", "No", "YesAndRightToLeft"), is a critical architectural hook. Its existence proves that the schema is aware of the domain conflict. A well-designed scanner application can and should use this field as a routing instruction. A file tagged with Manga="Yes" should be routed to a manga-specific API (AniList), while Manga="No" should be routed to a Western-focused API (Comic Vine).

1.4 The Pages Element: A Structured Data Deep Dive

A common misconception is that all fields in ComicInfo.xml represent bibliographic data that can be fetched from an external API. The Pages element categorically proves this false.
The Pages field is not a simple integer; it is a complex struct containing an array (ComicPageInfo).8 Each ComicPageInfo object within this array is a descriptor for a single page (image file) in the archive, containing its own attributes 8:
Image: The (0-based) index of the page.
Type: An enum (e.g., "FrontCover", "Story", "Advertisement", "Deleted").
DoublePage: A boolean flag.
ImageSize: The page's file size in bytes.
ImageWidth: The page's image width in pixels.
ImageHeight: The page's image height in pixels.
This Pages structure is not bibliographic metadata; it is a file manifest and a form of scanner-generated data. No external online database (Comic Vine, AniList, or Jikan) tracks this information. This data cannot be "scraped." It must be generated by the scanner application locally by opening the comic archive (e.g., unzipping the .cbz), iterating through the image files, and measuring their properties. This is a non-trivial processing step that falls entirely on the application's developer and cannot be outsourced to an API.

Part 2: The Foundational Conflict - Western Comics vs. Manga Data Models


2.1 Why a Single Source is Architecturally Infeasible

The user query, by listing Comic Vine and AniList/Jikan, inherently proves the application must support a mixed-media library. Applying a single data source to this mixed library is architecturally non-viable.
The data models of the target sources are incompatible because their content domains are incompatible.
Comic Vine (Western comics) is structured around a hierarchy of series, volumes, and issues.1 "Issues" are the primary unit of publication.
AniList & Jikan (Manga) are structured around series, volumes (tankōbon), and chapters.4 "Chapters" are the primary unit of publication, and volumes are collected editions of those chapters.
Attempting to find metadata for a Western comic (e.g., "The Amazing Spider-Man") on AniList will yield poor or no results. Likewise, searching for a manga (e.g., "Naruto") on Comic Vine will provide incomplete or incorrectly structured data. Therefore, any robust scanner must be a hybrid system, capable of routing queries to the correct domain-specific API.

2.2 Creator Role Mismatches (e.g., Penciller/Inker vs. Staff)

The most significant mapping challenge lies in the creator roles. As established in Part 1.3, ComicInfo.xml demands discrete roles for Penciller, Inker, and Colorist.8
Manga production does not follow this model. It typically involves a single Mangaka who handles "Story & Art," or a pairing of "Story" (Author) and "Art" (Artist). This role may be supported by uncredited Assistants.
The AniList API accurately reflects this reality. Instead of discrete fields like Penciller, it provides a generic staff connection.4 A query on this connection would return a list of staff members, each with a role (e.g., "Story", "Art", "Story & Art").
This creates a "lossy" mapping problem. A scanner, fetching data from AniList, will face a mapping dilemma. How does one map an AniList staff member with role "Art" to the ComicInfo.xml schema?
Does this data go into the Penciller field?
Does it go into the Inker field?
Should it be duplicated in both?
This mapping will be a "best-fit" compromise and inherently lossy. A Western comic's data, pulled from Comic Vine, will map cleanly role-for-role. A manga's data will not. This must be an explicit design decision. The most logical compromise is to map any "Art" role from AniList/Jikan to the Penciller field in ComicInfo.xml.

2.3 Publication Hierarchy Mismatches (e.g., Volume vs. Tankōbon)

A similar, though more subtle, conflict exists in publication hierarchy. The ComicInfo.xml Volume field is an organizational concept for US comics to differentiate series of the same name (e.g., "Batman Vol. 1" from 1940 vs. "Batman Vol. 2" from 2011).11
AniList and Jikan's volumes fields 4 refer to the physical collected editions (tankōbon) of a manga.
While the field name is the same, the semantic meaning is different. However, in practice, mapping Media.volumes (from AniList) to ComicInfo.Volume (in the XML) is the logical and most practical choice for a scanner. The more significant mismatch is that ComicInfo.xml has no field for chapters, which is a primary data point in the manga-focused APIs.4

Part 3: Comparative Technical & Integration Analysis


3.1 API Paradigm: AniList (GraphQL) vs. Comic Vine/Jikan (REST)

AniList (GraphQL): AniList provides a modern, powerful GraphQL v2 API.3 This is a significant architectural choice.
Pro: A single, complex query can retrieve a manga, its staff, its character list, and its sequels/prequels in one network request. This dramatically reduces the number of API calls, saving on rate limits and improving scanner performance.3 It also prevents over-fetching; the client requests only the fields it needs to map to ComicInfo.xml.
Con: Requires a dedicated GraphQL client library and a more complex query-building process compared to simple REST.
Comic Vine & Jikan (REST): Both Comic Vine and Jikan utilize standard RESTful APIs.6
Pro: Simple, universally understood, and easily implemented with any basic HTTP client.
Con: This paradigm can be "chatty." To aggregate the same amount of data as the single GraphQL call, a scanner might need to make multiple requests (e.g., GET /series/{id}, then GET /series/{id}/issues, then GET /issue/{id}/characters), putting more pressure on rate limits.

3.2 Authentication, Authorization, and Security Models

AniList: Implements the industry-standard OAuth2 for authentication.15 An access token, sent as a Bearer header, is required for all API requests, even for public data.16 This is the most complex model to implement, likely requiring a one-time user authorization flow or the storage of a long-lived developer token.
Comic Vine: Requires a simple, static API key. This key is passed as a URL parameter in the GET request.1 This is trivial to implement but is a less secure practice than using headers.
Jikan: As an unofficial, read-only wrapper, Jikan requires no authentication for public data queries.19 It explicitly does not support authenticated requests for user-specific actions like list updates.6 This is the simplest possible implementation.

3.3 Rate Limiting, Throttling, and Caching: A Practical Bottleneck Analysis

This is a critical area for a bulk "scanner" application, which will, by nature, make many requests.
AniList: The v2 API limit is 90 requests per minute.21 This is a generous limit for a modern API. Critically, AniList provides programmatic headers like X-RateLimit-Reset and Retry-After.21 This allows a well-built scanner to handle throttling gracefully and automatically, making it a robust, professional-grade service.
Comic Vine: The official limit is stated as 200 requests per resource, per hour.1 This is ambiguous and potentially very restrictive. However, the documentation also mentions "velocity detection" to block rapid per-second requests.1 One user claims to scan 50,000+ comics annually without issue.2 The logical reconciliation is that the 200/hr limit is a bulk limit, while velocity detection is a burst limit. A scanner must implement a robust, client-side throttle to "trickle" requests (e.g., one request every 2-3 seconds) to stay under both limits.
Jikan: The v4 API limit is 60 requests per minute and 3 requests per second.7 This is a reasonable and clearly defined limit.
Jikan's Caching Risk (The Deal-Breaker): The real bottleneck for Jikan is its server-side caching. All requests are aggressively cached for 24 hours.7 This is a direct consequence of its unofficial scraper architecture; Jikan must cache this heavily to protect itself (and MyAnimeList) from being rate-limited or banned.6 For a scanner application, this means that if a user adds a brand-new manga, Jikan will not see it for up to 24 hours. If an admin on MyAnimeList corrects a typo, the scanner will continue to pull that typo for 24 more hours. This makes AniList, which provides live data, the far superior choice for data freshness and accuracy.

Table: API Integration Cost-Benefit Analysis


Feature
AniList (v2)
Comic Vine
Jikan (v4)
API Paradigm
GraphQL
REST
REST
Auth Model
OAuth2 (Token Required)
API Key (in URL)
None (for read-only)
Data Model
Manga / Anime
Western Comics
Manga / Anime
Query Rate Limit
90 requests / minute
200 requests / resource / hour
60 requests / minute
Data Freshness
Live / Real-time
Live / Real-time
24-hour Cache (Stale)
Architectural Risk
Low. Official, stable API.
Medium. Ambiguous rate limits 1, known data gaps.2
High. Unofficial scraper.6 Breaks if MAL changes.
Data Source
Primary Database
Primary Database
MyAnimeList (Scraped)


Part 4: Source Capability Profile: Comic Vine API (Western Comics)


4.1 Resource Analysis: issue, volume, and series Schemas

The Comic Vine API's resources are a direct conceptual match for the ComicInfo.xml schema, split into issue(s), volume(s), and series/series_list.1 As the official documentation was inaccessible 24, the API's schema must be inferred from partial responses, user reports, and wrapper libraries.
Inferred issue Schema: id, name (the issue title), issue_number, cover_date (string), description (HTML), deck (a short summary), image (object with URLs), api_detail_url, has_staff_review, date_added, date_last_updated, volume (object), character_credits (array), person_credits (array).1
Inferred volume Schema: id, name, count_of_issues 25, series (object), description, publisher (object).5
Inferred series Schema: id, name (often aliased as seriesname), start_year, image, deck, site_detail_url, character_credits, team_credits, issues (array of issue objects), last_issue (object), publisher (object).26

4.2 "Scanner" Capability: Search and Filter Functionality

The API provides robust search capabilities necessary for a scanner. A dedicated /search resource can query across multiple resource types.14
More importantly for a scanner, each plural resource endpoint (e.g., /characters/, /issues/) supports filtering. A scanner can filter by field values (e.g., filter=name:Cain,gender:Female).18 This allows for targeted lookups.
The API also supports a field_list parameter, which allows the client to specify which fields to return.1 This is a critical optimization for a bulk scanner, as it dramatically reduces response payload size and network latency.

4.3 Critical Gaps and Missing Data (The "Format" and "Pages" Problem)

This is the most significant finding regarding the Comic Vine API. Despite being the "correct" source for Western comics, it is incapable of fully populating the ComicInfo.xml schema. Multiple user reports confirm that the API lacks key bibliographic fields required by collectors.2
The "Format" Void: A detailed user analysis concludes that the format field (e.g., "TPB", "Hardcover", "Digital", "One-Shot") does not exist in the API's issue or volume response.5 This is a major data void, as the ComicInfo.xml schema requires this field.
The "Pages" Void: Users also cite pages (page count) and reprint information as missing from the API.2
The inescapable conclusion is that the Western-focused API (Comic Vine) cannot fully populate the Western-focused metadata schema (ComicInfo.xml). This is a significant, counter-intuitive limitation that the scanner's developer must accept. The scanner will have "N/A" fields when using Comic Vine.

Part 5: Source Capability Profile: AniList API (Manga)


5.1 Resource Analysis: The GraphQL Media Type Schema

The primary resource for manga on AniList is the Media object, which is queried with the argument type: MANGA.4 While the official reference docs were inaccessible 30, the schema is richly detailed in other explored documentation.
Inferred Media Schema (for Manga):
Identifiers: id (AniList ID), idMal (MyAnimeList ID, for cross-reference).
Titles: title (object: english, romaji, native).
Publication Data: status (enum: FINISHED, RELEASING, etc.), startDate (FuzzyDate object), endDate (FuzzyDate object).
Content: description (HTML), format (enum: MANGA, NOVEL, ONE_SHOT), chapters (int), volumes (int).
Descriptors: genres (array of strings), tags (array of tag objects), isAdult (boolean).
Metrics: averageScore, popularity, trending.
Media: coverImage (object: large, medium, color), bannerImage.
Relational Data: staff (connection), characters (connection), relations (connection).4

5.2 "Scanner" Capability: GraphQL Query and Search Efficacy

The search and filter capability, exposed via GraphQL arguments on the Media query, is exceptionally powerful.4 A scanner can search by a wide array of fields, including id, idMal, search (a title string), startDate, format, status, chapters, volumes, genre, tag, and source.4 The ability to query idMal_in: [array] provides a powerful bulk-lookup feature for cross-referencing.32

5.3 Leveraging Relational Data: staff, characters, and relations

The true power of AniList for a scanner lies in its graph structure. Because it is a GraphQL API, a single query can ask for a Media object and, within that same request, retrieve its associated (or "connected") data.
A well-formed query can fetch a manga and:
Its staff connection, including each person's role ("Story", "Art", etc.).
Its characters connection, with the main and supporting characters.
Its relations connection, which lists prequels, sequels, spin-offs, and adaptations.
This allows a scanner to be incredibly efficient. In one call, it receives the data to populate Title, Summary, Genre, Characters, Writer (from staff), Penciller (from staff), and can even use the relations data to logically populate the ComicInfo.xml StoryArc or SeriesGroup fields. This is a level of data richness and query efficiency that the REST APIs cannot match.

Part 6: Source Capability Profile: Jikan API (Manga)


6.1 Resource Analysis: /manga/{id} and /manga (search) Schemas

Jikan is an unofficial MyAnimeList (MAL) scraper that provides a RESTful API.6 Its data, therefore, is a direct reflection of what is available on the MyAnimeList website.
Inferred /manga (search) Schema: The search response contains a data array. Each object in the array represents a manga and contains fields like: title, title_japanese, synopsis, type, images.jpg.image_url, chapters, volumes, status, score, and published (a date object).35
Inferred /manga/{id} (detail) Schema: The detail view for a single manga adds more comprehensive data, including: title, year, synopsis, genres (array), themes (array), authors (array with roles), serializations (array), and related (object).20

6.2 "Scanner" Capability: Search Filters and Retrieval

For a REST API, Jikan's search capabilities are excellent. The v4 /manga (search) endpoint provides granular filtering.37 A scanner can filter by:
q: The query string.
type: manga, novel, oneshot, doujin, manhwa, manhua.
status: publishing, completed, upcoming.
genre: By one or more genre IDs.
score: By numerical score.
magazine: By magazine ID.
order_by: (e.g., title, score, chapters).
This is a very strong, competitive feature set, allowing a scanner to perform highly specific lookups.

6.3 Architectural Risk Analysis: The "Wrapper" Dependency

Jikan's defining feature is also its greatest liability: it is not a primary data source.6
Risk 1: Cascading Failure: Jikan's parsers scrape the HTML of MyAnimeList.net.6 If MyAnimeList changes its website layout, Jikan's parsers will break. The scanner application will then fail until the Jikan development team fixes and deploys an update. This introduces a volatile, external dependency.
Risk 2: Cascading Rate Limits: Jikan is, itself, a client of MAL. It is possible for Jikan as a service to be rate-limited or blocked by MAL. These errors are then passed to the scanner as 429 or 503 errors.7
Risk 3: Stale Data: As noted in Part 3.3, the 24-hour mandatory cache 7 is an unacceptable liability for data freshness.
Architect's Conclusion: Jikan is a high-risk, strategically poor choice for a new, production-grade scanner when AniList exists. Its only virtue—the minor development simplicity of REST vs. GraphQL/OAuth—is vastly outweighed by the severe, long-term risks to stability and data integrity.

Part 7: The Definitive Field-Mapping Matrix

The following tables synthesize the analysis from Parts 1-6 to provide a definitive mapping and gap analysis for a scanner application.

Table: ComicInfo.xml Core Schema Definition

This table defines the target schema, derived from schema documentation 11 and the Go comicinfo struct.8
ComicInfo.xml Field
Data Type (Go)
Description
Title
string
Title of the book/issue.
Series
string
Title of the series the book is part of.
Number
string
Number of the book in the series.
Count
int
The total number of books in the series.
Volume
int
Volume containing the book (US-specific concept).
Summary
string
A description or summary of the book.
Year
int
Release year.
Month
int
Release month.
Day
int
Release day.
Writer
string
Person responsible for the scenario.
Penciller
string
Person responsible for drawing the art.
Inker
string
Person responsible for inking the pencil art.
Colorist
string
Person responsible for applying color.
Letterer
string
Person responsible for drawing text/bubbles.
CoverArtist
string
Person responsible for drawing the cover art.
Publisher
string
Publisher of the book.
Genre
string
Genre(s) (comma-separated).
Web
string
A URL.
PageCount
int
Total number of pages.
Format
string
e.g., "TPB", "Hardcover", "Digital".
Manga
Manga (enum)
"Yes", "No", "YesAndRightToLeft".
Characters
string
Character(s) (comma-separated).
StoryArc
string
The story arc the book is part of.
Pages
Pages (struct)
Scanner-Generated Only.


Table: The Master Metadata Mapping Matrix

This matrix provides the "best-fit" mapping from each API to the ComicInfo.xml target schema.

ComicInfo.xml Field
Comic Vine API (Western)
AniList API (Manga)
Jikan API (Manga)
Title
issue.name
Media.title.english or romaji
data.title
Series
issue.volume.series.name
Media.title.romaji or english
data.title
Number
issue.issue_number
Media.chapters (Not 1:1)
data.chapters (Not 1:1)
Volume
issue.volume.name (or int from name)
Media.volumes
data.volumes
Count
issue.volume.count_of_issues
Media.volumes (or chapters)
data.volumes (or chapters)
Summary
issue.description or issue.deck
Media.description
data.synopsis
Year
issue.cover_date (parse)
Media.startDate.year
data.published.from (parse)
Month
issue.cover_date (parse)
Media.startDate.month
data.published.from (parse)
Day
issue.cover_date (parse)
Media.startDate.day
data.published.from (parse)
Publisher
issue.volume.series.publisher.name
Media.staff (role: "Publisher")
data.serializations.name (array)
Genre
N/A (Not in inferred schema)
Media.genres (array)
data.genres (array)
Web
issue.site_detail_url
Media.siteUrl
data.url (MAL URL)
PageCount
N/A 2
N/A (Bibliographic)
N/A (Bibliographic)
Format
N/A 2
Media.format
data.type
Characters
issue.character_credits (array)
Media.characters.nodes (array)
data.characters (array)
StoryArc
N/A (Not in inferred schema)
Media.relations (Needs logic)
data.related (Needs logic)
Writer
issue.person_credits (role: "writer")
Media.staff (role: "Story")
data.authors (role: "Story")
Penciller
issue.person_credits (role: "penciller")
(Lossy) Media.staff (role: "Art")
(Lossy) data.authors (role: "Art")
Inker
issue.person_credits (role: "inker")
(Lossy) Media.staff (role: "Art")
(Lossy) data.authors (role: "Art")
Colorist
issue.person_credits (role: "colorist")
(Lossy) Media.staff (role: "Coloring")
N/A (Likely not provided)
Pages
Scanner-Generated Only
Scanner-Generated Only
Scanner-Generated Only


7.4 Analysis of Gaps, Voids, and "Lossy" Mappings

The Master Mapping Matrix reveals several critical gaps and compromises.
The Comic Vine Voids: As shown in the matrix and corroborated by user reports 2, the Comic Vine API fails to provide Genre, PageCount, Format, and StoryArc. This is a significant data gap that the scanner developer must accept as a limitation.
The "Format" Paradox: The manga-focused APIs (AniList Media.format and Jikan data.type) can populate the Format field, whereas Comic Vine cannot.
The Creator Role "Lossy" Mapping: The matrix highlights that mapping manga creators is a "best-fit" exercise. AniList's generic "Art" role must be mapped to the specific Penciller and/or Inker fields. This is a semantically incorrect but necessary compromise to populate the schema.
The Number vs. chapters Mismatch: ComicInfo.xml Number refers to an issue number. Manga does not have "issues." The closest analogs are chapters or volumes. A scanner will have to decide on a logical mapping. Mapping Media.volumes to ComicInfo.Volume and Media.chapters to ComicInfo.Number is a potential, albeit confusing, strategy.
The PageCount and Pages Voids: No API can provide PageCount (an integer) or Pages (a complex struct). PageCount is missing from Comic Vine 2, and it is not a bibliographic field for manga. Pages is a local file manifest.8 Both must be generated locally by the scanner.

Part 8: Final Architectural Recommendations

Based on the preceding analysis, the following architectural strategy is recommended for a robust, scalable, and maintainable metadata scanner.

8.1 Recommendation 1: A Hybrid-Source Architecture

A single API cannot serve a mixed-media library. The system must be architected to route requests to different APIs based on the media type. The ComicInfo.xml Manga tag 8 should be used as the primary routing flag.

8.2 Recommendation 2: The Optimal Strategy for Western Comics

Use the Comic Vine API. It is the only viable, domain-appropriate source.
The application must implement a robust client-side rate limiter. A "trickle" queue (e.g., one request every 2-3 seconds) is recommended to respect the 200 req/resource/hour bulk limit and, more importantly, the "velocity detection" burst limit.1
The stakeholder must be notified, and the application's UI designed to handle, the known data voids. The application will not be able to fetch Format, PageCount, or Genre from this source.2

8.3 Recommendation 3: The Optimal Strategy for Manga

Use the AniList GraphQL API as the Primary Source.
Rationale: It is an official, stable, modern API.4 Its data is live (avoiding Jikan's 24-hour staleness 7). Its GraphQL relations and staff connections provide richer data (for StoryArc and creator roles) in a single, efficient call.4 The 90 req/min limit is generous and professionally managed.21
The one-time development cost of implementing GraphQL and OAuth2 15 is a sound, necessary long-term investment in application stability and data integrity.
Reject Jikan: Do not build a production system on the Jikan API. Its status as an unofficial scraper 6 and its 24-hour data staleness 7 make it an unacceptably high-risk dependency for a core application feature.

8.4 A Proposed "Scanner" Logic Flow

Detect File: Scanner identifies a new file (e.g., Batman (2016) - 001.cbz or [Author] One-Punch Man - v01.cbz).
Check Local: Check for an existing ComicInfo.xml within the archive.
Establish Route:
If ComicInfo.xml exists, read the Manga tag. This is the definitive route.
If no XML exists, perform a heuristic guess. Parse the filename. If it contains manga-specific keywords ("v01", "[Author]", or matches a known manga SeriesGroup), set route to Manga=Yes.
Otherwise, default route to Manga=No.
API Routing & Mapping:
If Route is Manga=Yes:
Query AniList API: query { Media(search: "One-Punch Man", type: MANGA) {... } }
Map Response: Use the "AniList" column from the Master Mapping Matrix (Part 7).
Apply "Lossy" Logic: Map Media.staff (role: "Art") to ComicInfo.Penciller.
If Route is Manga=No:
Query Comic Vine API: GET /search/?api_key=...&resources=issue&query=Batman 2016 1 (implementing throttle).
Map Response: Use the "Comic Vine" column from the Master Mapping Matrix (Part 7).
Accept Voids: Accept "N/A" for Format, PageCount, Genre.
Generate Local Data (Critical Step):
After API mapping, open the physical file (e.g., .cbz).
Iterate through all image files.
Count the images and update/overwrite the PageCount field.
Generate the Pages array 8, populating Image index, ImageSize, ImageWidth, ImageHeight, and Type (e.g., page 0 is "FrontCover," others are "Story").
Write File: Save the newly created/updated ComicInfo.xml object back into the comic archive.
Works cited
Comic Vine API – Part 1 – Basics - Joseph E Phillips, accessed on November 14, 2025, https://josephephillips.com/blog/how-to-use-comic-vine-api-part1
We have the program, now let's get the DB... : r/comicrackusers - Reddit, accessed on November 14, 2025, https://www.reddit.com/r/comicrackusers/comments/19emohq/we_have_the_program_now_lets_get_the_db/
AniList Api v2 GraphQL Docs download | SourceForge.net, accessed on November 14, 2025, https://sourceforge.net/projects/anilist-api-v2-graphql.mirror/
AniList/docs: AniList API documentation - GitHub, accessed on November 14, 2025, https://github.com/AniList/docs
Why doesn't the Comic Vine scraper add pull down the "FORMAT" information into the issue? : r/comicrackusers - Reddit, accessed on November 14, 2025, https://www.reddit.com/r/comicrackusers/comments/y7j4fu/why_doesnt_the_comic_vine_scraper_add_pull_down/
jikan-me/jikan-rest: The REST API for Jikan - GitHub, accessed on November 14, 2025, https://github.com/jikan-me/jikan-rest
Jikan REST API v4 Docs, accessed on November 14, 2025, https://docs.api.jikan.moe/
comicinfo package - github.com/fmartingr/go-comicinfo/v2 - Go ..., accessed on November 14, 2025, https://pkg.go.dev/github.com/fmartingr/go-comicinfo/v2
ComicInfo.xml's new home - GitHub, accessed on November 14, 2025, https://github.com/anansi-project/comicinfo
ComicRack's ComicInfo.xml - The Anansi Project, accessed on November 14, 2025, https://anansi-project.github.io/docs/comicinfo/intro
documentation | The Anansi Project, accessed on November 14, 2025, https://anansi-project.github.io/docs/comicinfo/documentation
Anilist Anime Dataset - Kaggle, accessed on November 14, 2025, https://www.kaggle.com/datasets/calebmwelsh/anilist-anime-dataset
Getting data from Anilist.co for analysis (Part 1): Building a query using GraphiQL. - Medium, accessed on November 14, 2025, https://medium.com/@jonathan.roman1213/getting-data-from-anilist-co-for-analysis-part-1-building-a-query-using-graphiql-10b7d6d2e350
Comic Vine - Public APIs, accessed on November 14, 2025, https://publicapis.io/comic-vine-api
anilist_moe - crates.io: Rust Package Registry, accessed on November 14, 2025, https://crates.io/crates/anilist_moe/0.2.1
AniList MCP Server - LobeHub, accessed on November 14, 2025, https://lobehub.com/mcp/yuna0x0-anilist-mcp
AniList API — Free Public API | Public APIs Directory, accessed on November 14, 2025, https://publicapis.io/ani-list-api
mattleibow/ComicVineApi: A beautiful .NET API that wraps ... - GitHub, accessed on November 14, 2025, https://github.com/mattleibow/ComicVineApi
Behind the Scenes: Exploring the Technology of Jikan API - DhiWise, accessed on November 14, 2025, https://www.dhiwise.com/post/behind-the-scenes-exploring-the-technology-of-jikan-api
Upgrade to V4 · Apiary, accessed on November 14, 2025, https://jikan.docs.apiary.io/
Rate Limiting | AniList APIv2 Docs - GitBook, accessed on November 14, 2025, https://anilist.gitbook.io/anilist-apiv2-docs/docs/guide/rate-limiting
Releases · AniList/ApiV2-GraphQL-Docs - GitHub, accessed on November 14, 2025, https://github.com/AniList/ApiV2-GraphQL-Docs/releases
A JS/TS client for the Comic Vine API - GitHub, accessed on November 14, 2025, https://github.com/AllyMurray/comic-vine
accessed on January 1, 1970, http://comicvine.gamespot.com/api/documentation
New script to get a volumes issue count from ComicVine : r/comicrackusers - Reddit, accessed on November 14, 2025, https://www.reddit.com/r/comicrackusers/comments/uv5jzu/new_script_to_get_a_volumes_issue_count_from/
swc/comicvine_api: Simple to use Comic Vine (comicvine.com) API in Python. Modified from http://github.com/dbr/tvdb_api - GitHub, accessed on November 14, 2025, https://github.com/swc/comicvine_api
Comic Vine API - PublicAPI, accessed on November 14, 2025, https://publicapi.dev/comic-vine-api
Comic Vine API – Part 2 – Advanced Filters - Joseph E Phillips, accessed on November 14, 2025, https://josephephillips.com/blog/how-to-use-comic-vine-api-part2
Anilist api v2 GRAPHQL - Stack Overflow, accessed on November 14, 2025, https://stackoverflow.com/questions/51924820/anilist-api-v2-graphql
accessed on January 1, 1970, https://studio.apollographql.com/sandbox/explorer?endpoint=https%3A%2F%2Fgraphql.anilist.co
accessed on January 1, 1970, https://anilist.github.io/ApiV2-GraphQL-Docs/
How to Query Multiple Media Items by MyAnimeList IDs Using Anilist's GraphQL API? - Stack Overflow, accessed on November 14, 2025, https://stackoverflow.com/questions/78879836/how-to-query-multiple-media-items-by-myanimelist-ids-using-anilists-graphql-api
Modifying existent code to get search results from API - Stack Overflow, accessed on November 14, 2025, https://stackoverflow.com/questions/53824463/modifying-existent-code-to-get-search-results-from-api
Jikan - Unofficial MyAnimeList API, accessed on November 14, 2025, https://jikan.moe/
Display all anime data [Jikan.moe API v4] [closed] - Stack Overflow, accessed on November 14, 2025, https://stackoverflow.com/questions/74813631/display-all-anime-data-jikan-moe-api-v4
How to Use APIs – Real Example with Jikan & Bruno! - YouTube, accessed on November 14, 2025, https://www.youtube.com/watch?v=-93PBcntHvo
Jikan® - Unofficial MyAnimeList API - RapidAPI, accessed on November 14, 2025, https://rapidapi.com/theapiguy/api/jikan1
