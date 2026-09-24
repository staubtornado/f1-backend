Services and upstream client
============================

F1 service
----------

.. autoclass:: app.services.f1.F1Service
   :members:
   :private-members: _cached, _season_ttl
   :show-inheritance:

OpenF1 and Redis cache
----------------------

.. autoclass:: app.services.openf1.OpenF1
   :members:
   :private-members: _get_drivers, _with_driver_portrait, _get_meetings, _call_json, _get_image_base64, _call_content, _call, _get_retry_delay
   :show-inheritance:

.. autoclass:: app.services.openf1.RedisCache
   :members:
   :show-inheritance:
