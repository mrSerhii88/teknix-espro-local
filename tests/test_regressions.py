"""Offline regression tests. No MQTT connection or boiler commands are sent."""
from __future__ import annotations

import ast
import asyncio
import __future__
import importlib
import logging
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from datetime import timedelta

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "teknix_espro_local"
package = ModuleType("_teknix_under_test")
package.__path__ = [str(COMPONENT)]
sys.modules[package.__name__] = package
const = importlib.import_module(f"{package.__name__}.const")
protocol = importlib.import_module(f"{package.__name__}.protocol")


def definitions(filename, symbols, context):
    """Load actual pure functions/descriptions without importing Home Assistant."""
    tree = ast.parse((COMPONENT / filename).read_text())
    tree.body = [
        node for node in tree.body
        if (isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in symbols)
        or (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in symbols for t in node.targets))
        or (isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id in symbols)
    ]
    exec(compile(tree, filename, "exec", flags=__future__.annotations.compiler_flag), context)
    return context


def description(**kwargs):
    return SimpleNamespace(**kwargs)


class PowerTests(unittest.TestCase):
    def setUp(self):
        self.numbers = definitions("number.py", {"_identity", "_x10", "_relay_count", "NUMBERS"}, {
            "TeknixNumberDescription": description,
            "NumberDeviceClass": SimpleNamespace(TEMPERATURE="temperature"),
            "UnitOfPower": SimpleNamespace(KILO_WATT="kW"),
            "UnitOfTemperature": SimpleNamespace(CELSIUS="°C"),
            "EntityCategory": SimpleNamespace(CONFIG="config"),
            "NumberMode": SimpleNamespace(SLIDER="slider", AUTO="auto"),
        })
        self.sensors = definitions("sensor.py", {"_issue_date", "_error_code", "ERROR_CODES", "SENSORS"}, {
            "TeknixSensorDescription": description,
            "SensorDeviceClass": SimpleNamespace(TEMPERATURE="temperature", ENUM="enum"),
            "SensorStateClass": SimpleNamespace(MEASUREMENT="measurement"),
            "UnitOfPower": SimpleNamespace(KILO_WATT="kW"),
            "UnitOfTemperature": SimpleNamespace(CELSIUS="°C"),
            "EntityCategory": SimpleNamespace(DIAGNOSTIC="diagnostic"),
        })

    def test_all_six_stages_read_write_and_metadata(self):
        for item in self.numbers["NUMBERS"]:
            if item.field not in {"P4_MAX_POWER_HEAT", "P5_MAX_POWER_GVS"}:
                continue
            self.assertEqual((item.native_min_value, item.native_step, item.native_max_value), (2.5, 2.5, 15))
            for stage in range(1, 7):
                with self.subTest(field=item.field, stage=stage):
                    self.assertEqual(item.value_fn({item.field: stage}), stage * 2.5)
                    self.assertEqual(item.encode_fn(stage * 2.5), stage)
            for value in [0, -2.5, 1, 2, 3, 12, 15.1, 17.5, 25, float("nan"), float("inf")]:
                with self.subTest(field=item.field, rejected=value):
                    with self.assertRaises((ValueError, OverflowError)):
                        item.encode_fn(value)

    def test_priority_consumer_and_nameplate_power(self):
        items = {item.key: item for item in self.sensors["SENSORS"]}
        for stage in range(1, 7):
            self.assertEqual(items["p6_consumer_priority"].value_fn({"P6_CONSUMER_PRIORITY": stage}), stage * 2.5)
        self.assertEqual(items["rated_power"].value_fn({"POWER": 1, "POWER_FRACT": 50}), 15.0)


class ProtocolTests(unittest.TestCase):
    def test_main_off_and_on_frames_are_valid(self):
        fields = [0] * 45
        fields[17] = 6
        for main in (0, 1):
            frame = f"I{main}&" + "&".join(map(str, fields)) + f"&{main + sum(fields)}Z"
            state = protocol.BoilerState.from_frame(frame)
            self.assertIsNotNone(state)
            self.assertEqual(state.switch_boiler, main)
            self.assertEqual(state["P4_MAX_POWER_HEAT"], 6)
            self.assertIsNone(protocol.BoilerState.from_frame(frame[:-2] + "9Z"))

    def test_command_indices_and_validation(self):
        self.assertEqual(protocol.build_t_command(-1, 1), "T01010002Z")
        self.assertEqual(protocol.build_t_command(10, 0), "T12000003Z")
        self.assertEqual(protocol.build_t_command(17, 6), "T19060016Z")
        for index, value in [(-2, 1), (100, 1), (10, -1), (10, 100)]:
            with self.assertRaises(ValueError):
                protocol.build_t_command(index, value)


class FakeCoordinator:
    @classmethod
    def __class_getitem__(cls, _item):
        return cls

    def __init__(self, hass, *_args, **_kwargs):
        self.hass = hass
        self.last_update_success = True
        self.errors = 0
        self.data = None

    def async_set_update_error(self, _error):
        self.errors += 1
        self.last_update_success = False

    def async_set_updated_data(self, state):
        self.data = state
        self.last_update_success = True


class CoordinatorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.clock = 100.0
        self.calls = []
        self.ticks = []

        async def publish(_hass, topic, payload):
            self.calls.append((topic, payload))

        async def subscribe(*_args):
            return lambda: self.calls.append(("unsub", "mqtt"))

        def interval(_hass, callback, duration):
            self.ticks.append((callback, duration))
            return lambda: self.calls.append(("unsub", "watchdog"))

        ctx = {name: getattr(const, name) for name in dir(const) if name.isupper()}
        ctx.update(logging=logging, timedelta=timedelta, monotonic=lambda: self.clock,
                   DataUpdateCoordinator=FakeCoordinator, UpdateFailed=RuntimeError,
                   callback=lambda f: f, mqtt=SimpleNamespace(async_publish=publish, async_subscribe=subscribe),
                   async_track_time_interval=interval, BoilerState=protocol.BoilerState,
                   build_backlog_payload=protocol.build_backlog_payload, build_t_command=protocol.build_t_command)
        ctx = definitions("coordinator.py", {"_LOGGER", "STALE_FRAME_SECONDS", "TeknixCoordinator"}, ctx)
        self.coordinator = ctx["TeknixCoordinator"](object(), "example_boiler")
        await self.coordinator.async_start()
        self.frame = "I0&" + "&".join(["0"] * 45) + "&0Z"

    async def asyncTearDown(self):
        await self.coordinator.async_stop()

    async def test_expiry_corrupt_frames_recovery_and_no_error_flood(self):
        c = self.coordinator
        c._handle_message(SimpleNamespace(payload=self.frame))
        self.clock = 190
        c._check_freshness(None)
        self.assertTrue(c.last_update_success)
        self.clock = 191
        c._check_freshness(None)
        self.assertFalse(c.last_update_success)
        c._check_freshness(None)
        self.assertEqual(c.errors, 1)
        c._handle_message(SimpleNamespace(payload="bad frame"))
        self.assertFalse(c.last_update_success)
        c._handle_message(SimpleNamespace(payload=self.frame))
        self.assertTrue(c.last_update_success)
        self.clock = 200
        c._check_freshness(None)
        self.assertTrue(c.last_update_success)

    async def test_no_valid_frames_after_start_also_expire(self):
        self.clock = 191
        self.coordinator._check_freshness(None)
        self.assertFalse(self.coordinator.last_update_success)

    async def test_routing_timer_and_unload_cleanup(self):
        c = self.coordinator
        self.assertEqual(self.ticks[0][1], timedelta(seconds=10))
        await c.async_set_field("SWITCH_BOILER", 1)
        self.assertEqual(self.calls[-1], ("cmnd/example_boiler/Backlog", "SerialSend T01010002Z; Delay 10; SerialSend1 INFO"))
        await c.async_set_field("HEATING_MODE", 0)
        self.assertIn("T12000003Z", self.calls[-1][1])
        with self.assertRaises(ValueError):
            await c.async_set_field("UNKNOWN_FIELD", 1)
        await c.async_stop()
        self.assertIn(("unsub", "mqtt"), self.calls)
        self.assertIn(("unsub", "watchdog"), self.calls)
        count = len(self.calls)
        await c.async_stop()
        self.assertEqual(len(self.calls), count)


if __name__ == "__main__":
    unittest.main()
