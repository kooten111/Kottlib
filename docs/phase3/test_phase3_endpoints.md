# Phase 3 Endpoint Testing Guide

## Favorites Endpoints

### Get Favorites
```bash
curl http://localhost:8080/v2/library/1/favs
```

Expected: JSON array of favorite comics

### Add to Favorites
```bash
curl -X POST http://localhost:8080/v2/library/1/comic/5/fav
```

Expected: `{"success": true}`

### Remove from Favorites
```bash
curl -X DELETE http://localhost:8080/v2/library/1/comic/5/fav
```

Expected: `{"success": true}` or `{"success": false}`

---

## Labels/Tags Endpoints

### Get All Labels
```bash
curl http://localhost:8080/v2/library/1/tags
```

Expected: JSON array of labels

### Get Label Info
```bash
curl http://localhost:8080/v2/library/1/tag/1/info
```

Expected: JSON object with label details

### Get Comics with Label
```bash
curl http://localhost:8080/v2/library/1/tag/1/content
```

Expected: JSON array of comics

### Create Label
```bash
curl -X POST http://localhost:8080/v2/library/1/tag \
  -H "Content-Type: text/plain" \
  -d "name:To Read
color_id:1"
```

Expected: JSON object with created label

### Delete Label
```bash
curl -X DELETE http://localhost:8080/v2/library/1/tag/1
```

Expected: `{"success": true}`

### Add Label to Comic
```bash
curl -X POST http://localhost:8080/v2/library/1/comic/5/tag/1
```

Expected: `{"success": true}`

### Remove Label from Comic
```bash
curl -X DELETE http://localhost:8080/v2/library/1/comic/5/tag/1
```

Expected: `{"success": true}`

---

## Reading Lists Endpoints

### Get All Reading Lists
```bash
curl http://localhost:8080/v2/library/1/reading_lists
```

Expected: JSON array of reading lists

### Get Reading List Info
```bash
curl http://localhost:8080/v2/library/1/reading_list/1/info
```

Expected: JSON object with reading list details

### Get Comics in Reading List
```bash
curl http://localhost:8080/v2/library/1/reading_list/1/content
```

Expected: JSON array of comics (ordered by position)

### Create Reading List
```bash
curl -X POST http://localhost:8080/v2/library/1/reading_list \
  -H "Content-Type: text/plain" \
  -d "name:Marvel Event: Civil War
description:Complete Civil War reading order
is_public:true"
```

Expected: JSON object with created reading list

### Delete Reading List
```bash
curl -X DELETE http://localhost:8080/v2/library/1/reading_list/1
```

Expected: `{"success": true}`

### Add Comic to Reading List
```bash
curl -X POST http://localhost:8080/v2/library/1/reading_list/1/comic/5
```

Expected: `{"success": true}`

### Remove Comic from Reading List
```bash
curl -X DELETE http://localhost:8080/v2/library/1/reading_list/1/comic/5
```

Expected: `{"success": true}`

---

## Summary of New Endpoints

### Favorites (3 endpoints)
- `GET /v2/library/{id}/favs` - Get favorites
- `POST /v2/library/{id}/comic/{id}/fav` - Add to favorites
- `DELETE /v2/library/{id}/comic/{id}/fav` - Remove from favorites

### Labels/Tags (7 endpoints)
- `GET /v2/library/{id}/tags` - Get all labels
- `GET /v2/library/{id}/tag/{id}/info` - Get label info
- `GET /v2/library/{id}/tag/{id}/content` - Get comics with label
- `POST /v2/library/{id}/tag` - Create label
- `DELETE /v2/library/{id}/tag/{id}` - Delete label
- `POST /v2/library/{id}/comic/{id}/tag/{id}` - Add label to comic
- `DELETE /v2/library/{id}/comic/{id}/tag/{id}` - Remove label from comic

### Reading Lists (7 endpoints)
- `GET /v2/library/{id}/reading_lists` - Get all reading lists
- `GET /v2/library/{id}/reading_list/{id}/info` - Get reading list info
- `GET /v2/library/{id}/reading_list/{id}/content` - Get comics in list
- `POST /v2/library/{id}/reading_list` - Create reading list
- `DELETE /v2/library/{id}/reading_list/{id}` - Delete reading list
- `POST /v2/library/{id}/reading_list/{id}/comic/{id}` - Add comic to list
- `DELETE /v2/library/{id}/reading_list/{id}/comic/{id}` - Remove comic from list

**Total: 17 new endpoints**
