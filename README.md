# F1 Backend

A lightweight FastAPI backend that provides Formula 1 season, race weekend, and session data.

The backend uses the public OpenF1 API as its main data source and enriches race weekend information with country metadata and flag data. Redis is used to cache frequently requested data.

## API Overview

The API currently provides three main endpoint groups:

1. Available Formula 1 seasons
2. Race weekends for a selected season
3. Sessions for a selected race weekend

Base URL during local development:

```text
http://localhost:8000
```

## Endpoints

### Get all available seasons

```http
GET /seasons/
```

Returns all Formula 1 seasons for which OpenF1 provides session data.

#### Example request

```bash
curl http://localhost:8000/seasons/
```

#### Example response

```json
[
  2023,
  2024,
  2025,
  2026
]
```

#### Response fields

| Field | Type | Description |
| --- | --- | --- |
| `[]` | `number[]` | A sorted list of available season years. |

---

### Get race weekends for a season

```http
GET /seasons/{season}/weekends/
```

Returns all race weekends for a specific Formula 1 season.

#### Path parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `season` | `integer` | yes | The season year, for example `2024`. |

#### Response fields

| Field | Type | Description |
| --- | --- | --- |
| `name` | `string` | Name of the race weekend. |
| `id` | `integer` | OpenF1 meeting key. This value is used as `weekend_id` for the sessions endpoint. |
| `country` | `object \| null` | Country metadata for the race weekend. Can be `null` if country enrichment fails. |
| `country.id` | `integer` | Numeric country code. |
| `country.name` | `string` | English country name. |
| `country.name_de` | `string` | German country name. |
| `country.alpha3_code` | `string` | ISO 3166-1 alpha-3 country code. |
| `country.subregion` | `string` | Country subregion. |
| `country.region` | `string` | Country region. |
| `country.flag_base64` | `string` | Base64-encoded SVG flag. |
| `circuit_id` | `integer` | OpenF1 circuit key. |
| `date_start` | `string` | Start date and time of the weekend in ISO 8601 format. |
| `date_end` | `string` | End date and time of the weekend in ISO 8601 format. |
| `gmt_offset` | `string` | Local GMT offset of the event. |
| `cancelled` | `boolean` | Indicates whether the race weekend was cancelled. |

---

### Get sessions for a race weekend

```http
GET /weekend/{weekend_id}/sessions/
```

Returns all sessions for a specific race weekend.

A `weekend_id` can be obtained from the `/seasons/{season}/weekends/` endpoint. It corresponds to the OpenF1 `meeting_key`.

#### Path parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `weekend_id` | `integer` | yes | The race weekend / meeting ID. |

#### Response fields

| Field | Type | Description |
| --- | --- | --- |
| `id` | `integer` | OpenF1 session key. |
| `type` | `string` | Normalized session type. |
| `weekend_id` | `integer` | Related race weekend / meeting ID. |
| `start_time` | `string` | Session start time in ISO 8601 format. |

#### Possible session types

```text
practice_one
practice_two
practice_three
sprint
sprint_qualifying
qualifying
grand_prix
```

## Typical API Flow

A client usually uses the API in this order:

```text
GET /seasons/
        ↓
GET /seasons/{season}/weekends/
        ↓
GET /weekend/{weekend_id}/sessions/
```

## Upstream APIs

This backend uses:

- [OpenF1 API](https://openf1.org/)
- [REST Countries](https://restcountries.com/)
- [FlagCDN](https://flagcdn.com/)

OpenF1 requests are rate-limited internally to 3 requests per second and 30 requests per minute. REST Countries / flag requests are rate-limited to 2 requests per second.
