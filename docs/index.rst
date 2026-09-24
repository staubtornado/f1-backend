F1 Backend documentation
========================

The FastAPI backend retrieves Formula 1 data through OpenF1, converts it into
Pydantic response models and caches data in Redis. Country flags and driver
portraits are downloaded from the URLs provided by OpenF1 and encoded as base64.

.. toctree::
   :maxdepth: 2

   usage
   services
   api
   schemas

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
