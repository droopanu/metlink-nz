"""Tests for the sensor module."""
# Copyright 2021 Jason Rumney
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp import ClientResponseError
import homeassistant.util.dt as dt_util

from custom_components.metlink.const import (
    ATTRIBUTION,
    CONF_DEST,
    CONF_NUM_DEPARTURES,
    CONF_ROUTE,
    CONF_STOP_ID,
)
from datetime import timedelta

from custom_components.metlink.MetlinkAPI import MetlinkRateLimited
from custom_components.metlink.sensor import MetlinkSensor, parse_route_filters, slug

TEST_RESPONSE = [
    {
        "farezone": "1",
        "closed": False,
        "departures": [
            {
                "stop_id": "WELL",
                "service_id": "HVL",
                "direction": "outbound",
                "operator": "RAIL",
                "origin": {"stop_id": "WELL", "name": "WgtnStn"},
                "destination": {"stop_id": "UPPE", "name": "UPPE-All stops"},
                "delay": "PT2M",
                "vehicle_id": None,
                "name": "WgtnStn",
                "arrival": {"expected": None},
                "departure": {
                    "aimed": "2021-04-29T21:35:00+12:00",
                    "expected": "2021-04-29T21:37:00+12:00",
                },
                "status": "delay",
                "monitored": False,
                "wheelchair_accessible": False,
            },
            {
                "stop_id": "WELL",
                "service_id": "KPL",
                "direction": "outbound",
                "operator": "RAIL",
                "origin": {"stop_id": "WELL", "name": "WgtnStn"},
                "destination": {"stop_id": "WAIK", "name": "WAIK-All stops"},
                "delay": "PT0S",
                "vehicle_id": None,
                "name": "WgtnStn",
                "arrival": {"expected": None},
                "departure": {
                    "aimed": "2021-04-29T21:44:00+12:00",
                    "expected": None,
                },
                "status": None,
                "monitored": False,
                "wheelchair_accessible": False,
            },
            {
                "stop_id": "WELL",
                "service_id": "KPL",
                "direction": "outbound",
                "operator": "RAIL",
                "origin": {"stop_id": "WELL", "name": "WgtnStn"},
                "destination": {"stop_id": "PORI", "name": "Porirua"},
                "delay": "PT0S",
                "vehicle_id": None,
                "name": "WgtnStn",
                "arrival": {"expected": None},
                "departure": {
                    "aimed": "2021-04-29T21:55:00+12:00",
                    "expected": None,
                },
                "status": None,
                "monitored": False,
                "wheelchair_accessible": False,
            },
            {
                "stop_id": "WELL",
                "service_id": "KPL",
                "direction": "outbound",
                "operator": "RAIL",
                "origin": {"stop_id": "WELL", "name": "WgtnStn"},
                "destination": {"stop_id": "PORI", "name": "Porirua"},
                "delay": "PT30M34S",
                "vehicle_id": None,
                "name": "WgtnStn",
                "arrival": {"expected": None},
                "departure": {
                    "aimed": "2021-04-29T22:15:00+12:00",
                    "expected": "2021-04-29T22:45:34+12:00",
                },
                "status": "late",
                "monitored": False,
                "wheelchair_accessible": False,
            },
        ],
    }
]


async def test_async_update_success(hass, aioclient_mock):
    """Tests a fully successful async_update."""
    metlink = MagicMock()
    metlink.get_predictions = AsyncMock(side_effect=TEST_RESPONSE)
    metlink.get_service_alerts = AsyncMock(return_value={"entity": []})
    sensor = MetlinkSensor(
        metlink,
        {CONF_STOP_ID: "WELL", CONF_ROUTE: "KPL", CONF_DEST: "Porirua"},
    )
    await sensor.async_update()

    expected = {
        "attribution": ATTRIBUTION,
        "stop_id": "WELL",
        "departure": "2021-04-29T21:55:00+12:00",
        "description": "KPL Porirua",
        "service_id": "KPL",
        "stop_name": "WgtnStn",
        "status": "sched",
        "destination_id": "PORI",
        "destination": "Porirua",
        "delay": 0,
        "wheelchair_accessible": False,
        "monitored": False,
        "vehicle_id": None,
        "alert_count": 0,
    }

    assert expected == sensor.attrs
    assert expected == sensor.extra_state_attributes
    assert sensor.available is True
    assert sensor.icon == "mdi:train"
    assert sensor.name == "Metlink WELL"
    assert sensor.unique_id == "metlink_WELL_rKPL_dPorirua"
    assert sensor.state == dt_util.parse_datetime(expected["departure"])


async def test_async_update_failed():
    """Tests a failed async_update."""
    metlink = MagicMock()
    metlink.get_service_alerts = AsyncMock(return_value={"entity": []})
    metlink.get_predictions = AsyncMock(
        side_effect=ClientResponseError(request_info="dummy", history="")
    )

    sensor = MetlinkSensor(metlink, {"stop_id": "WELL"})
    await sensor.async_update()

    assert sensor.available is False
    assert {"attribution": ATTRIBUTION, "stop_id": "WELL"} == sensor.attrs


async def test_async_update_misformatted():
    """Tests a misformatted async_update."""
    metlink = MagicMock()
    metlink.get_service_alerts = AsyncMock(return_value={"entity": []})
    metlink.get_predictions = AsyncMock(side_effect=TypeError("Test error handling"))

    sensor = MetlinkSensor(metlink, {"stop_id": "WELL"})
    await sensor.async_update()

    assert sensor.available is False
    assert {"attribution": ATTRIBUTION, "stop_id": "WELL"} == sensor.attrs


async def test_async_update_multiple(hass, aioclient_mock):
    """Tests a fully successful async_update."""
    metlink = MagicMock()
    metlink.get_predictions = AsyncMock(side_effect=TEST_RESPONSE)
    metlink.get_service_alerts = AsyncMock(return_value={"entity": []})
    sensor = MetlinkSensor(
        metlink,
        {CONF_STOP_ID: "WELL", CONF_ROUTE: "KPL", CONF_NUM_DEPARTURES: 4},
    )
    await sensor.async_update()

    expected = {
        "attribution": ATTRIBUTION,
        "stop_id": "WELL",
        "departure": "2021-04-29T21:44:00+12:00",
        "description": "KPL WAIK-All stops",
        "service_id": "KPL",
        "stop_name": "WgtnStn",
        "status": "sched",
        "destination_id": "WAIK",
        "destination": "WAIK-All stops",
        "delay": 0,
        "wheelchair_accessible": False,
        "monitored": False,
        "vehicle_id": None,
        "alert_count": 0,
        "departure_2": "2021-04-29T21:55:00+12:00",
        "description_2": "KPL Porirua",
        "service_id_2": "KPL",
        "status_2": "sched",
        "destination_id_2": "PORI",
        "destination_2": "Porirua",
        "delay_2": 0,
        "wheelchair_accessible_2": False,
        "monitored_2": False,
        "vehicle_id_2": None,
        "alert_count_2": 0,
        "departure_3": "2021-04-29T22:45:34+12:00",
        "description_3": "KPL Porirua",
        "service_id_3": "KPL",
        "status_3": "late",
        "destination_id_3": "PORI",
        "destination_3": "Porirua",
        "delay_3": 30,
        "wheelchair_accessible_3": False,
        "monitored_3": False,
        "vehicle_id_3": None,
        "alert_count_3": 0,
    }

    assert expected == sensor.attrs
    assert expected == sensor.extra_state_attributes
    assert sensor.available is True
    assert sensor.icon == "mdi:train"
    assert sensor.name == "Metlink WELL"
    assert sensor.unique_id == "metlink_WELL_rKPL"
    assert sensor.state == dt_util.parse_datetime(expected["departure"])


async def test_async_update_multiple_route_filter(hass, aioclient_mock):
    """Tests that comma-separated route filters are supported."""
    metlink = MagicMock()
    metlink.get_predictions = AsyncMock(side_effect=TEST_RESPONSE)
    metlink.get_service_alerts = AsyncMock(return_value={"entity": []})
    sensor = MetlinkSensor(
        metlink,
        {CONF_STOP_ID: "WELL", CONF_ROUTE: " KPL, HVL ", CONF_NUM_DEPARTURES: 1},
    )
    await sensor.async_update()

    assert sensor.available is True
    assert sensor.attrs["service_id"] == "HVL"
    assert sensor.attrs["description"] == "HVL UPPE-All stops"


def test_parse_route_filters():
    """Test route filter parser for comma-separated values."""
    assert parse_route_filters(None) == set()
    assert parse_route_filters("") == set()
    assert parse_route_filters("KPL") == {"KPL"}
    assert parse_route_filters(" KPL, HVL ,, ") == {"KPL", "HVL"}


def test_slug():
    """Test the slug function"""
    assert "abc_def" == slug("abc def")
    assert "_abc_def_ghi" == slug(" abc'def?ghi")


async def test_rate_limited_sensor_backs_off():
    """A rate-limited sensor makes no request until the back-off ends."""
    retry_at = dt_util.utcnow() + timedelta(minutes=2)
    metlink = MagicMock()
    metlink.get_predictions = AsyncMock(side_effect=MetlinkRateLimited(retry_at))
    metlink.get_service_alerts = AsyncMock(return_value={"entity": []})
    sensor = MetlinkSensor(metlink, {CONF_STOP_ID: "WELL"})
    await sensor.async_update()

    assert sensor.available is False
    assert sensor.retry_at == retry_at
    # A forced update before retry_at must not reach the API, whatever the
    # normal polling schedule says.
    sensor.update_time = sensor.update_time - timedelta(days=1)
    await sensor.async_update()
    assert metlink.get_predictions.call_count == 1


async def test_alerts_failure_keeps_departures(hass, aioclient_mock):
    """Departures are still published when service alerts cannot be fetched."""
    metlink = MagicMock()
    metlink.get_predictions = AsyncMock(side_effect=TEST_RESPONSE)
    metlink.get_service_alerts = AsyncMock(side_effect=ValueError("bad alerts"))
    sensor = MetlinkSensor(metlink, {CONF_STOP_ID: "WELL", CONF_ROUTE: "KPL"})
    await sensor.async_update()

    assert sensor.available is True
    assert sensor.attrs["departure"] == "2021-04-29T21:44:00+12:00"
    assert sensor.attrs["alert_count"] == 0


def _fast_sensor(hass, departures_at, control_state="on"):
    """A sensor whose next departure is `departures_at`, with fast polling."""
    response = {
        "departures": [
            dict(
                TEST_RESPONSE[0]["departures"][0],
                departure={"aimed": departures_at.isoformat(), "expected": None},
            )
        ]
    }
    metlink = MagicMock()
    metlink.get_predictions = AsyncMock(return_value=response)
    metlink.get_service_alerts = AsyncMock(return_value={"entity": []})
    sensor = MetlinkSensor(
        metlink,
        {CONF_STOP_ID: "WELL"},
        {"fast_poll_entity": "input_boolean.commute", "fast_poll_seconds": 60},
    )
    sensor.hass = hass
    if control_state is not None:
        hass.states.async_set("input_boolean.commute", control_state)
    return sensor, metlink


async def _two_updates(sensor, seconds_later):
    await sensor.async_update()
    later = dt_util.utcnow() + timedelta(seconds=seconds_later)
    with patch("homeassistant.util.dt.utcnow", return_value=later):
        await sensor.async_update()


async def test_fast_poll_overrides_hold(hass):
    """While the control entity is on, a departure in the window refreshes early."""
    # 16 minutes away: the normal schedule would hold polling for 2 minutes.
    sensor, metlink = _fast_sensor(hass, dt_util.now() + timedelta(minutes=16))
    await _two_updates(sensor, 61)
    assert metlink.get_predictions.call_count == 2


async def test_fast_poll_respects_interval(hass):
    """Fast polling still waits for the fast interval between fetches."""
    sensor, metlink = _fast_sensor(hass, dt_util.now() + timedelta(minutes=16))
    await _two_updates(sensor, 30)
    assert metlink.get_predictions.call_count == 1


async def test_fast_poll_off_keeps_schedule(hass):
    """With the control entity off the normal schedule applies."""
    sensor, metlink = _fast_sensor(hass, dt_util.now() + timedelta(minutes=16), "off")
    await _two_updates(sensor, 61)
    assert metlink.get_predictions.call_count == 1


async def test_fast_poll_missing_entity_is_off(hass):
    """A missing or unavailable control entity never enables fast polling."""
    sensor, metlink = _fast_sensor(
        hass, dt_util.now() + timedelta(minutes=16), control_state=None
    )
    await _two_updates(sensor, 61)
    hass.states.async_set("input_boolean.commute", "unavailable")
    await _two_updates(sensor, 61)
    assert metlink.get_predictions.call_count == 1


async def test_fast_poll_outside_window(hass):
    """Departures beyond the window keep the normal schedule."""
    sensor, metlink = _fast_sensor(hass, dt_util.now() + timedelta(minutes=45))
    await _two_updates(sensor, 61)
    assert metlink.get_predictions.call_count == 1


async def test_backoff_beats_fast_poll(hass):
    """An API back-off is honoured even when fast polling is due."""
    sensor, metlink = _fast_sensor(hass, dt_util.now() + timedelta(minutes=16))
    await sensor.async_update()
    sensor.retry_at = dt_util.now() + timedelta(minutes=5)
    later = dt_util.utcnow() + timedelta(seconds=61)
    with patch("homeassistant.util.dt.utcnow", return_value=later):
        await sensor.async_update()
    assert metlink.get_predictions.call_count == 1
