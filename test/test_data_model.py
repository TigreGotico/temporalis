from temporalis import DataPoint, WeatherData


def test_datapoint_as_dict_idempotent():
    dp = DataPoint("Temperature", 20, "ºC", min_val=15, max_val=25)
    d1 = dp.as_dict()
    d2 = dp.as_dict()
    assert d1 == d2
    assert dp.value == 20


def test_datapoint_as_dict_no_mutation():
    dp = DataPoint("Humidity", 80, "%")
    dp.as_dict()
    assert dp.value == 80
    assert dp.name == "Humidity"
    assert dp.units == "%"


def test_weatherdata_as_dict_idempotent():
    wd = WeatherData()
    wd.temperature = DataPoint("Temperature", 20, "ºC")
    wd.humidity = DataPoint("Humidity", 80, "%")
    wd.summary = "clear"
    wd.icon = "clear"
    d1 = wd.as_dict()
    d2 = wd.as_dict()
    assert d1 == d2


def test_weatherdata_as_dict_no_mutation():
    wd = WeatherData()
    wd.temperature = DataPoint("Temperature", 20, "ºC")
    wd.summary = "rain"
    wd.as_dict()
    assert wd.temperature is not None
    assert wd.temperature.value == 20
    assert wd.summary == "rain"


def test_datapoint_repr():
    dp = DataPoint("Temperature", 20, "ºC")
    assert "20" in repr(dp)
    assert "ºC" in repr(dp)
