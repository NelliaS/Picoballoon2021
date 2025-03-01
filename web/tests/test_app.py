import pytest

@pytest.fixture
def db(app):
    from db import Database
    db = Database(app.config['DATABASE_PATH'])
    yield db


@pytest.fixture
def app():
    import pathlib
    import os
    from app import app
    with app.app_context():
        app.config['DATABASE_PATH'] = str(pathlib.Path().resolve())
    yield app
    if os.path.exists(f"""{app.config["DATABASE_PATH"]}/database.sqlite"""):
        os.remove(f"""{app.config['DATABASE_PATH']}/database.sqlite""")


@pytest.fixture
def client(app):
    with app.test_client() as client:       # test client
        yield client


def test_db_private_attributes(db):
    '''Database attributes aren't accesible outside class'''
    with pytest.raises(AttributeError):
        assert db.__cursor
    with pytest.raises(AttributeError):
        assert db.__connection


def test_endpoint_returns_200(client):
    '''Endpoint receives data and return status_code 200 - when authorization token is correct'''
    response = client.post('/endpoint', headers={'Authorization': 'Basic Zm9vOmJhcg=='}, json={
    "app_id": "picoballoon2021",
    "dev_id": "probe",
    "hardware_serial": "00EF30A4C3C5F12F",
    "port": 1,
    "counter": 18,
    "payload_raw": "vCYoASS5AQAAAAAAAAAAAAAA",
    "payload_fields": {
        "alt_m": 0,
        "bat_mv": 441,
        "core_temp_c": 36,
        "lat": 0,
        "lon": 0,
        "loop_time_s": 0,
        "pressure_pa": 99160,
        "temp_c": 29.6
        },
    "metadata": {
        "time": "2021-06-17T19:20:32.358785168Z",
        "frequency": 867.9,
        "modulation": "LORA",
        "data_rate": "SF10BW125",
        "coding_rate": "4/5",
        "gateways": [
            {
            "gtw_id": "eui-b827ebfffe114baa",
            "timestamp": 2703562732,
            "time": "2021-06-17T19:20:32.342551Z",
            "channel": 7,
            "rssi": -120,
            "snr": -14.8,
            "rf_chain": 0,
            "latitude": 0,
            "longitude": 0,
            "altitude": 0
            },
            {},
            {},
            {}
            ],
        "latitude": 52.2345,
        "longitude": 6.2345,
        "altitude": 2
        },
    "downlink_url": "https://integrations.thethingsnetwork.org/…Kq8"
    })
    assert response.status_code == 200


def test_endpoint_passes_data(client, db):
    '''Endpoint passes received data to database'''
    response = client.post('/endpoint', headers={'Authorization': 'Basic Zm9vOmJhcg=='}, json={
    "payload_fields": {
        "alt_m": 1000,
        "bat_mv": 441,
        "core_temp_c": 36,
        "lat": 40.455,
        "lon": 10.12,
        "loop_time_s": 100,
        "pressure_pa": 99160,
        "temp_c": 29.6
        },
    "metadata": {
        "frequency": 867.9,
        "gateways": [
            {
            "gtw_id": "eui-b827ebfffe114baa",
            "timestamp": 2703562732,
            "time": "2021-06-17T19:20:32.342551Z",
            "channel": 7,
            "rssi": -120,
            "snr": -14.8,
            "rf_chain": 0,
            "latitude": 0,
            "longitude": 0,
            "altitude": 0,
            }
            ],
        "latitude": 52.2345,
        "longitude": 6.2345,
        "altitude": 2
        }
    })
    for data_row in db.fetch_all_data():
        for value in data_row:
            assert value != 'None'
    assert response.status_code == 200


def test_endpoint_save_externally(client, db, app):
    '''Endpoint saves incoming json to a new file'''
    from os import path
    from datetime import datetime

    response = client.post('/endpoint', headers={'Authorization': 'Basic Zm9vOmJhcg=='}, json={})
    last_input = db.fetch_all_data()
    timestamp = last_input[0][0]
    time = datetime.fromtimestamp(timestamp).strftime("%d.%m. %H:%M")

    assert path.exists(f"""{app.config['DATABASE_PATH']}/cloud_data/{time}.txt""") is True
    assert response.status_code == 200


def test_endpoint_no_authorization(client, db):
    '''Endpoint can handle missing headers - and deny access'''
    response = client.post('/endpoint', json={})
    assert response.status_code == 403


def test_endpoint_wrong_data(client):
    '''Endpoint can handle invalid input and deny access'''
    response = client.post('/endpoint', headers={'Authorization': 'Basic Zm9vOmJhcg=='}, data='[1, 2, 3]')
    assert response.status_code == 400
    response = client.post('/endpoint', headers={'Authorization': 'Basic Zm9vOmJhcg=='}, data='')
    assert response.status_code == 400


def test_database_no_gps(client, db):
    '''Database can handle missing gps data and save data from device instead (not from gateway)'''
    response = client.post('/endpoint', headers={'Authorization': 'Basic Zm9vOmJhcg=='}, json={
    "payload_fields": {},
    "metadata": {
        "gateways": [
            {
            "rssi": -120,
            "latitude": 10.32,
            "longitude": 14.22,
            "altitude": 5000
            },
            {},
            {},
            {}
            ],
        "latitude": 52.2345,
        "longitude": 6.2345,
        "altitude": 200
        }
    })
    for data_row in db.fetch_all_data():
        lat_gw, lon_gw, alt_gw, freq, rssi = data_row[9:-1]
        assert [lat_gw, lon_gw, alt_gw] == [52.2345, 6.2345, 200]
    assert response.status_code == 200


def test_database_missing_device_info(client, db):
    '''Database can handle missing gps data and missing device info data and save data from gateway instead'''
    response = client.post('/endpoint', headers={'Authorization': 'Basic Zm9vOmJhcg=='}, json={
    "payload_fields": {},
    "metadata": {
        "frequency": 700.9,
        "gateways": [
            {
            "gtw_id": "eui-b827ebfffe114baa",
            "timestamp": 2703562732,
            "time": "2021-06-17T19:20:32.342551Z",
            "channel": 7,
            "rssi": -100,
            "snr": -14.8,
            "rf_chain": 0,
            "latitude": 53.2312345254,
            "longitude": 42.1,
            "altitude": 100
            },
            {},
            {},
            {}
            ]
        }
    })
    for data_row in db.fetch_all_data():
        lat_gw, lon_gw, alt_gw, freq, rssi = data_row[9:-1]
        assert [lat_gw, lon_gw, alt_gw, freq, rssi] == [53.2312345254, 42.1, 100, 700.9, -100]
    assert response.status_code == 200


def test_database_no_gw(client, db):
    '''
    Database can handle missing gps data, missing device info and missing gateway data
    Only timestamp is present
    '''
    response = client.post('/endpoint', headers={'Authorization': 'Basic Zm9vOmJhcg=='}, json={
    "payload_fields": {},
    "metadata": {
        "frequency": 0,
        "gateways": []
        },
    })
    for data_row in db.fetch_all_data():
        for value in data_row[1:1]:     # except timestamp and json
            assert value == 'None'
    assert response.status_code == 200


def test_database_no_data(client, db):
    '''Database can handle empty json'''
    response = client.post('/endpoint', headers={'Authorization': 'Basic Zm9vOmJhcg=='}, json={})
    for data_row in db.fetch_all_data():
        for value in data_row[1:1]:     # except timestamp and json
            assert value == 'None'
    assert response.status_code == 200


def test_database_handle_0(client, db):
    '''Database can treat 0 values as missing (None)'''
    response = client.post('/endpoint', headers={'Authorization': 'Basic Zm9vOmJhcg=='}, json={
    "payload_fields": {
        "alt_m": 0,
        "bat_mv": 0,
        "core_temp_c": 0,
        "lat": 0,
        "lon": 0,
        "loop_time_s": 0,
        "pressure_pa": 0,
        "temp_c": 0
        },
    "metadata": {
        "frequency": 0,
        "gateways": [
            {
            "rssi": 0,
            "rf_chain": 0,
            "latitude": 0,
            "longitude": 0,
            "altitude": 0
            }
            ],
        "latitude": 0,
        "longitude": 0,
        "altitude": 0
        }
    })
    for data_row in db.fetch_all_data():
        for value in data_row[1:-1]:  # except timestamp and json
            assert value == 'None'
    assert response.status_code == 200


def test_database_strongest_gw(client, db):
    '''Database will use gateway with strongest rssi'''
    response = client.post('/endpoint', headers={'Authorization': 'Basic Zm9vOmJhcg=='}, json={
    "metadata": {
        "frequency": 867.9,
        "gateways": [
            {
            "rssi": -120,
            "latitude": 10.00,
            "longitude": 10.00,
            "altitude": 5000
            },
            {
            "rssi": 100,
            "latitude": 20.00,
            "longitude": 20.00,
            "altitude": 6000
            },
            {
            "rssi": 50,
            "latitude": 30.00,
            "longitude": 30.00,
            "altitude": 7000
            }
            ],
        }
    })
    for data_row in db.fetch_all_data():
        lat_gw, lon_gw, alt_gw, freq, rssi = data_row[9:-1]
        assert [lat_gw, lon_gw, alt_gw, freq, rssi] == [20.00, 20.00, 6000, 867.9, 100]
    assert response.status_code == 200


def test_database_strings_invalid(client, db):
    '''Database will treat strins as missing'''
    response = client.post('/endpoint', headers={'Authorization': 'Basic Zm9vOmJhcg=='}, json={
    "payload_fields": {"loop_time_s": "heey"},
    "metadata": {
        "frequency": "hey",
        "gateways": [
            {
            "latitude": "hello",
            "longitude": "hi",
            }
            ],
        }
    })
    for data_row in db.fetch_all_data():
        _, _, _, _, _, _, _, _, loop_time, lat_gw, lon_gw, _, freq, rssi = data_row[:-1]
        assert [lat_gw, lon_gw, freq, loop_time] == ['None', 'None', 'None', 'None']
    assert response.status_code == 200


def test_app_temp_correct(client, db, app):
    '''App will use valid temperature'''
    from app import provide_data
    response = client.post('/endpoint', headers={'Authorization': 'Basic Zm9vOmJhcg=='}, json={
    "payload_fields": {
        "core_temp_c": 30,
        "temp_c": 20
        },
    })
    data = provide_data()
    temp = data[0][2]
    assert temp == "20.0 °C"


def test_app_temp_invalid(client, db, app):
    '''App will use core temperature instead of temperature if needed'''
    from app import provide_data
    response = client.post('/endpoint', headers={'Authorization': 'Basic Zm9vOmJhcg=='}, json={
    "payload_fields": {
        "core_temp_c": 30,
        "temp_c": 200
        },
    })
    data = provide_data()
    temp = data[0][2]
    assert temp == "30.0 °C"

def test_app_temp_missing(client, db, app):
    '''App cannot use any temperature, since both are invalid'''
    from app import provide_data
    response = client.post('/endpoint', headers={'Authorization': 'Basic Zm9vOmJhcg=='}, json={
    "payload_fields": {
        "core_temp_c": -110,
        "temp_c": 51
        },
    })
    data = provide_data()
    temp = data[0][2]
    assert temp == "missing"