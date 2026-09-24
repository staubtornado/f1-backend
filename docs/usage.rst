Usage and behavior
==================

Build this documentation
------------------------

From the backend directory, using an activated Python environment with Python
3.11 or newer:

.. code-block:: console

   python -m pip install -r requirements-docs.txt
   python -m sphinx -b html -W --keep-going docs docs/_build/html

Open ``docs/_build/html/index.html`` in a browser. The build imports the backend
modules to render their docstrings; it does not start FastAPI's lifespan or
require a running Redis server or OpenF1 connection. Runtime dependencies must
be installed because autodoc imports the actual models and services.

Start the API
-------------

Run Redis locally, or set ``REDIS_HOST`` to its hostname, then start the backend:

.. code-block:: console

   python -m uvicorn app.main:app --reload

The local base URL is ``http://localhost:8000``. FastAPI provides interactive
HTTP documentation at ``/docs`` and the OpenAPI schema at ``/openapi.json``.

Endpoints
---------

All endpoints use GET. Driver IDs are racing numbers; weekend IDs and session
IDs are OpenF1 meeting keys and session keys respectively.

.. list-table::
   :header-rows: 1
   :widths: 60 40

   * - Path
     - Response
   * - ``/seasons/``
     - Ascending season years
   * - ``/seasons/{season}/weekends/``
     - Weekends with country flags
   * - ``/weekend/{weekend_id}/sessions/``
     - Sessions, including testing days
   * - ``/session/{session_id}/result/``
     - Session classifications
   * - ``/seasons/{season}/drivers/{driver_id}/``
     - Driver profile and portrait
   * - ``/standings/{season}/driver_standings/``
     - Driver championship standings
   * - ``/standings/{season}/team_standings/``
     - Team championship standings
   * - ``/weekend/{weekend_id}/starting_grid/``
     - Grids associated with qualifying sessions
   * - ``/grand-prix/{session_id}/positions/``
     - Chronological position updates with driver profiles

Caching
-------

These lifetimes apply to the converted service responses:

.. list-table::
   :header-rows: 1

   * - Data
     - Lifetime
   * - Seasons, driver profiles, populated results and complete grids
     - One day
   * - Season weekends and populated championship standings
     - One week for past UTC years; one hour otherwise
   * - Weekend sessions
     - One week if every session started over two days ago; five minutes otherwise
   * - Position updates
     - 30 seconds, including empty results
   * - Other empty lists, empty standings/classifications or incomplete grids
     - 30 seconds

Raw meetings and driver records may also be cached by the OpenF1 client.
Images are cached for one week when a cache is attached. Missing image URLs
produce empty strings; failed downloads propagate an exception.
Per-key locks coordinate concurrent misses within a cache instance, not across
separate workers.

Selection and conversion details
--------------------------------

Driver standings use the latest started, non-cancelled session whose upstream
``session_type`` is Race or Sprint. Team standings inspect weekends by descending
start date and use the latest started Grand Prix in the first eligible weekend.
Neither selection requires the session to have finished.

Classifications retain upstream order. Their gap to the previous entry is a
duration difference, not a separately fetched track interval.
The conversion mutates the source dictionary's duration and leader-gap values;
see :meth:`app.schemas.classification.Classification.from_openf1` for details.

Country identifiers come from OpenF1's ``country_key``, not ISO numeric codes.
The country model contains ``id``, ``name``, ``alpha3_code`` and ``flag_base64``.
No REST Countries enrichment is performed. Weekend UTC offsets are timedeltas,
serialized by Pydantic as ISO 8601 durations. Championship points currently use
integer model fields; fractional values can fail validation.

Upstream requests and errors
----------------------------

Within each OpenF1 client, API attempts are paced at least 2.1 seconds apart.
HTTP 429 responses allow up to two retries and set a shared cooldown using
Retry-After or exponential backoff. Image downloads allow up to eight concurrent
requests; external image URLs bypass the OpenF1 API limiters.

HTTP status errors from upstream data or image requests retain their status,
body and Content-Type in the API response. Other upstream headers are not
forwarded. Missing season drivers produce HTTP 404; position records referring
to missing driver profiles produce HTTP 502. Validation, transport and Redis
errors are not converted by the upstream HTTP status error handler.
